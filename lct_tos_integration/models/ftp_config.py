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
from xml.etree import ElementTree as ET
import os
from datetime import datetime
import re

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

    def _get_elmnt_text(self, elmnt, tag):
        sub_elmnt = elmnt.find(tag)
        if sub_elmnt is not None:
            return sub_elmnt.text
        else:
            raise osv.except_osv(('Error'),('Unable to find tag %s\nin element : %s\nin file : %s' % (tag, elmnt.tag, self.curr_file)))

    def _get_product_info(self, ids):
        if not ids:
            raise osv.except_osv(('Error'), ('XML file is missing some information on products'))
        return ids[0]

    def _get_invoice_lines(self, cr, uid, lines, line_map, context=None):
        product_model = self.pool.get('product.product')
        if len(lines) < 1:
            return []

        lines_vals = []
        for line in lines.findall('line'):
            vals = {}
            for field, tag in line_map.iteritems():
                if isinstance(tag, str):
                    vals[field] = self._get_elmnt_text(line,tag)

            category_type = self._get_elmnt_text(line, line_map['product_map']['category_type_id'])
            if category_type == 'I':
                category_type_name, service_name = 'Import', 'Discharge'
            elif category_type == 'E':
                category_type_name, service_name = 'Export', 'Load'
            else:
                raise osv.except_osv(('Error'), ('XML file is missing some information on products'))
            category_type_id = self._get_product_info(self.pool.get('lct.product.category').search(cr, uid, [('name', '=', category_type_name)], context=context))
            service_id = self._get_product_info(self.pool.get('lct.product.service').search(cr, uid, [('name', '=', service_name)], context=context))

            size_size = int(self._get_elmnt_text(line,line_map['product_map']['size_id']))
            size_id = self._get_product_info(self.pool.get('lct.product.size').search(cr, uid, [('size', '=', size_size)], context=context))

            status = self._get_elmnt_text(line,line_map['product_map']['status_id'])
            status_name = 'Full' if status == 'F' \
                else 'Empty' if status == 'E' \
                else False
            status_ids = status_name and self.pool.get('lct.product.status').search(cr, uid, [('name', '=', status_name)], context=context) or False
            status_id = self._get_product_info(status_ids)

            type_name = 'GP' if self._get_elmnt_text(line,line_map['product_map']['type_id']) == 'GP' \
                else False
            type_ids = type_name and self.pool.get('lct.product.type').search(cr, uid, [('name', '=', type_name)], context=context) or False
            type_id = self._get_product_info(type_ids)

            product_domain = [(name, '=', eval(name)) for name in ['category_type_id', 'service_id', 'size_id', 'status_id', 'type_id']]
            product_ids = product_model.search(cr, uid, product_domain, context=context)
            product = product_ids and product_model.browse(cr, uid, product_ids, context=context)[0] or False
            if not product:
                raise osv.except_osv(('Error'), ('No product could be found for this combination'))

            vals.update({
                'product_id': product.id,
                'name' : product.name,
                'quantity': 1,
                'price_unit': product.list_price,
            })
            lines_vals.append(vals)
        return [(0,0,vals) for vals in lines_vals]

    def _get_invoice_vals(self, cr, uid, invoice, invoice_map, context=None):
        partner_model = self.pool.get('res.partner')
        vals = {}
        for field, tag in invoice_map.iteritems():
            if isinstance(tag, str):
                vals[field] = self._get_elmnt_text(invoice, tag)

        partner_ids = partner_model.search(cr, uid, [('name', '=', vals['partner_id'])], context=context) \
            or partner_model.search(cr, uid, [('name', 'ilike', vals['partner_id'])], context=context)
        if partner_ids:
            vals['partner_id'] = partner_ids[0]
        else:
            raise osv.except_osv(('Error'), ('No customer with this name was found'))

        invoice_line = self._get_invoice_lines(cr, uid, invoice.find('lines'), invoice_map['line_map'], context=context)

        # TODO /!\ Must be changed
        account_id = self.pool.get('account.account').search(cr, uid, [], limit=1, context=context)[0]

        vals.update({
            'account_id': account_id,
            'date_invoice': datetime.today().strftime('%Y-%m-%d'),
            'invoice_line': invoice_line,
            'state': 'draft',
            'type': 'out_invoice',
        })
        return vals

    def _import_app(self, cr, uid, appointments, context=None):
        appointment_map = {
            'partner_id': 'customer_id',
            'appoint_ref': 'appointment_reference',
            'appoint_date': 'appointment_date',
            'line_map':  {
                'product_map':{
                    'category_type_id': 'category',
                    'size_id': 'container_size',
                    'status_id': 'status',
                    'type_id': 'container_type',
                },
                'cont_nr': 'container_number',
                'cont_operator': 'container_operator',
            },
        }
        appointment_ids = []
        invoice_model = self.pool.get('account.invoice')
        for appointment in appointments.findall('appointment'):
            appointment_vals = self._get_invoice_vals(cr, uid, appointment, appointment_map, context=context)
            appointment_vals['type2'] = 'appointment'
            individual = appointment.find('individual_customer')
            appointment_vals['individual_cust'] = True if individual is not None and individual.text == 'IND' else False
            appointment_ids.append(invoice_model.create(cr, uid, appointment_vals, context=context))
        return appointment_ids

    def _import_vbl(self, cr, uid, vbillings, context=None):
        vbilling_map = {
            'partner_id': 'vessel_operator_id',
            'call_sign': 'call_sign',
            'lloyds_nr': 'lloyds_number',
            'vessel_ID': 'vessel_id',
            'berth_time': 'berthing_time',
            'dep_time': 'departure_time',
            'line_map':  {
                'product_map':{
                    'category_type_id': 'transaction_category_id',
                    'size_id': 'container_size',
                    'status_id': 'container_status',
                    'type_id': 'container_type_id',
                },
                'cont_nr': 'container_number',
                'cont_operator': 'container_operator_id',
            },
        }
        vbilling_ids = []
        product_model = self.pool.get('product.product')
        invoice_model = self.pool.get('account.invoice')
        for vbilling in vbillings.findall('vbilling'):
            vbilling_vals = self._get_invoice_vals(cr, uid, vbilling, vbilling_map, context=context)
            vbilling_vals['type2'] = 'vessel'
            if vbilling.find('hatchcovers_moves') is not None and int(self._get_elmnt_text(vbilling, 'hatchcovers_moves')) > 0:
                product_ids = product_model.search(cr, uid, [('name', '=', 'Hatch cover move')], context=context)
                if not product_ids:
                    raise osv.except_osv(('Error'), ('No product found for "Hatch cover move"'))
                product = product_model.browse(cr, uid, product_ids)[0]
                line_vals = {
                    'product_id': product.id,
                    'name' : product.name,
                    'quantity': int(self._get_elmnt_text(vbilling, 'hatchcovers_moves')),
                    'price_unit': product.list_price,
                }
                vbilling_vals['invoice_line'].append((0,0,line_vals))
            if vbilling.find('gearbox_count') is not None and int(self._get_elmnt_text(vbilling, 'gearbox_count')) > 0:
                product_ids = product_model.search(cr, uid, [('name', '=', 'Gearbox count')])
                if not product_ids:
                    raise osv.except_osv(('Error'), ('No product found for "Hatch cover move"'))
                product = product_model.browse(cr, uid, product_ids)[0]
                line_vals = {
                    'product_id': product.id,
                    'name' : product.name,
                    'quantity': int(self._get_elmnt_text(vbilling, 'gearbox_count')),
                    'price_unit': product.list_price,
                }
                vbilling_vals['invoice_line'].append((0,0,line_vals))
            vbilling_ids.append(invoice_model.create(cr, uid, vbilling_vals, context=context))
        return vbilling_ids

    def _import_data(self, cr, uid, ids, context=None):
        if not ids:
            return []

        config_obj = self.browse(cr, uid, ids, context=context)[0]
        ftp = FTP(host=config_obj.addr, user=config_obj.user, passwd=config_obj.psswd)
        outbound_path =  config_obj.outbound_path
        ftp.cwd(outbound_path)
        module_path = __file__.split('models')[0]

        invoice_ids = []
        for filename in ftp.nlst():
            self.curr_file = filename
            loc_file = os.path.join(module_path, 'tmp', filename)
            with open(loc_file, 'w+') as f:
                ftp.retrlines('RETR ' + filename, f.write)
            if re.match('^VBL_IN_\d{2}-\d{2}-\d{2}_SEQ\d{6}\.xml$', filename):
                root = ET.parse(loc_file).getroot()
                invoice_ids.extend(self._import_vbl(cr, uid, root, context=context))
            elif re.match('^APP_IN_\d{2}-\d{2}-\d{2}_SEQ\d{6}\.xml$', filename):
                root = ET.parse(loc_file).getroot()
                invoice_ids.extend(self._import_app(cr, uid, root, context=context))
            os.remove(loc_file)
            ftp.delete(filename)
        return invoice_ids

    def button_import_data(self, cr, uid, ids, context=None):
        return self._import_data(cr, uid, ids, context=context)

    def cron_import_data(self, cr, uid, context=None):
        self._import_data(cr, uid, self.search(cr, uid, [('active','=',True)]), context=context)