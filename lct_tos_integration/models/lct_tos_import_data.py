

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
from lxml import etree as ET
import traceback
import re
from datetime import datetime


class lct_tos_import_data(osv.Model):
    _name = 'lct.tos.import.data'

    _columns = {
        'name': fields.char('File name', readonly=True),
        'content': fields.text('File content', readonly=True),
        'type': fields.selection([('xml','xml')], string='File type'),
        'status': fields.selection([('fail','Fail'),('success','Success'),('pending','Pending')], string='Status', readonly=True, required=True),
        'create_date': fields.date(string='Import date', readonly=True),
        'error': fields.text('Errors'),
    }

    _defaults = {
        'status': 'pending',
    }

    def process_data(self, cr, uid, ids, context=None):
        if not ids:
            return []

        for imp_data_id in ids:
            cr.execute('SAVEPOINT SP')
            imp_data = self.browse(cr, uid, imp_data_id, context=context)
            if imp_data.status != 'pending':
                continue
            filename = imp_data.name
            if re.match('^VBL_\d{6}_\d{6}\.xml$', filename):
                try:
                    root = ET.fromstring(imp_data.content)
                    self._import_vbl(cr, uid, root, context=context)

                except:
                    cr.execute('ROLLBACK TO SP')
                    imp_data_model.write(cr, uid, imp_data_id, {
                        'status': 'fail',
                        'error': traceback.format_exc(),
                        }, context=context)
                    continue
            elif re.match('^APP_\d{6}_\d{6}\.xml$', filename):
                try:
                    root = ET.fromstring(imp_data.content)
                    self._import_app(cr, uid, root, context=context)
                except:
                    cr.execute('ROLLBACK TO SP')
                    self.write(cr, uid, imp_data_id, {
                        'status': 'fail',
                        'error': traceback.format_exc(),
                        }, context=context)
                    continue
            else:
                cr.execute('ROLLBACK TO SP')
                error = 'Filename format not known.\nKnown formats are :\n    APP_YYMMDD_SEQ000.xml\n    VBL_YYMMDD_SEQ000.xml'
                self.write(cr, uid, imp_data_id, {
                    'status': 'fail',
                    'error': error,
                    }, context=context)
                continue
            self.write(cr, uid, imp_data_id, {'status': 'success'}, context=context)
            cr.execute('RELEASE SAVEPOINT SP')
            # cr.execute('COMMIT')


    def _get_elmnt_text(self, elmnt, tag):
        sub_elmnt = elmnt.find(tag)
        if sub_elmnt is not None:
            return sub_elmnt.text
        else:
            raise osv.except_osv(('Error in file %s' % self.curr_file),('Unable to find tag %s\nin element : %s' % (tag, elmnt.tag)))

    def _get_product_info(self, cr, uid, model, field, value, label):
        ids = self.pool.get(model).search(cr, uid, [(field, '=', value)])
        if not ids:
            if value:
                raise osv.except_osv(('Error in file %s' % self.curr_file), ('The following information (%s = %s) does not exist') % (label, value))
            else:
                raise osv.except_osv(('Error in file %s' % self.curr_file), ('The following information (%s) was not found') % (label,))
        return ids[0]

    def _get_product_properties(self, cr, uid, line, product_map, context=None):
        product_properties = {}

        category = self._get_elmnt_text(line, product_map['category_id'])
        category_name = 'Import' if category == 'I' else 'Export' if category == 'E' else False
        if not category_name:
            raise osv.except_osv(('Error in file %s' % self.curr_file), ('Some information (category_id) could not be found on product'))
        product_properties['category_id'] = {
            'name': category_name,
            'id': self._get_product_info(cr, uid, 'lct.product.category', 'name', category_name, 'Category')
        }

        size_size = int(self._get_elmnt_text(line, product_map['size_id']))
        product_properties['size_id'] = {
            'name': size_size,
            'id': self._get_product_info(cr, uid, 'lct.product.size', 'size', size_size, 'Size')
        }

        status = self._get_elmnt_text(line, product_map['status_id'])
        status_name = 'Full' if status == 'F' \
            else 'Empty' if status == 'E' \
            else False
        product_properties['status_id'] = {
            'name': status_name,
            'id': self._get_product_info(cr, uid, 'lct.product.status', 'name', status_name, 'Status')
        }

        type_name = self._get_elmnt_text(line, product_map['type_id'])
        product_properties['type_id'] = {
            'name': type_name,
            'id': self._get_product_info(cr, uid, 'lct.product.type', 'name', type_name, 'Type')
        }

        return product_properties

    def _get_app_lines(self, cr, uid, lines, line_map, context=None):
        product_model = self.pool.get('product.product')
        if len(lines) < 1:
            return []

        lines_vals = {}
        for line in lines.findall('line'):
            product_properties = self._get_product_properties(cr, uid, line, line_map['product_map'], context=context)
            services = {
                'Storage': self._get_elmnt_text(line, 'storage'),
                'Reefer': self._get_elmnt_text(line, 'plugged_time'),
            }
            for service, quantity in services.iteritems():
                if quantity and int(quantity) > 0:
                    product_properties['service_id'] = {
                        'name': service,
                        'id': self._get_product_info(cr, uid, 'lct.product.service', 'name', service, 'Status')
                    }
                    product_domain = [(name, '=', product_properties[name]['id']) for name in ['category_id', 'size_id', 'status_id', 'type_id', 'service_id']]
                    product_ids = product_model.search(cr, uid, product_domain, context=context)
                    product = product_ids and product_model.browse(cr, uid, product_ids, context=context)[0] or False
                    if not product:
                        raise osv.except_osv(('Error in file %s' % self.curr_file), ('No product could be found for this combination : '
                                '\n category_id : %s \n service_id : %s \n size_id : %s \n status_id : %s \n type_id : %s' % \
                                tuple(product_properties[name]['name'] for name in ['category_id',  'service_id', 'size_id', 'status_id', 'type_id'])))
                    try:
                        cont_nr_name = line.find('container_number').text
                        cont_nr_mgc_nr = (0,0,{'name': cont_nr_name})
                    except:
                        raise osv.except_osv(('Error in file %s' % self.curr_file), ('Could not find the container number'))

                    if product.name in lines_vals:
                        lines_vals[product.name]['quantity'] += int(quantity)
                        lines_vals[product.name]['cont_nr_ids'].extend([cont_nr_mgc_nr] * int(quantity))
                    else:
                        vals = {}
                        for field, tag in line_map.iteritems():
                            if isinstance(tag, str):
                                vals[field] = self._get_elmnt_text(line,tag)
                        vals['cont_nr_ids'] = [cont_nr_mgc_nr] * int(quantity)
                        account = product.property_account_income or (product.categ_id and product.categ_id.property_account_income_categ) or False
                        if account:
                            vals['account_id'] = account.id
                        else:
                            raise osv.except_osv(('Error in file %s' % self.curr_file), ('Could not find an income account on product %s ') % product.name)
                        vals.update({
                            'product_id': product.id,
                            'name' : product.name,
                            'price_unit': product.list_price,
                            'quantity': int(quantity),
                        })
                        lines_vals[product.name] = vals
        return [(0,0,vals) for vals in lines_vals.values()]

    def _get_vbl_lines(self, cr, uid, lines, line_map, context=None):
        product_model = self.pool.get('product.product')
        if len(lines) < 1:
            return []

        lines_vals = {}
        for line in lines.findall('line'):
            category = self._get_elmnt_text(line, line_map['product_map']['category_id'])
            if category == 'I':
                category_name, service_name = 'Import', 'Discharge'
            elif category == 'E':
                category_name, service_name = 'Export', 'Load'
            else:
                raise osv.except_osv(('Error in file %s' % self.curr_file), ('Some information (category_id) could not be found on product'))
            category_id = self._get_product_info(cr, uid, 'lct.product.category', 'name', category_name, 'Category Type')
            service_id = self._get_product_info(cr, uid, 'lct.product.service', 'name', service_name, 'Service')

            size_size = int(self._get_elmnt_text(line,line_map['product_map']['size_id']))
            size_id = self._get_product_info(cr, uid, 'lct.product.size', 'size', size_size, 'Size')

            status = self._get_elmnt_text(line,line_map['product_map']['status_id'])
            status_name = 'Full' if status == 'F' \
                else 'Empty' if status == 'E' \
                else False
            status_id = self._get_product_info(cr, uid, 'lct.product.status', 'name', status_name, 'Status')

            type_name = 'GP' if self._get_elmnt_text(line,line_map['product_map']['type_id']) == 'GP' \
                else False

            type_id = self._get_product_info(cr, uid, 'lct.product.type', 'name', type_name, 'Type')

            product_domain = [(name, '=', eval(name)) for name in ['category_id', 'service_id', 'size_id', 'status_id', 'type_id']]
            product_ids = product_model.search(cr, uid, product_domain, context=context)
            product = product_ids and product_model.browse(cr, uid, product_ids, context=context)[0] or False
            if not product:
                raise osv.except_osv(('Error in file %s' % self.curr_file), ('No product could be found for this combination : '
                        '\n category_id : %s \n service_id : %s \n size_id : %s \n status_id : %s \n type_id : %s' % \
                        (category_name, service_name, size_size, status_name, type_name)))
            try:
                cont_nr_name = line.find('container_number').text
                cont_nr_mgc_nr = (0,0,{'name': cont_nr_name})
            except:
                raise osv.except_osv(('Error in file %s' % self.curr_file), ('Could not find the container number'))

            if product.name in lines_vals:
                lines_vals[product.name]['quantity'] += 1
                lines_vals[product.name]['cont_nr_ids'].append(cont_nr_mgc_nr)
            else:
                vals = {}
                for field, tag in line_map.iteritems():
                    if isinstance(tag, str):
                        vals[field] = self._get_elmnt_text(line,tag)
                vals['cont_nr_ids'] = [cont_nr_mgc_nr]
                account = product.property_account_income or (product.categ_id and product.categ_id.property_account_income_categ) or False
                if account:
                    vals['account_id'] = account.id
                else:
                    raise osv.except_osv(('Error in file %s' % self.curr_file), ('Could not find an income account on product %s ') % product.name)
                vals.update({
                    'product_id': product.id,
                    'name' : product.name,
                    'price_unit': product.list_price,
                    'quantity': 1,
                })
                lines_vals[product.name] = vals
        return [(0,0,vals) for vals in lines_vals.values()]

    def _get_invoice_vals(self, cr, uid, invoice, invoice_type, context=None):
        invoice_map = {
            'partner_id': 'customer_id',
            'appoint_ref': 'appointment_reference',
            'appoint_date': 'appointment_date',
            'date_due': 'pay_through_date',
            'line_map':  {
                'product_map':{
                    'category_id': 'category',
                    'size_id': 'container_size',
                    'status_id': 'status',
                    'type_id': 'container_type',
                },
                'cont_operator': 'container_operator',
            },
        } if invoice_type == 'app' \
        else {
            'partner_id': 'vessel_operator_id',
            'call_sign': 'call_sign',
            'lloyds_nr': 'lloyds_number',
            'vessel_ID': 'vessel_id',
            'berth_time': 'berthing_time',
            'dep_time': 'departure_time',
            'line_map':  {
                'product_map':{
                    'category_id': 'transaction_category_id',
                    'size_id': 'container_size',
                    'status_id': 'container_status',
                    'type_id': 'container_type_id',
                },
                'cont_operator': 'container_operator_id',
            },
        }

        partner_model = self.pool.get('res.partner')
        vals = {}
        for field, tag in invoice_map.iteritems():
            if isinstance(tag, str):
                vals[field] = self._get_elmnt_text(invoice, tag)

        if not vals['partner_id'].isdigit():
            raise osv.except_osv(('Error in file %s' % self.curr_file), ('customer_id should be an integer'))
        partner_ids = partner_model.search(cr, uid, [('id', '=', int(vals['partner_id']))], context=context)
        if partner_ids:
            vals['partner_id'] = partner_ids[0]
        else:
            raise osv.except_osv(('Error in file %s' % self.curr_file), ('No customer with this name (%s) was found' % vals['partner_id'] ))

        invoice_line = self._get_app_lines(cr, uid, invoice.find('lines'), invoice_map['line_map'], context=context) \
                if invoice_type == 'app' \
                else self._get_vbl_lines(cr, uid, invoice.find('lines'), invoice_map['line_map'], context=context)

        partner  = partner_model.browse(cr, uid, vals['partner_id'], context=context)
        account = partner.property_account_receivable
        if account:
            vals['account_id'] = account.id
        else:
            raise osv.except_osv(('Error in file %s' % self.curr_file), ('No account receivable could be found on cutomer %s' % partner.name))

        vals.update({
            'date_invoice': datetime.today().strftime('%Y-%m-%d'),
            'invoice_line': invoice_line,
            'state': 'draft',
            'type': 'out_invoice',
        })
        return vals

    def _import_app(self, cr, uid, appointments, context=None):
        appointment_ids = []
        if not appointments.findall('appointment'):
            raise osv.except_osv(('Warning in file %s' % self.curr_file),('This file contains no appointment'))
        invoice_model = self.pool.get('account.invoice')
        for appointment in appointments.findall('appointment'):
            appointment_vals = self._get_invoice_vals(cr, uid, appointment, 'app', context=context)
            appointment_vals['type2'] = 'appointment'
            individual = appointment.find('individual_customer')
            appointment_vals['individual_cust'] = True if individual is not None and individual.text == 'IND' else False
            appointment_ids.append(invoice_model.create(cr, uid, appointment_vals, context=context))
        return appointment_ids

    def _import_vbl(self, cr, uid, vbillings, context=None):
        vbilling_ids = []
        if not vbillings.findall('vbilling'):
            raise osv.except_osv(('Warning in file %s' % self.curr_file),('This file contains no vessel billing'))
        product_model = self.pool.get('product.product')
        invoice_model = self.pool.get('account.invoice')
        for vbilling in vbillings.findall('vbilling'):
            vbilling_vals = self._get_invoice_vals(cr, uid, vbilling, 'vbl', context=context)
            vbilling_vals['type2'] = 'vessel'
            if vbilling.find('hatchcovers_moves') is not None and int(self._get_elmnt_text(vbilling, 'hatchcovers_moves')) > 0:
                product_ids = product_model.search(cr, uid, [('name', '=', 'Hatch cover move')], context=context)
                if not product_ids:
                    raise osv.except_osv(('Error in file %s' % self.curr_file), ('No product found for "Hatch cover move"'))
                product = product_model.browse(cr, uid, product_ids, context=context)[0]
                line_vals = {
                    'product_id': product.id,
                    'name' : product.name,
                    'quantity': int(self._get_elmnt_text(vbilling, 'hatchcovers_moves')),
                    'price_unit': product.list_price,
                }
                account = product.property_account_income or (product.categ_id and product.categ_id.property_account_income_categ) or False
                if account:
                    line_vals['account_id'] = account.id
                else:
                    raise osv.except_osv(('Error in file %s' % self.curr_file), ('Could not find an income account on product %s ') % product.name)
                vbilling_vals['invoice_line'].append((0,0,line_vals))
            if vbilling.find('gearbox_count') is not None and int(self._get_elmnt_text(vbilling, 'gearbox_count')) > 0:
                product_ids = product_model.search(cr, uid, [('name', '=', 'Gearbox count')], context=context)
                if not product_ids:
                    raise osv.except_osv(('Error in file %s' % self.curr_file), ('No product found for "Gearbox count"'))
                product = product_model.browse(cr, uid, product_ids, context=context)[0]
                line_vals = {
                    'product_id': product.id,
                    'name' : product.name,
                    'quantity': int(self._get_elmnt_text(vbilling, 'gearbox_count')),
                    'price_unit': product.list_price,
                }
                account = product.property_account_income or (product.categ_id and product.categ_id.property_account_income_categ) or False
                if account:
                    line_vals['account_id'] = account.id
                else:
                    raise osv.except_osv(('Error in file %s' % self.curr_file), ('Could not find an income account on product %s ') % product.name)
                vbilling_vals['invoice_line'].append((0,0,line_vals))
            vbilling_ids.append(invoice_model.create(cr, uid, vbilling_vals, context=context))
        return vbilling_ids