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

    def _write_partner_data(self, cr, uid, cust_elmnt, partner, context=None):
        if not partner:
            return

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

        self._write_tree(cust_elmnt, values)

    def _write_to_file(self, filename, root):
        module_path = __file__.split('models')[0]
        local_file = module_path + 'tmp/' + filename
        with io.open(local_file, 'w+', encoding='utf-8') as f:
            f.write(u'<?xml version="1.0" encoding="utf-8"?>')
            f.write(ET.tostring(root, encoding='utf-8').decode('utf-8'))

    def _upload(self, cr, uid, ftp_config_id, filename, context=None):
        config_obj = self.browse(cr, uid, ftp_config_id, context=context)
        ftp = FTP(host=config_obj.addr,user=config_obj.user, passwd=config_obj.psswd)
        inbound_path =  config_obj.inbound_path.rstrip('/') + "/"
        ftp.cwd(inbound_path)
        with open(local_file, 'r') as f:
            ftp.storlines('STOR ' + filename, f)
        os.remove(local_file)

    def _export_partners(self, cr, uid, ftp_config_id, partner_ids, context=None):
        if not ftp_config_id:
            return []

        now = datetime.now()
        root_create = ET.Element('customers')
        root_update = ET.Element('customers')
        partner_model = self.pool.get('res.partner')

        for partner_id in partner_ids:
            partner = partner_model.browse(cr, uid, partner_id, context=context)
            partner_perm = partner_model.perm_read(cr, uid, [partner_id], context=context, details=True)
            create_date = datetime.strptime(partner_perm[0].get('create_date'),'%Y-%m-%d %H:%M:%S.%f')
            if create_date > now - timedelta(seconds=2):
                self._write_partner_data(cr, uid, ET.SubElement(root_create,'customer'), partner, context=None)
            else:
                self._write_partner_data(cr, uid, ET.SubElement(root_update,'customer'), partner, context=None)

        ir_model_data_model = self.pool.get('ir.model.data')
        sequence_model = self.pool.get('ir.sequence')

        if len(root_create.findall('customer')) > 0:
            mdid = ir_model_data_model._get_id(cr, uid, 'lct_tos_integration', 'sequence_partner_create_export')
            sequence_id = ir_model_data_model.read(cr, uid, [mdid], ['res_id'])[0]['res_id']
            sequence = sequence_model.next_by_id(cr, uid, sequence_id, context=context)
            if int(sequence[3:]) >= 999999:
                sequence_model._alter_sequence(cr, sequence_id, 1, 1)
            filename = "CUS_CREATE_" + datetime.today().strftime('%y%m%d') + "_" + sequence + ".xml"
            self._write_to_file(filename, root_create)
            self._upload(cr, uid, ftp_config_id, filename, context=context)

        if len(root_update.findall('customer')) > 0:
            mdid = ir_model_data_model._get_id(cr, uid, 'lct_tos_integration', 'sequence_partner_update_export')
            sequence_id = ir_model_data_model.read(cr, uid, [mdid], ['res_id'])[0]['res_id']
            sequence = sequence_model.next_by_id(cr, uid, sequence_id, context=context)
            if int(sequence[3:]) >= 999999:
                sequence_model._alter_sequence(cr, sequence_id, 1, 1)
            filename = "CUS_UPDATE_" + datetime.today().strftime('%y%m%d') + "_" + sequence + ".xml"
            self._write_to_file(filename, root_update)
            self._upload(cr, uid, ftp_config_id, filename, context=context)

        return []

    def action_export_partners(self, cr, uid, partner_ids, context=None):
        ftp_config_ids = self.search(cr, uid, [('active','=',True)], context=context)
        ftp_config_id = ftp_config_ids and ftp_config_ids[0] or False
        return self._export_partners(cr, uid, ftp_config_id, partner_ids, context=context)

