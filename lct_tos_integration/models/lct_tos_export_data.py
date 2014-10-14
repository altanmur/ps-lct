# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-TODAY OpenERP S.A. <http://www.openerp.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import fields, osv

import os
import traceback
from StringIO import StringIO
from lxml import etree as ET
from datetime import datetime
import unicodedata
from ftplib import FTP

import xml_tools


class lct_tos_export_data(osv.Model):
    _name = 'lct.tos.export.data'

    _columns = {
        'name': fields.char('File name', readonly=True),
        'content': fields.text('File content', readonly=True),
        'type': fields.selection([('xml','xml')], string='File type'),
        'status': fields.selection([('fail','Failed to upload'),('success','Uploaded'),('pending','Pending')], string='Status', readonly=True, required=True),
        'create_date': fields.date(string='Created Date', readonly=True),
        'error': fields.text('Errors'),
    }

    _defaults = {
        'status': 'pending',
    }

    def button_reset(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'status': 'pending', 'error': False}, context=context)

    def _create_from_xml(self, cr, uid, root, file_name, context=None):
        header = u'<?xml version="1.0" encoding="utf-8"?>'
        body = ET.tostring(root, encoding='utf-8', pretty_print=True).decode('utf-8')
        content = '\n'.join([header, body])

        vals = {
            'name': file_name,
            'content': content,
            'type': 'xml',
        }

        return self.create(cr, uid, vals, context=context)

    def upload_files(self, cr, uid, ids, context=None):
        ftp_config_model = self.pool.get('ftp.config')
        ftp_config_ids = ftp_config_model.search(cr, uid, [('active','=',True)], context=context)
        ftp_config_id = ftp_config_ids and ftp_config_ids[0] or False
        if not ftp_config_id:
            raise osv.except_osv(('Error'), ('Impossible to find an active FTP Config'))

        config = ftp_config_model.browse(cr, uid, ftp_config_id, context=context)
        ftp = FTP(host=config.addr, user=config.user, passwd=config.psswd)
        inbound_path =  config.inbound_path.rstrip(os.sep) + os.sep
        ftp.cwd(inbound_path)

        for exported_file in self.browse(cr, uid, ids, context=context):
            cr.execute('SAVEPOINT SP')
            file_name = exported_file.name
            f = StringIO()
            f.write(exported_file.content)
            f.seek(0)
            try:
                ftp.storlines('STOR ' + file_name, f)
            except:
                cr.execute('ROLLBACK TO SP')
                self.write(cr, uid, exported_file.id, {
                    'status': 'fail',
                    'error': traceback.format_exc()
                }, context=context)
            else:
                self.write(cr, uid, exported_file.id, {
                        'status': 'success',
                    }, context=context)
                cr.execute('RELEASE SAVEPOINT SP')



    def export_app(self, cr, uid, invoice_id, payment_id, context=None):
        invoice = self.pool.get('account.invoice').browse(cr, uid, invoice_id, context=context)
        voucher = self.pool.get('account.voucher').browse(cr, uid, payment_id, context=context)
        imported_file = invoice.imported_file_id
        if not imported_file:
            raise osv.except_osv(('Error'), ("No imported file found on invoice"))

        content = unicodedata.normalize('NFKD', imported_file.content).encode('ascii','ignore')
        root = ET.fromstring(content)
        appointment = root.find('appointment')

        xml_tools.find_or_create(appointment, 'payment_made').text = 'YES'
        xml_tools.find_or_create(appointment, 'payment_date').text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        xml_tools.find_or_create(appointment, 'cashier_receipt_number').text = voucher.cashier_rcpt_nr

        exported_file_id = self._create_from_xml(cr, uid, root, imported_file.name, context=context)

        self.upload_files(cr, uid, [exported_file_id], context=context)

