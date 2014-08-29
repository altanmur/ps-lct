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
from ftplib import FTP
from lxml import etree as ET
import os
from StringIO import StringIO
from datetime import datetime
import io
import traceback
from tempfile import NamedTemporaryFile


class ftp_config(osv.osv):
    _name="ftp.config"

    _columns = {
        'name': fields.char('Name', required=True),
        'addr': fields.char('Server Address', required=True),
        'user': fields.char('Username', required=True),
        'psswd': fields.char('Password', required=True),
        'inbound_path': fields.char('Path of inbound folder', required=True),
        'outbound_path': fields.char('Path of outbound folder', required=True),
        'active': fields.boolean('Active'),
        'last_import': fields.date('Last Import', readonly=True)
    }

    def _check_active(self, cr, uid, ids, context=None):
        config_ids = self.search(cr, uid, [('active','=',True)], context=context)
        return len(config_ids) <= 1

    _constraints = [
        (_check_active, 'There can only be one active ftp configuration', ['active']),
    ]

    # Data Import

    def _import_ftp_data(self, cr, uid, config_ids, context=None):
        if not config_ids:
            return []

        imp_data_model = self.pool.get('lct.tos.import.data')
        imp_data_ids = []
        for config_obj in self.browse(cr, uid, config_ids, context=context):
            ftp = FTP(host=config_obj.addr, user=config_obj.user, passwd=config_obj.psswd)
            ftp.cwd(config_obj.outbound_path)
            archive_path = 'done'
            if archive_path not in ftp.nlst():
                ftp.mkd(archive_path)

            for filename in ftp.nlst():
                if filename == archive_path:
                    continue

                content = StringIO()
                try:
                    ftp.retrlines('RETR ' + filename, content.write)
                except:
                    imp_data_model.create(cr, uid, {
                            'name': filename,
                            'content': False,
                            'status': 'fail',
                            'error': traceback.format_exc(),
                        }, context=context)
                    continue

                imp_data_ids.append(imp_data_model.create(cr, uid, {
                        'name': filename,
                        'content': content.getvalue(),
                    }, context=context))

                toname = filename
                extension = ''
                if '.' in filename[1:-1]:
                    extension =  "".join(['.', filename.split('.')[-1]])
                toname_base = toname[:-(len(extension))]

                n = 1
                archive_files = [archive_file.replace('/done','') for archive_file in ftp.nlst(archive_path)]
                while toname in archive_files :
                    toname = "".join([toname_base, '-', str(n), extension])
                    n += 1
                try:
                    ftp.rename(filename, "".join([archive_path, "/", toname]))
                except:
                    imp_data_model.write(cr, uid, imp_data_ids.pop(), {
                        'status': 'fail',
                        'error': traceback.format_exc(),
                        }, context=context)
                    continue

        cr.commit()
        imp_data_model.process_data(cr, uid, imp_data_ids, context=context)

    def button_import_ftp_data(self, cr, uid, ids, context=None):
        return self._import_ftp_data(cr, uid, ids, context=context)

    def cron_import_ftp_data(self, cr, uid, context=None):
        self._import_ftp_data(cr, uid, self.search(cr, uid, [('active','=',True)]), context=context)


    # Data Export

    def _dict_to_tree(self, vals, elmnt):
        for tag, val in vals.iteritems():
            subelmnt = ET.SubElement(elmnt, tag)
            if not val:
                pass
            elif isinstance(val, unicode):
                subelmnt.text = val
            elif isinstance(val, str):
                subelmnt.text = unicode(val)
            elif isinstance(val, int) or isinstance(val, long) and not isinstance(val, bool):
                subelmnt.text = unicode(str(val))
            elif isinstance(val,dict):
                self._dict_to_tree(val, subelmnt)
            elif isinstance(val,list):
                for list_elem in val:
                    self._dict_to_tree(list_elem, subelmnt)

    def _write_partners_tree(self, cr, uid, partner_ids, context=None):
        root = ET.Element('customers')
        partner_model = self.pool.get('res.partner')
        partners = partner_model.browse(cr, uid, partner_ids, context=context)
        for partner in partners:
            values = {
                'customer_id': partner.id,
                'customer_key': partner.ref,
                'name': partner.name,
                'street': (partner.street + ( (', ' + partner.street2) if partner.street2 else '') if partner.street else '') or False,
                'city': partner.city,
                'zip': partner.zip,
                'country': partner.country_id and partner.country_id.name,
                'email': partner.email,
                'website': partner.website,
                'phone': partner.phone or partner.mobile or False
            }
            self._dict_to_tree(values, ET.SubElement(root, 'customer'))
        return root

    def _write_app_tree(self, cr, uid, app_id, payment_id, context=None):
        root = ET.Element('appointments')
        invoice_model = self.pool.get('account.invoice')
        voucher_model = self.pool.get('account.voucher')
        invoice = invoice_model.browse(cr, uid, app_id, context=context)
        voucher = voucher_model.browse(cr, uid, payment_id, context=context)
        values = {
            'customer_id': invoice.partner_id.name,
            'individual_customer': 'IND' if invoice.individual_cust else 'STD',
            'appointment_reference': invoice.appoint_ref,
            'appointment_date': invoice.appoint_date,
            'payment_made': 'YES',
            'pay_through_date': invoice.date_due,
            'payment_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'cashier_receipt_number': voucher.cashier_rcpt_nr, # TODO
        }
        self._dict_to_tree(values, ET.SubElement(root, 'appointment'))
        return root

    def _write_xml_file(self, root):
        f = NamedTemporaryFile("w+")
        f.write(u'<?xml version="1.0" encoding="utf-8"?>')
        f.write(ET.tostring(root, encoding='utf-8', pretty_print=True).decode('utf-8'))
        return f

    def _upload_file(self, cr, uid, temp_file, file_name, context=None):
        ftp_config_ids = self.search(cr, uid, [('active','=',True)], context=context)
        ftp_config_id = ftp_config_ids and ftp_config_ids[0] or False
        config_obj = self.browse(cr, uid, ftp_config_id, context=context)
        ftp = FTP(host=config_obj.addr, user=config_obj.user, passwd=config_obj.psswd)
        inbound_path =  config_obj.inbound_path.rstrip('/') + "/"
        ftp.cwd(inbound_path)
        temp_file.seek(0)
        ftp.storlines('STOR ' + file_name, temp_file)

    def export_partners(self, cr, uid, partner_ids, context=None):
        if not partner_ids:
            return []
        ftp_config_ids = self.search(cr, uid, [('active','=',True)], context=context)
        if not ftp_config_ids:
            raise osv.except_osv(('Error'), ('Impossible to find an active FTP configuration to export this partner'))
        root = self._write_partners_tree(cr, uid, partner_ids, context=context)

        sequence = self.pool.get('ir.sequence').get_next_by_xml_id(cr, uid, 'lct_tos_integration', 'sequence_partner_export', context=context)

        local_path = __file__.split('models')[0] + "tmp/"
        file_name = 'CUS_' + datetime.today().strftime('%y%m%d') + '_' + sequence + '.xml'
        self._upload_file(cr, uid, self._write_xml_file(root), file_name, context=context)
        return partner_ids

    def export_app(self, cr, uid, app_id, payment_id, context=None):
        if not (app_id and payment_id):
            return []
        root = self._write_app_tree(cr, uid, app_id, payment_id, context=context)
        sequence = self.pool.get('ir.sequence').get_next_by_xml_id(cr, uid, 'lct_tos_integration', 'sequence_appointment_validate_export', context=context)
        local_path = __file__.split('models')[0] + "tmp/"
        file_name = 'APP_' + datetime.today().strftime('%y%m%d') + '_' + sequence + '.xml'
        self._upload_file(cr, uid, self._write_xml_file(root), file_name, context=context)
