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
import re
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

    def _get_invoice_lines(self, cr, uid, lines_elmnt, context=None):
        if not lines_elmnt:
            return []

        lines_vals = []
        for line_elmnt in lines_elmnt.findall('line'):

            category_name = 'Import' if line_elmnt.find('transaction_category_id').text == 'I' \
                else 'Export' if line_elmnt.find('transaction_category_id').text == 'E' \
                else False
            category_ids = category_name and self.pool.get('lct.product.category').search(cr, uid, [('name','=',category_name)], context=context) or False
            category_id = category_ids and category_ids[0] or False

            service_name = 'Discharge' if category_name == 'Import' \
                else 'Load' if category_name == 'Export' \
                else False
            service_ids = service_name and self.pool.get('lct.product.service').search(cr, uid, [('name','=',service_name)], context=context) or False
            service_id = service_ids and service_ids[0] or False

            size_size = int(line_elmnt.find('container_size').text)
            size_ids = self.pool.get('lct.product.size').search(cr, uid, [('size','=',size_size)], context=context)
            size_id = size_ids and size_ids[0]

            status_name = 'Full' if line_elmnt.find('container_status').text == 'F' \
                else 'Empty' if line_elmnt.find('container_status').text == 'E' \
                else False
            status_ids = status_name and self.pool.get('lct.product.status').search(cr, uid, [('name','=',status_name)], context=context) or False
            status_id = status_ids and status_ids[0] or False

            type_name = 'GP' if line_elmnt.find('container_type_id').text == 'GP' \
                else False
            type_ids = type_name and self.pool.get('lct.product.type').search(cr, uid, [('name','=',type_name)], context=context) or False
            type_id = type_ids and type_ids[0] or False
            if service_id and size_id and status_id and type_id:
                product_domain = [
                    ('category_type_id','=',category_id),
                    ('service_id','=',service_id),
                    ('size_id','=',size_id),
                    ('status_id','=',status_id),
                    ('type_id','=',type_id),
                ]
                product_ids = self.pool.get('product.product').search(cr, uid, product_domain, context=context)
                product = product_ids and self.pool.get('product.product').browse(cr, uid, product_ids, context=context)[0] or False

                lines_vals.append({
                    'cont_nr': line_elmnt.find('container_number').text,
                    'cont_operator': line_elmnt.find('container_operator_id').text,
                    'product_id': product and product.id or False,
                    'name' : product and product.name or False,
                    'quantity': 1,
                    'price_unit': product and product.list_price or False,
                    })
        return [(0,0,vals) for vals in lines_vals]

    def _import_data(self, cr, uid, ids, context=None):
        if not ids:
            return []
        config_obj = self.browse(cr, uid, ids, context=context)[0]
        ftp = FTP(host=config_obj.addr,user=config_obj.user, passwd=config_obj.psswd)
        outbound_path =  config_obj.outbound_path.rstrip('/') + "/"
        ftp.cwd(outbound_path + 'transfer_complete')
        module_path = __file__.split('models')[0]

        vbilling_ids = []
        for filename in ftp.nlst():
            if not re.match('^VBL_IN_\d{2}-\d{2}-\d{2}_SEQ\d{6}\.xml$',filename):
                continue
            loc_file = os.path.join(module_path, 'tmp', filename)
            with open(loc_file, 'w+') as f:
                ftp.retrlines('RETR ' + filename, f.write)
                f.close()
                vbillings = ET.parse(loc_file).getroot()
                for vbilling in vbillings.findall('vbilling'):
                    partner_name = vbilling.find('vessel_operator_id').text
                    partner_ids = self.pool.get('res.partner').search(cr, uid, [('name','=',partner_name)], context=context) \
                        or self.pool.get('res.partner').search(cr, uid, [('name','ilike',partner_name)], context=context)
                    if partner_ids:
                        partner_id = partner_ids[0]
                    else:
                        continue

                    invoice_line = self._get_invoice_lines(cr, uid, vbilling.find('lines'), context=context)
                    if vbilling.find('hatchcovers_moves') is not None and int(vbilling.find('hatchcovers_moves').text) > 0:
                        product_ids = self.pool.get('product.product').search(cr, uid, [('name','=','Hatch cover move')])
                        product = product_ids and self.pool.get('product.product').browse(cr, uid, product_ids)[0] or False
                        vals = {
                            'product_id': product and product.id or False,
                            'name' : product and product.name or False,
                            'quantity': int(vbilling.find('hatchcovers_moves').text),
                            'price_unit': product and product.list_price or False,
                        }
                        invoice_line.append((0,0,vals))
                    if vbilling.find('gearbox_count') is not None and int(vbilling.find('gearbox_count').text) > 0:
                        product_ids = self.pool.get('product.product').search(cr, uid, [('name','=','Gearbox count')])
                        product = product_ids and self.pool.get('product.product').browse(cr, uid, product_ids)[0] or False
                        vals = {
                            'product_id': product and product.id or False,
                            'name' : product and product.name or False,
                            'quantity': int(vbilling.find('gearbox_count').text),
                            'price_unit': product and product.list_price or False,
                        }
                        invoice_line.append((0,0,vals))

                    # /!\ No good, no good
                    account_id = self.pool.get('account.account').search(cr, uid, [], context=context)[0]

                    vals = {
                        'type2': 'vessel',
                        'partner_id': partner_id,
                        'account_id': account_id,
                        'call_sign': vbilling.find('call_sign').text,
                        'lloyds_nr': vbilling.find('lloyds_number').text,
                        'vessel_ID': vbilling.find('vessel_id').text,
                        'dep_time': vbilling.find('departure_time').text,
                        'berth_time': vbilling.find('berthing_time').text,
                        'date_invoice': datetime.today().strftime('%Y-%m-%d'),
                        'invoice_line': invoice_line,
                    }
                    vbilling_ids.append(self.pool.get('account.invoice').create(cr, uid, vals, context=context))
                    print 'rezgege\n'
            os.remove(loc_file)
            ftp.delete(filename)
        return vbilling_ids



    def button_import_data(self, cr, uid, ids, context=None):
        return self._import_data(cr, uid, ids, context=context)

    def cron_import_data(self, cr, uid, context=None):
        self._import_data(cr, uid,self.search(cr, uid, [('active','=',True)]), context=context)