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
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
import io
from ftplib import FTP
import os

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
    }

    def _check_active(self, cr, uid, ids, context=None):
        config_ids = self.search(cr, uid, [('active','=',True)], context=context)
        return len(config_ids) <= 1

    _constraints = [
        (_check_active, 'There can only be one active ftp configuration', ['active']),
    ]

    def _write_tree(self, elmnt, vals):
        for tag, val in vals.iteritems():
            subelmnt = ET.SubElement(elmnt, tag)
            if isinstance(val, unicode):
                subelmnt.text = val
            elif isinstance(val, str):
                subelmnt.text = unicode(val)
            elif isinstance(val,dict):
                self._write_tree(subelmnt, val)

    def _upload(self, cr, uid, root, ftp_config_id, file_name, context=None):
        module_path = __file__.split('models')[0]
        local_file = module_path + 'tmp/' + file_name
        with io.open(local_file, 'w+', encoding='utf-8') as f:
            f.write(u'<?xml version="1.0" encoding="utf-8"?>')
            f.write(ET.tostring(root, encoding='utf-8').decode('utf-8'))

    def _write_partners_tree(self, cr, uid, partner_ids, context=None):
        root = ET.Element('customers')
        partner_model = self.pool.get('res.partner')
        partners = partner_model.browse(cr, uid, partner_ids, context=context)
        for partner in partners:
            values = {
                'customer_id': partner.name,
                'customer_key': partner.ref,
                'name': partner.parent_id and partner.parent_id.name or False,
                'street': (partner.street + ( (', ' + partner.street2) if partner.street2 else '') if partner.street else ''),
                'city': partner.city,
                'zip': partner.zip,
                'country': partner.country_id and partner.country_id.name,
                'email': partner.email,
                'website': partner.website,
                'phone': partner.phone or partner.mobile or False
            }
            self._write_tree(ET.SubElement(root, 'customer'), values)
        return root

    def _get_sequence(self, cr, uid, module, xml_id, context=None):
        ir_model_data_model = self.pool.get('ir.model.data')
        sequence_model = self.pool.get('ir.sequence')
        mdid = ir_model_data_model._get_id(cr, uid, module, xml_id)
        sequence_id = ir_model_data_model.read(cr, uid, [mdid], ['res_id'])[0]['res_id']
        sequence_obj = sequence_model.browse(cr, uid, sequence_id, context=context)
        sequence = sequence_model.next_by_id(cr, uid, sequence_id, context=context)
        if int(sequence) >= 10**(sequence_obj.padding):
                sequence_model._alter_sequence(cr, sequence_id, 1, 1)
                sequence = sequence_model.next_by_id(cr, uid, sequence_id, context=context)
        return sequence

    def _write_xml_file(self, local_file, root):
        with io.open(local_file, 'w+', encoding='utf-8') as f:
            f.write(u'<?xml version="1.0" encoding="utf-8"?>')
            f.write(ET.tostring(root, encoding='utf-8').decode('utf-8'))

    def _upload_file(self, cr, uid, local_path, file_name, context=None):
        ftp_config_ids = self.search(cr, uid, [('active','=',True)], context=context)
        ftp_config_id = ftp_config_ids and ftp_config_ids[0] or False
        config_obj = self.browse(cr, uid, ftp_config_id, context=context)
        ftp = FTP(host=config_obj.addr, user=config_obj.user, passwd=config_obj.psswd)
        inbound_path =  config_obj.inbound_path.rstrip('/') + "/"
        ftp.cwd(inbound_path)
        local_file = local_path + file_name
        with open(local_file, 'r') as f:
            ftp.storlines('STOR ' + file_name, f)
        os.remove(local_file)

    def export_partners(self, cr, uid, partner_ids, create_or_write='create', context=None):
        if not partner_ids:
            return []
        if create_or_write not in ['create', 'update']:
            raise osv.except_osv(('Error'), ("Argument create_or_write should be 'create' or 'write'"))

        sequence_xml_id, file_prefix = ('sequence_partner_update_export', 'CUS_UPDATE_') if create_or_write == 'update' \
            else ('sequence_partner_create_export', 'CUS_CREATE_')

        root = self._write_partners_tree(cr, uid, partner_ids, context=context)

        sequence = self._get_sequence(cr, uid, 'lct_tos_integration', sequence_xml_id, context=context)

        local_path = __file__.split('models')[0] + "tmp/"
        file_name = file_prefix + datetime.today().strftime('%y%m%d') + '_SEQ' + sequence + '.xml'
        self._write_xml_file(local_path + file_name, root)
        self._upload_file(cr, uid, local_path, file_name, context=context)


