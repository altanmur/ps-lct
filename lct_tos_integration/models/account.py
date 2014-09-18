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
from datetime import datetime
import re

class lct_container_number(osv.osv):
    _name = 'lct.container.number'

    _columns = {
        'name': fields.char('Container Number'),
        'date_start': fields.date('Arrival date'),
        'pricelist_qty': fields.integer('Quantity', help="Quantity used for pricelist computation"),
        'cont_operator': fields.char('Container operator'),
        'invoice_line_id': fields.many2one('account.invoice.line', string="Invoice line", ondelete="cascade", required=True),
        'oog_coef': fields.float('Out of Gauge coefficient'),
        'invoice_id': fields.related('invoice_line_id', 'invoice_id', string='Invoice'),
    }

    _defaults = {
        'oog_coef': 1.,
    }

    def _check_unique_invoice(self, cr, uid, ids, context=None):
        for cont_nr in self.browse(cr, uid, ids, context=context):
            other_nr_ids = self.search(cr, uid, [('name','=',cont_nr.name), ('invoice_id', '!=', False)], context=context)
            other_nrs = self.browse(cr, uid, other_nr_ids, context=context)
            if other_nrs and any((other_nr.invoice_id.id != cont_nr.invoice_id.id for other_nr in other_nrs)):
                return False
        return True

    _constraints = [
        (_check_unique_invoice, 'A container number can not math different invoices', ['name', 'invoice_id']),
    ]


class account_invoice_line(osv.osv):
    _inherit = 'account.invoice.line'

    _columns = {
        'cont_nr_ids': fields.one2many('lct.container.number', 'invoice_line_id', 'Containers'),
        'book_nr': fields.char('Booking number'),
    }


class account_voucher(osv.osv):
    _inherit = 'account.voucher'

    _columns = {
        'cashier_rcpt_nr': fields.char('Cashier receipt number'),
    }

    def create(self, cr, uid, vals, context=None):
        if 'cashier_rcpt_nr' not in vals:
            vals['cashier_rcpt_nr'] = self.pool.get('ir.sequence').get_next_by_xml_id(cr, uid, 'lct_tos_integration', 'sequence_cashier_receipt_number', context=context)
        return super(account_voucher, self).create(cr, uid, vals, context=context)

    def button_proforma_voucher(self, cr, uid, ids, context=None):
        res = super(account_voucher, self).button_proforma_voucher(cr, uid, ids, context=context)
        if not ids:
            return res

        invoice_id = context.get('invoice_id', False)
        if invoice_id:
            inv = self.pool.get('account.invoice').browse(cr, uid, invoice_id, context=context)
            if inv.type2 != 'appointment':
                return res
            amount = 0.0
            for payment in inv.payment_ids:
                amount += payment.credit - payment.debit
            if amount >= inv.amount_total:
                self.pool.get('ftp.config').export_app(cr, uid, invoice_id, ids[0], context=context)
        return res


class account_invoice(osv.osv):
    _inherit = 'account.invoice'

    _columns = {
        'type2': fields.selection([
            ('vessel','Vessel Billing'),
            ('appointment','Appointment')
            ], 'Type of invoice'),
        'call_sign': fields.char('Call sign'),
        'lloyds_nr': fields.char('Lloyds number'),
        'vessel_ID': fields.char('Vessel ID'),
        'berth_time': fields.datetime('Berthing time'),
        'dep_time': fields.datetime('Departure time'),
        'individual_cust': fields.boolean('Individual customer'),
        'appoint_ref': fields.char('Appointment reference'),
        'appoint_date': fields.datetime('Appointment date'),
        'invoice_line_vessel': fields.related('invoice_line', type='one2many', relation='account.invoice.line', string="Invoice lines"),
        'invoice_line_appoint': fields.related('invoice_line', type='one2many', relation='account.invoice.line', string="Invoice lines"),
    }

    def _get_elmnt_text(self, elmnt, tag):
        sub_elmnt = elmnt.find(tag)
        if sub_elmnt is not None:
            return sub_elmnt.text
        else:
            raise osv.except_osv(('Error'),('Unable to find tag %s\nin element : %s' % (tag, elmnt.tag)))

    def _get_product_info(self, cr, uid, model, field, value, label):
        ids = self.pool.get(model).search(cr, uid, [(field, '=', value)])
        if not ids:
            if value:
                raise osv.except_osv(('Error'), ('The following information (%s = %s) does not exist') % (label, value))
            else:
                raise osv.except_osv(('Error'), ('The following information (%s) was not found') % (label,))
        return ids[0]

    def _product_category(self, category):
        return 'Import' if category == 'I' else \
                'Export' if category == 'E' else \
                'Transshipment' if category == 'T' else \
                'Restowage & Shifting' if category == 'R' else \
                False

    def _product_status(self, status):
        return 'Full' if status == 'F' else \
               'Empty' if status == 'E' else \
               False

    def _get_product_properties(self, cr, uid, line, product_map, context=None):
        product_properties = {}

        category = self._get_elmnt_text(line, product_map['category_id'])
        category_name = self._product_category(category)

        if not category_name:
            raise osv.except_osv(('Error'), ('Some information (category_id) could not be found on product'))
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
        status_name = self._product_status(status)
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

    def _get_app_lines(self, cr, uid, lines, line_map, partner, context=None):
        if len(lines) < 1:
            return []

        product_model = self.pool.get('product.product')
        pricelist_model = self.pool.get('product.pricelist')
        pricelist = partner.property_product_pricelist

        lines_vals = {}
        for line in lines.findall('line'):
            product_properties = self._get_product_properties(cr, uid, line, line_map['product_map'], context=context)
            services = {
                'Storage': self._get_elmnt_text(line, 'storage'),
                'Reefer electricity': self._get_elmnt_text(line, 'plugged_time'),
            }
            for service, quantity in services.iteritems():
                if quantity and quantity.isdigit() and int(quantity) > 0:
                    product_properties['service_id'] = {
                        'name': service,
                        'id': self._get_product_info(cr, uid, 'lct.product.service', 'name', service, 'Status')
                    }
                    product_domain = [(name, '=', product_properties[name]['id']) for name in ['category_id', 'size_id', 'status_id', 'type_id', 'service_id']]
                    product_ids = product_model.search(cr, uid, product_domain, context=context)
                    product = product_ids and product_model.browse(cr, uid, product_ids, context=context)[0] or False
                    if not product:
                        raise osv.except_osv(('Error'), ('No product could be found for this combination : '
                                '\n category_id : %s \n service_id : %s \n size_id : %s \n status_id : %s \n type_id : %s' % \
                                tuple(product_properties[name]['name'] for name in ['category_id',  'service_id', 'size_id', 'status_id', 'type_id'])))

                    cont_nr = (0, 0, {
                                'name': self._get_elmnt_text(line, 'container_number'),
                                'pricelist_qty': int(quantity),
                                'cont_operator': self._get_elmnt_text(line, 'container_operator'),
                            })
                    if product.id in lines_vals:
                        lines_vals[product.id]['cont_nr_ids'].append(cont_nr)
                    else:
                        vals = {}
                        for field, tag in line_map.iteritems():
                            if isinstance(tag, str):
                                vals[field] = self._get_elmnt_text(line, tag)
                        account = product.property_account_income or (product.categ_id and product.categ_id.property_account_income_categ) or False
                        if account:
                            vals['account_id'] = account.id
                        else:
                            raise osv.except_osv(('Error'), ('Could not find an income account on product %s ') % product.name)
                        vals.update({
                            'product_id': product.id,
                            'name' : product.name,
                            'cont_nr_ids': [cont_nr],
                        })
                        lines_vals[product.id] = vals

        for vals in lines_vals.values():
            qties = [cont_nr[2]['pricelist_qty'] for cont_nr in vals['cont_nr_ids']]
            vals.update({
                'price_unit': pricelist_model.tariff_price_get(cr, uid, partner.id, vals['product_id'], len(qties), qties, context=context),
                'quantity': len(qties)
                })

        return [(0,0,vals) for vals in lines_vals.values()]

    def _vbl_service_by_category(self, category):
        return ('Import', 'Discharge') if category == 'I' else \
               ('Export', 'Load') if category == 'E' else \
               ('Transshipment', 'Discharge') if category == 'T' else \
               ('Restowage & Shifting', 'Shifting from cell to cell') if category == R'' else \
               (False, False)

    def _get_vbl_lines(self, cr, uid, lines, line_map, partner, context=None):
        if len(lines) < 1:
            return []

        product_model = self.pool.get('product.product')
        pricelist_model = self.pool.get('product.pricelist')
        pricelist = partner.property_product_pricelist

        lines_vals = {}
        category_name, service_name = ('', '')
        for line in lines.findall('line'):
            category = self._get_elmnt_text(line, line_map['product_map']['category_id'])
            category_name, service_name = self._vbl_service_by_category(category)
            if not category_name:
                raise osv.except_osv(('Error'), ('Some information (category_id) could not be found on product'))
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
            products = product_ids and [product_model.browse(cr, uid, product_ids, context=context)[0]] or False
            if not products:
                raise osv.except_osv(('Error'), ('No product could be found for this combination : '
                        '\n category_id : %s \n service_id : %s \n size_id : %s \n status_id : %s \n type_id : %s' % \
                        (category_name, service_name, size_size, status_name, type_name)))
            cont_nr = (0, 0, {
                                'name': self._get_elmnt_text(line, 'container_number'),
                                'pricelist_qty': 1,
                                'cont_operator': self._get_elmnt_text(line, 'container_operator_id'),
                                'oog_coef': 3. if self._get_elmnt_text(line, 'oog') == "YES" else 1.,
                            })
            if self._get_elmnt_text(line, 'bundles') == "YES":
                service_id = self._get_product_info(cr, uid, 'lct.product.service', 'name', 'Bundle', 'Service')
                product_domain = [(name, '=', eval(name)) for name in ['category_id', 'service_id', 'size_id', 'status_id', 'type_id']]
                product_ids = product_model.search(cr, uid, product_domain, context=context)
                product = product_ids and product_model.browse(cr, uid, product_ids, context=context)[0] or False
                if not products:
                    raise osv.except_osv(('Error'), ('No product could be found for this combination : '
                            '\n category_id : %s \n service_id : %s \n size_id : %s \n status_id : %s \n type_id : %s' % \
                            (category_name, 'Bundle', size_size, status_name, type_name)))
                products.append(product)
            for product in products:
                if product.id in lines_vals:
                    lines_vals[product.id]['cont_nr_ids'].append(cont_nr)
                else:
                    vals = {}
                    for field, tag in line_map.iteritems():
                        if isinstance(tag, str):
                            vals[field] = self._get_elmnt_text(line,tag)

                    account = product.property_account_income or (product.categ_id and product.categ_id.property_account_income_categ) or False
                    if account:
                        vals['account_id'] = account.id
                    else:
                        raise osv.except_osv(('Error'), ('Could not find an income account on product %s ') % product.name)
                    vals.update({
                        'product_id': product.id,
                        'name' : product.name,
                        'cont_nr_ids': [cont_nr],
                    })
                    lines_vals[product.id] = vals

        for vals in lines_vals.values():
            qties = [cont_nr[2]['pricelist_qty'] for cont_nr in vals['cont_nr_ids']]
            vals.update({
                'price_unit': pricelist_model.tariff_price_get(cr, uid, partner.id, vals['product_id'], len(qties), qties, context=context),
                'quantity': len(qties)
                })

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
            },
        }
        vals = {}
        for field, tag in invoice_map.iteritems():
            if isinstance(tag, str):
                vals[field] = self._get_elmnt_text(invoice, tag)
        if not vals['partner_id'].isdigit():
            raise osv.except_osv(('Error'), (invoice_map['partner_id'] + ' should be a number'))
        partner = self.pool.get('res.partner').browse(cr, uid, int(vals['partner_id']), context=context)
        if partner.exists():
            vals['partner_id'] = partner.id

        else:
            raise osv.except_osv(('Error'), ('No customer with this name (%s) was found' % vals['partner_id'] ))

        invoice_line = self._get_app_lines(cr, uid, invoice.find('lines'), invoice_map['line_map'], partner, context=context) \
                if invoice_type == 'app' \
                else self._get_vbl_lines(cr, uid, invoice.find('lines'), invoice_map['line_map'], partner, context=context)

        account = partner.property_account_receivable
        if account:
            vals['account_id'] = account.id
        else:
            raise osv.except_osv(('Error'), ('No account receivable could be found on cutomer %s' % partner.name))

        vals.update({
            'date_invoice': datetime.today().strftime('%Y-%m-%d'),
            'invoice_line': invoice_line,
            'state': 'draft',
            'type': 'out_invoice',
        })
        return vals

    def xml_to_app(self, cr, uid, imp_data_id, context=None):
        imp_data = self.pool.get('lct.tos.import.data').browse(cr, uid, imp_data_id, context=context)
        content = re.sub('<\?xml.*\?>','',imp_data.content).replace(u"\ufeff","")
        appointments = ET.fromstring(content)
        appointment_ids = []
        invoice_model = self.pool.get('account.invoice')
        for appointment in appointments.findall('appointment'):
            appointment_vals = self._get_invoice_vals(cr, uid, appointment, 'app', context=context)
            appointment_vals['type2'] = 'appointment'
            individual = {
                'IND': True,
                'STD': False,
            }.get(self._get_elmnt_text(appointment, 'individual_customer'), None)
            if individual is None:
                raise osv.except_osv(('Error'), ('Invalid text in tag "individual_customer"'))
            appointment_vals['individual_cust'] = individual
            appointment_ids.append(invoice_model.create(cr, uid, appointment_vals, context=context))
        return appointment_ids

    def xml_to_vbl(self, cr, uid, imp_data_id, context=None):
        imp_data = self.pool.get('lct.tos.import.data').browse(cr, uid, imp_data_id, context=context)
        content = re.sub('<\?xml.*\?>','',imp_data.content).replace(u"\ufeff","")
        vbillings = ET.fromstring(content)
        vbilling_ids = []
        product_model = self.pool.get('product.product')
        invoice_model = self.pool.get('account.invoice')
        invoiceline_model = self.pool.get('account.invoice.line')
        pricelist_model = self.pool.get('product.pricelist')
        partner_model = self.pool.get('res.partner')
        yard_model = self.pool.get('lct.tos.yardactivity')
        for vbilling in vbillings.findall('vbilling'):
            vbilling_vals = self._get_invoice_vals(cr, uid, vbilling, 'vbl', context=context)
            vbilling_vals['type2'] = 'vessel'
            partner = partner_model.browse(cr, uid, vbilling_vals['partner_id'])
            pricelist = partner.property_product_pricelist

            n_hcm = 0
            try:
                n_hcm = int(self._get_elmnt_text(vbilling, 'hatchcovers_moves'))
                assert n_hcm > 0
            except:
                pass
            else:
                product_ids = product_model.search(cr, uid, [('name', '=', 'Hatch Cover Move')], context=context)
                if not product_ids:
                    raise osv.except_osv(('Error'), ('No product found for "Hatch Cover Move"'))
                product = product_model.browse(cr, uid, product_ids, context=context)[0]
                line_vals = {
                    'product_id': product.id,
                    'name' : product.name,
                    'quantity': n_hcm,
                    'price_unit': pricelist_model.price_get_multi(cr, uid, [pricelist.id], [(product.id, n_hcm, partner.id)], context=context)[product.id][pricelist.id],
                }
                account = product.property_account_income or (product.categ_id and product.categ_id.property_account_income_categ) or False
                if account:
                    line_vals['account_id'] = account.id
                else:
                    raise osv.except_osv(('Error'), ('Could not find an income account on product %s ') % product.name)
                vbilling_vals['invoice_line'].append((0,0,line_vals))

            n_gc = 0
            try:
                n_gc = int(self._get_elmnt_text(vbilling, 'gearbox_count'))
                assert n_gc > 0
            except:
                pass
            else:
                product_ids = product_model.search(cr, uid, [('name', '=', 'Gearbox Count')], context=context)
                if not product_ids:
                    raise osv.except_osv(('Error'), ('No product found for "Gearbox Count"'))
                product = product_model.browse(cr, uid, product_ids, context=context)[0]
                line_vals = {
                    'product_id': product.id,
                    'name' : product.name,
                    'quantity': n_gc,
                    'price_unit': pricelist_model.price_get_multi(cr, uid, [pricelist.id], [(product.id, n_gc, partner.id)], context=context)[product.id][pricelist.id],
                }
                account = product.property_account_income or (product.categ_id and product.categ_id.property_account_income_categ) or False
                if account:
                    line_vals['account_id'] = account.id
                else:
                    raise osv.except_osv(('Error'), ('Could not find an income account on product %s ') % product.name)
                vbilling_vals['invoice_line'].append((0,0,line_vals))
            vbilling_ids.append(invoice_model.create(cr, uid, vbilling_vals, context=context))
        #Add yard activities on created invoices
        invoiceline_ids = invoiceline_model.search(cr, uid, [('invoice_id', 'in', vbilling_ids)], context=context)
        for line in invoiceline_model.browse(cr, uid, invoiceline_ids, context=context):
            for container in line.cont_nr_ids:
                yard_ids = yard_model.search(cr, uid, ['container_number', '=', container.name], context=context)
                yards = yard_model.browse(cr, uid, yard_ids, context=context)
                for yard in yards:
                    pass
        return vbilling_ids
