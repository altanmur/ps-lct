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
from ftplib import FTP

import xml_tools


class lct_tos_export_data(osv.Model):
    _name = 'lct.tos.export.data'

    _columns = {
        'name': fields.char('File name', readonly=True),
        'content': fields.text('File content', readonly=True),
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
        }
        return self.create(cr, uid, vals, context=context)

    def upload_files(self, cr, uid, ids, context=None):
        pending_files = self.search(cr, uid, [('id', 'in', ids), ('status', '=', 'pending')], context=context)
        if len(pending_files) < len(ids):
            raise osv.except_osv(('Error'), ('You can only process pending files'))

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

        content = imported_file.content.encode('utf-8')
        root = ET.fromstring(content)
        appointment = root.find('appointment')

        xml_tools.find_or_create(appointment, 'payment_made').text = 'YES'
        xml_tools.find_or_create(appointment, 'payment_date').text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        xml_tools.find_or_create(appointment, 'cashier_receipt_number').text = voucher.cashier_rcpt_nr

        sequence = self.pool.get('ir.sequence').get_next_by_xml_id(cr, uid, 'lct_tos_integration', 'sequence_appointment_validate_export', context=context)
        file_name = 'APP_' + datetime.today().strftime('%y%m%d') + '_' + sequence + '.xml'

        exported_file_id = self._create_from_xml(cr, uid, root, file_name, context=context)
        self.upload_files(cr, uid, [exported_file_id], context=context)

    def _write_partners_tree(self, cr, uid, partner_ids, context=None):
        root = ET.Element('customers')
        partner_model = self.pool.get('res.partner')
        partners = partner_model.browse(cr, uid, partner_ids, context=context)
        for partner in partners:
            vals = {
                'customer_id': partner.id,
                'customer_key': partner.ref,
                'name': partner.name,
                'street': (partner.street + ( (', ' + partner.street2) if partner.street2 else '') if partner.street else '') or False,
                'city': partner.city,
                'zip': partner.zip,
                'country': partner.country_id and partner.country_id.code,
                'email': partner.email,
                'website': partner.website,
                'phone': partner.phone or partner.mobile or False
            }
            xml_tools.dict_to_tree(vals, ET.SubElement(root, 'customer'))
        return root

    def export_partners(self, cr, uid, partner_ids, context=None):
        if not partner_ids:
            return []

        root = self._write_partners_tree(cr, uid, partner_ids, context=context)

        sequence = self.pool.get('ir.sequence').get_next_by_xml_id(cr, uid, 'lct_tos_integration', 'sequence_partner_export', context=context)
        file_name = 'CUS_' + datetime.today().strftime('%y%m%d') + '_' + sequence + '.xml'

        exported_file_id = self._create_from_xml(cr, uid, root, file_name, context=context)
        self.upload_files(cr, uid, [exported_file_id], context=context)
