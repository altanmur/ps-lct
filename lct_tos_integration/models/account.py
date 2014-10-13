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
        'quantity': fields.integer('Quantity', help="Real quantity of product on invoice line"),
        'pricelist_qty': fields.integer('Quantity', help="Quantity used for pricelist computation"),
        'cont_operator': fields.char('Container operator'),
        'call_sign': fields.char('Call sign'),
        'lloyds_nr': fields.char('Lloyds number'),
        'vessel_ID': fields.char('Vessel ID'),
        'berth_time': fields.datetime('Berthing time'),
        'dep_time': fields.datetime('Departure time'),
        'invoice_line_id': fields.many2one('account.invoice.line', string="Invoice line"),
    }


class account_invoice_line(osv.osv):
    _inherit = 'account.invoice.line'

    _columns = {
        'cont_nr_ids': fields.one2many('lct.container.number', 'invoice_line_id', 'Containers'),
        'book_nr': fields.char('Booking number'),
    }

    def _merge_vbl_line_pair(self, cr, uid, id1, id2, context=None):
        cont_nr_model = self.pool.get('lct.container.number')
        line1, line2 = self.browse(cr, uid, [id1, id2], context=context)
        cont_nr_model.write(cr, uid, [cont_nr.id for cont_nr in line2.cont_nr_ids],
                            {'invoice_line_id': line1.id}, context=context)
        quantities = [line1.quantity, line2.quantity]
        prices = [line1.price_unit, line2.price_unit]
        quantity = sum(quantities)
        price_unit = (prices[0]*quantities[0] + prices[1]*quantities[1])/quantity
        self.write(cr, uid, [line1.id], {
                        'quantity': quantity,
                        'price_unit': price_unit,
                   }, context=context)
        self.unlink(cr, uid, [line2.id], context=context)
        return line1.id


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
            ('appointment','Appointment'),
            ('dockage', 'Vessel Dockage'),
            ('yactivity', 'Yard Activity'),
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
        'voyage_number_in': fields.char('Voyage Number In'),
        'voyage_number_out': fields.char('Voyage Number Out'),
        'off_window': fields.boolean('OFF window'),
        'loa': fields.integer('LOA'),
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

    def _get_product_properties(self, cr, uid, line, product_map, context=None):
        product_properties = {}

        category = self._get_elmnt_text(line, product_map['category_id'])
        category_name = 'Import' if category == 'I' else 'Export' if category == 'E' else False
        if not category_name:
            raise osv.except_osv(('Error'), ('Some information (category_id) could not be found on product'))
        product_properties['category_id'] = {
            'name': category_name,
            'id': category_name and self._get_product_info(cr, uid, 'lct.product.category', 'name', category_name, 'Category') or False
        }

        size_size = int(self._get_elmnt_text(line, product_map['size_id']))
        product_properties['size_id'] = {
            'name': size_size,
            'id': size_size and self._get_product_info(cr, uid, 'lct.product.size', 'size', size_size, 'Size') or False
        }

        status = self._get_elmnt_text(line, product_map['status_id'])
        status_name = 'Full' if status == 'F' \
            else 'Empty' if status == 'E' \
            else False
        product_properties['status_id'] = {
            'name': status_name,
            'id': status_name and self._get_product_info(cr, uid, 'lct.product.status', 'name', status_name, 'Status') or False
        }

        type_name = self._get_elmnt_text(line, product_map['type_id'])
        product_properties['type_id'] = {
            'name': type_name,
            'id': type_name and self._get_product_info(cr, uid, 'lct.product.type', 'name', type_name, 'Type') or False
        }

        return product_properties

    def _get_partner(self, cr, uid, elmnt, tag, context=None):
        partner_id = self._get_elmnt_text(elmnt, tag)
        if not partner_id or not partner_id.isdigit():
            raise osv.except_osv(('Error'), (tag + ' should be a number'))
        partner_id = int(partner_id)
        if not self.pool.get('res.partner').search(cr, uid, [('id','=',partner_id)]):
            raise osv.except_osv(('Error'), ('No partner found with this id: ', partner_id))
        return partner_id

    def _xml_get_digit(self, elmt, tag):
        try:
            res = int(self._get_elmnt_text(elmt, tag))
        except:
            res = 0
        return res

    def _get_status(self, cr, uid, status):
        imd_model = self.pool.get('ir.model.data')
        if status == 'F':
            xml_id = 'lct_product_status_full'
        elif status == 'E':
            xml_id = 'lct_product_status_empty'
        else:
            return False
        return imd_model.get_record_id(cr, uid, 'lct_tos_integration', xml_id)

    def _get_size(self, cr, uid, size):
        imd_model = self.pool.get('ir.model.data')
        if size == '20':
            xml_id = 'lct_product_size_20'
        elif size == '40':
            xml_id = 'lct_product_size_40'
        else:
            return False
        return imd_model.get_record_id(cr, uid, 'lct_tos_integration', xml_id)

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
            qty_tot = 0.0
            qties = [cont_nr[2]['pricelist_qty'] for cont_nr in vals['cont_nr_ids']]
            price = sum((qty*pricelist_model.price_get_multi(cr, uid, [pricelist.id], [(vals['product_id'], qty, partner.id)], context=context)[vals['product_id']][pricelist.id] for qty in qties))
            vals.update({
                'price_unit': price/len(qties),
                'quantity': len(qties)
                })

        return [(0,0,vals) for vals in lines_vals.values()]

    def _get_vcl_lines(self, cr, uid, vals, partner, context=None):
        product_model = self.pool.get('product.product')
        pricelist_model = self.pool.get('product.pricelist')
        category_model = self.pool.get('lct.product.category')
        sub_category_model = self.pool.get('lct.product.sub.category')

        pricelist = partner.property_product_pricelist

        category_id = category_model.search(cr, uid, [('name', '=', 'Dockage')], context=context)
        if len(category_id) != 1:
            raise osv.except_osv(('Error'), ('The category "Dockage" doesnt exist'))
        category_id = category_id[0]

        if not vals['loa']:
            raise osv.except_osv(('Error'), ('There is no loa defined for the VCL'))
        vals['loa'] = int(vals['loa'])
        sub_category_id = False
        if vals['loa'] <= 160:
            sub_category_id = sub_category_model.search(cr, uid, [('name', '=', 'LOA 160m and below')], context=context)
        elif vals['loa'] > 160 and vals['loa'] < 360:
            sub_category_id = sub_category_model.search(cr, uid, [('name', '=', 'LOA 160m to 360m')], context=context)
        elif vals['loa'] >= 360:
            sub_category_id = sub_category_model.search(cr, uid, [('name', '=', 'LOA 360m and above')], context=context)
        if not sub_category_id:
            raise osv.except_osv(('Error'), ('Cannot find sub category for the VCL'))
        sub_category_id = sub_category_id[0]

        product_ids = product_model.search(cr, uid, [('category_id', '=', category_id), ('sub_category_id', '=', sub_category_id)], context=context)
        if not product_ids:
            raise osv.except_osv(('Error'), ('No product could be found for this VCL'))
        product = product_model.browse(cr, uid, product_ids, context=context)[0]

        account = product.property_account_income or (product.categ_id and product.categ_id.property_account_income_categ) or False
        if not account:
            raise osv.except_osv(('Error'), ('Could not find an income account on product %s ') % product.name)

        price_unit = pricelist_model.price_get_multi(cr, uid, [pricelist.id], [(product.id, 1, partner.id)], context=context)[product.id][pricelist.id]

        line = {
            'quantity': 1,
            'price_unit': price_unit,
            'product_id': product.id,
            'name': product.name,
            'account_id': account.id,
        }
        return [(0,0,line)]


    def _get_invoice_vals(self, cr, uid, invoice, invoice_type, context=None):
        invoice_map = {}
        if invoice_type == 'app':
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
            }
        elif invoice_type == 'vcl':
            invoice_map = {
                'partner_id': 'vessel_operator_id',
                'call_sign': 'call_sign',
                'lloyds_nr': 'lloyds_number',
                'vessel_ID': 'vessel_id',
                'berth_time': 'berthing_time',
                'dep_time': 'departure_time',
                'voyage_number_in': 'voyage_number_in',
                'voyage_number_out': 'voyage_number_out',
                'loa': 'loa',
                'off_window': 'off_window',
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
            raise osv.except_osv(('Error'), ('No customer with this id (%s) was found' % vals['partner_id'] ))

        invoice_line = []
        if invoice_type == 'app':
            invoice_line = self._get_app_lines(cr, uid, invoice.find('lines'), invoice_map['line_map'], partner, context=context)
        elif invoice_type == 'vcl':
            invoice_line = self._get_vcl_lines(cr, uid, vals, partner, context=context)

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


    # APP

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


    # VBL

    def _get_vbl_category_service(self, cr, uid, category):
        imd_model = self.pool.get('ir.model.data')
        module = 'lct_tos_integration'
        if category == 'I':
            category_id = imd_model.get_record_id(cr, uid, module, 'lct_product_category_import')
            service_ids = [imd_model.get_record_id(cr, uid, module, 'lct_product_service_discharge')]
        elif category == 'E':
            category_id = imd_model.get_record_id(cr, uid, module, 'lct_product_category_export')
            service_ids = [imd_model.get_record_id(cr, uid, module, 'lct_product_service_load')]
        elif category == 'T':
            category_id = imd_model.get_record_id(cr, uid, module, 'lct_product_category_transshipment')
            service_ids = [imd_model.get_record_id(cr, uid, module, 'lct_product_service_discharge'), imd_model.get_record_id(cr, uid, module, 'lct_product_service_reload')]
        elif category == 'R':
            category_id = imd_model.get_record_id(cr, uid, module, 'lct_product_category_restowageshifting')
            service_ids = [imd_model.get_record_id(cr, uid, module, 'lct_product_service_restow')]
        else:
            category_id = False
            service_ids = [False]
        return (category_id, service_ids)

    def _get_vbl_type(self, cr, uid, p_type):
        imd_model = self.pool.get('ir.model.data')
        module = 'lct_tos_integration'
        if p_type == 'GP':
            type_id = imd_model.get_record_id(cr, uid, module, 'lct_product_type_gp')
        elif p_type == 'RE':
            type_id = imd_model.get_record_id(cr, uid, module, 'lct_product_type_reeferdg')
        else:
            type_id = False
        return type_id

    def xml_to_vbl(self, cr, uid, imp_data_id, context=None):
        product_model = self.pool.get('product.product')
        invoice_model = self.pool.get('account.invoice')
        pricelist_model = self.pool.get('product.pricelist')
        partner_model = self.pool.get('res.partner')
        cont_nr_model = self.pool.get('lct.container.number')
        imd_model = self.pool.get('ir.model.data')
        pending_yac_model = self.pool.get('lct.pending.yard.activity')
        module = 'lct_tos_integration'

        imp_data = self.pool.get('lct.tos.import.data').browse(cr, uid, imp_data_id, context=context)
        content = re.sub('<\?xml.*\?>','',imp_data.content).replace(u"\ufeff","")
        vbillings = ET.fromstring(content)

        invoice_lines = {}
        for vbilling in vbillings.findall('vbilling'):
            partner_id = self._get_partner(cr, uid, vbilling, 'vessel_operator_id')
            partner = partner_model.browse(cr, uid, partner_id, context=context)

            vessel_ID = self._get_elmnt_text(vbilling, 'vessel_id')
            cont_nr_vals ={
                'call_sign': self._get_elmnt_text(vbilling, 'call_sign'),
                'lloyds_nr': self._get_elmnt_text(vbilling, 'lloyds_number'),
                'vessel_ID': vessel_ID,
                'berth_time': self._get_elmnt_text(vbilling, 'berthing_time'),
                'dep_time': self._get_elmnt_text(vbilling, 'departure_time'),
            }
            n_hcm = self._xml_get_digit(vbilling, 'hatchcovers_moves')
            if n_hcm > 0:
                service_id = imd_model.get_record_id(cr, uid, module, 'lct_product_service_hatchcovermoves')
                product_id = product_model.search(cr, uid, [('service_id', '=', service_id)], context=context)
                if not product_id:
                    raise osv.except_osv(('Error'), ('The product "Hatch Cover Moves" cannot be found.'))
                product_id = product_id[0]
                vals = dict(cont_nr_vals, pricelist_qty=n_hcm, quantity=n_hcm)
                cont_nr_id = cont_nr_model.create(cr, uid, vals, context=context)
                invoice_lines[partner_id] = {product_id: [cont_nr_id]}

            n_gbc = self._xml_get_digit(vbilling, 'gearbox_count')
            if n_gbc > 0:
                service_id = imd_model.get_record_id(cr, uid, module, 'lct_product_service_gearboxcount')
                product_id = product_model.search(cr, uid, [('service_id', '=', service_id)], context=context)
                if not product_id:
                    raise osv.except_osv(('Error'), ('The product "Gearbox Count" cannot be found.'))
                product_id = product_id[0]
                vals = dict(cont_nr_vals, pricelist_qty=n_gbc, quantity=n_gbc)
                cont_nr_id = cont_nr_model.create(cr, uid, vals, context=context)
                if partner_id not in invoice_lines:
                    invoice_lines[partner_id] = {product_id: [cont_nr_id]}
                else:
                    invoice_lines[partner_id][product_id] = [cont_nr_id]

            lines = vbilling.find('lines')
            if lines is None:
                continue
            for line in lines.findall('line'):
                partner_id = self._get_partner(cr, uid, line, 'container_operator_id', context=context)

                cont_nr_name = self._get_elmnt_text(line, 'container_number')
                cont_nr_vals['name'] = cont_nr_name
                pricelist_qty = 1

                category = self._get_elmnt_text(line, 'transaction_category_id')
                if category == 'R':
                    partner_id = self._get_partner(cr, uid, vbilling, 'vessel_operator_id', context=context)
                category_id, service_ids = self._get_vbl_category_service(cr, uid, category)

                size = self._get_elmnt_text(line, 'container_size')
                size_id = self._get_size(cr, uid, size)

                status = self._get_elmnt_text(line, 'container_status')
                status_id = self._get_status(cr, uid, status)

                if status != 'E':
                    p_type = self._get_elmnt_text(line, 'container_type_id')
                    type_id = self._get_vbl_type(cr, uid, p_type)
                else:
                    type_id = False
                properties = {
                    'category_id': category_id,
                    'service_ids': service_ids,
                    'size_id': size_id,
                    'status_id': status_id,
                    'type_id': type_id,
                }
                product_ids = product_model.get_products_by_properties(cr, uid, dict(properties), context=context)
                if not all(product_ids):
                    error  = 'One or more product(s) could not be found with these combinations: '
                    error += ', '.join([key + ': ' + str(val) for key, val in properties.iteritems()])
                    raise osv.except_osv(('Error'), (error))

                bundle = self._get_elmnt_text(line, 'bundles')
                if bundle=='YES':
                    product_ids.append(imd_model.get_record_id(cr, uid, module, 'bundle'))

                if partner_id not in invoice_lines:
                    invoice_lines[partner_id] = {}
                for product_id in product_ids:
                    if product_id not in invoice_lines[partner_id]:
                        invoice_lines[partner_id][product_id] = []
                    cont_nr_id = cont_nr_model.create(cr, uid, dict(cont_nr_vals, pricelist_qty=1, quantity=1), context=context)
                    invoice_lines[partner_id][product_id].append(cont_nr_id)
                if category in ['E', 'T']:
                    domain = [('vessel_ID', '=', vessel_ID), ('name', '=', cont_nr_name), ('status', '=', 'pending')]
                    pending_yac_ids = pending_yac_model.search(cr, uid, domain, context=context)

                    reefe_properties = dict(properties)
                    expst_properties = dict(properties)

                    reefe_properties['service_ids'] = [imd_model.get_record_id(cr, uid, module, 'lct_product_service_reeferelectricity')]
                    reefe_properties['status_id'] = False
                    reefe_properties['type_id'] = False
                    expst_properties['service_ids'] = [imd_model.get_record_id(cr, uid, module, 'lct_product_service_storage')]

                    reefe_product_id = product_model.get_products_by_properties(cr, uid, reefe_properties, context=context)[0]
                    expst_product_id = product_model.get_products_by_properties(cr, uid, expst_properties, context=context)[0]

                    reefe_qties = []
                    expst_qties = []
                    for pending_yac in pending_yac_model.browse(cr, uid, pending_yac_ids, context=context):
                        if pending_yac.type == 'reefe':
                            reefe_qties.append(pending_yac.plugged_time)
                        elif pending_yac.type == 'expst':
                            dep_date = datetime.strptime(pending_yac.dep_timestamp, "%Y-%m-%d %H:%M:%S").date()
                            arr_date = datetime.strptime(pending_yac.arr_timestamp, "%Y-%m-%d %H:%M:%S").date()
                            expst_qties.append((dep_date - arr_date).days + 1)
                    if reefe_qties:
                        if reefe_product_id not in invoice_lines[partner_id]:
                            invoice_lines[partner_id][reefe_product_id] = []
                        for quantity in reefe_qties:
                            cont_nr_id = cont_nr_model.create(cr, uid, dict(cont_nr_vals, pricelist_qty=quantity, quantity=quantity), context=context)
                            invoice_lines[partner_id][reefe_product_id].append(cont_nr_id)
                    if expst_qties:
                        if expst_product_id not in invoice_lines[partner_id]:
                            invoice_lines[partner_id][expst_product_id] = []
                        for quantity in expst_qties:
                            cont_nr_id = cont_nr_model.create(cr, uid, dict(cont_nr_vals, pricelist_qty=quantity, quantity=quantity), context=context)
                            invoice_lines[partner_id][expst_product_id].append(cont_nr_id)

                    pending_yac_model.write(cr, uid, pending_yac_ids, {'status': 'processed'}, context=context)

        invoice_ids = self._create_invoices(cr, uid, invoice_lines, context=context)
        invoice_model.write(cr, uid, invoice_ids, {'type2': 'vessel'})

    def _create_invoices(self, cr, uid, invoice_lines, context=None):
        partner_model = self.pool.get('res.partner')
        pricelist_model = self.pool.get('product.pricelist')
        invoice_model = self.pool.get('account.invoice')
        invoice_line_model = self.pool.get('account.invoice.line')
        cont_nr_model = self.pool.get('lct.container.number')
        product_model = self.pool.get('product.product')

        date_invoice = datetime.today().strftime('%Y-%m-%d')

        invoice_ids = []
        for partner_id, invoice in invoice_lines.iteritems():
            partner = partner_model.browse(cr, uid, partner_id, context=context)
            account = partner.property_account_receivable
            if not account:
                raise osv.except_osv(('Error'), ('No account receivable could be found on customer %s' % partner.name))
            pricelist_id = partner.property_product_pricelist.id
            invoice_vals = {
                'partner_id': partner_id,
                'account_id': account.id,
                'date_invoice': date_invoice,
            }
            invoice_ids.append(invoice_model.create(cr, uid, invoice_vals, context=context))
            line_vals = {
                'invoice_id': invoice_ids[-1],
            }
            for product_id, cont_nr_ids in invoice.iteritems():
                product = product_model.browse(cr, uid, product_id, context=context)
                account = product.property_account_income or (product.categ_id and product.categ_id.property_account_income_categ) or False
                if not account:
                    raise osv.except_osv(('Error'), ('Could not find an income account on product %s ') % product.name)
                cont_nrs = cont_nr_model.browse(cr, uid, cont_nr_ids, context=context)
                quantities = [cont_nr.quantity for cont_nr in cont_nrs]
                pricelist_qties = [cont_nr.pricelist_qty for cont_nr in cont_nrs]
                quantity = sum(quantities)
                price = 0.
                for pricelist_qty in pricelist_qties:
                    price_multi = pricelist_model.price_get_multi(cr, uid, [pricelist_id], [(product_id, pricelist_qty, partner_id)], context=context)
                    price += pricelist_qty*price_multi[product_id][pricelist_id]

                line_vals.update({
                    'product_id': product_id,
                    'name': product.name,
                    'account_id': account.id,
                    'partner_id': partner_id,
                    'quantity': quantity,
                    'price_unit': price/quantity,
                })
                line_id = invoice_line_model.create(cr, uid, line_vals, context=context)
                cont_nr_model.write(cr, uid, cont_nr_ids, {'invoice_line_id': line_id}, context=context)
        return invoice_ids

    def _merge_vbl_pair(self, cr, uid, id1, id2, context=None):
        invoice_line_model = self.pool.get('account.invoice.line')
        vbl1, vbl2 = self.browse(cr, uid, [id1, id2], context=context)
        new_lines = dict([(line.product_id.id, line) for line in vbl1.invoice_line])
        for line in vbl2.invoice_line:
            product_id = line.product_id.id
            if product_id in new_lines:
                line_id = invoice_line_model._merge_vbl_line_pair(cr, uid, new_lines[product_id].id, line.id, context=context)
            else:
                line_id = line.id
            invoice_line_model.write(cr, uid, [line_id], {'invoice_id': vbl1.id}, context=context)
        self.unlink(cr, uid, [vbl2.id], context=context)
        date_invoice = datetime.today().strftime('%Y-%m-%d'),
        self.write(cr, uid, [vbl1.id], {'date_invoice': date_invoice}, context=context)
        return vbl1.id

    def _merge_vbls(self, cr, uid, ids, context=None):
        n_ids = len(ids)
        if n_ids < 1:
            return False
        elif n_ids == 1:
            return ids[0]
        elif n_ids == 2:
            return self._merge_vbl_pair(cr, uid, ids[0], ids[1], context=context)
        else:
            id1 = self._merge_vbls(cr, uid, ids[:n_ids/2], context=context)
            id2 = self._merge_vbls(cr, uid, ids[n_ids/2:], context=context)
            return self._merge_vbl_pair(cr, uid, id1, id2, context=context)

    def _group_vbl_by_partner(self, cr, uid, ids, auto=False, context=None):
        if not ids:
            return []
        vbl_by_currency_by_partner = {}
        for vbl in self.browse(cr, uid, ids, context=context):
            partner_id = vbl.partner_id.id
            currency_id = vbl.currency_id.id
            if partner_id in vbl_by_currency_by_partner:
                if currency_id in vbl_by_currency_by_partner[partner_id]:
                    vbl_by_currency_by_partner[partner_id][currency_id].append(vbl.id)
                else:
                    vbl_by_currency_by_partner[partner_id][currency_id] = [vbl.id]
            else:
                vbl_by_currency_by_partner[partner_id] = {currency_id : [vbl.id]}
        if not auto:
            if len(vbl_by_currency_by_partner) > 1:
                raise osv.except_osv(('Error'), ("You can't group invoices with different customers"))
            elif len(vbl_by_currency_by_partner.values()[0]) > 1:
                raise osv.except_osv(('Error'), ("You can't group invoices with different currencies"))
        for vbl_by_currency in vbl_by_currency_by_partner.values():
            for vbl_ids in vbl_by_currency.values():
                self._merge_vbls(cr, uid, vbl_ids, context=context)


    # GROUP INVOICES

    def group_invoices(self, cr, uid, ids, context=None):
        vbl_ids = self.search(cr, uid, [('id','in',ids), ('type2','=','vessel')], context=context)
        if len(ids) > len(vbl_ids):
            raise osv.except_osv(('Error'), "You can only group invoices of type Vessel Billing")
        self._group_vbl_by_partner(cr, uid, vbl_ids, context=context)


    # VCL

    def xml_to_vcl(self, cr, uid, imp_data_id, context=None):
        imp_data = self.pool.get('lct.tos.import.data').browse(cr, uid, imp_data_id, context=context)
        content = re.sub('<\?xml.*\?>','',imp_data.content).replace(u"\ufeff","")
        vdockages = ET.fromstring(content)
        vdockage_ids = []

        invoice_model = self.pool.get('account.invoice')
        for dockage in vdockages.findall('call'):
            dockage_vals = self._get_invoice_vals(cr, uid, dockage, 'vcl', context=context)
            dockage_vals['type2'] = 'dockage'
            if dockage_vals['off_window'] == 'YES':
                dockage_vals['off_window'] = True
            else:
                dockage_vals['off_window'] = False
            if 'voyage_number_in' in dockage_vals and dockage_vals['voyage_number_in'] and 'dep_time' in dockage_vals and dockage_vals['dep_time'] \
                and self.search(cr, uid, [('voyage_number_in', '=', dockage_vals['voyage_number_in']), ('dep_time', '=', dockage_vals['dep_time'])], context=context):
                raise osv.except_osv(('Error'), ('Another Vessel Dockage with the same voyage number in and same departure time already exists.'))
            vdockage_ids.append(invoice_model.create(cr, uid, dockage_vals, context=context))
        return vdockage_ids

    # YAC

    def _get_yac_category(self, cr, uid, yard_activity):
        imd_model = self.pool.get('ir.model.data')
        if yard_activity == 'STUFF':
            xml_id ='lct_product_category_stuffcharges'
        elif yard_activity == 'STRIP':
            xml_id =  'lct_product_category_stripcharges'
        elif yard_activity == 'RENOM':
            xml_id = 'lct_product_category_renominations'
        elif yard_activity == 'AMEND':
            xml_id = 'lct_product_category_amendmentcharges'
        elif yard_activity == 'INSPE':
            xml_id = 'lct_product_category_inspection'
        elif yard_activity == 'SERVI':
            xml_id = 'lct_product_category_services'
        elif yard_activity == 'ATTSE':
            xml_id = 'lct_product_category_sealnumber'
        elif yard_activity == 'ASEAL':
            xml_id = 'lct_product_category_seal'
        elif yard_activity == 'PLACA':
            xml_id = 'lct_product_category_placards'
        else:
            return False
        return imd_model.get_record_id(cr, uid, 'lct_tos_integration', xml_id)

    def _get_yac_service(self, cr, uid, service):
        imd_model = self.pool.get('ir.model.data')
        if service == 'PTI':
            xml_id = 'lct_product_service_pti'
        elif service == 'WAS':
            xml_id = 'lct_product_service_washing'
        else:
            return False
        return imd_model.get_record_id(cr, uid, 'lct_tos_integration', xml_id)

    def _get_yac_type(self, cr, uid, p_type):
        imd_model = self.pool.get('ir.model.data')
        if p_type == 'GP':
            xml_id = 'lct_product_type_gp'
        elif p_type == 'RE':
            xml_id = 'lct_product_type_reeferdg'
        else:
            return False
        return imd_model.get_record_id(cr, uid, 'lct_tos_integration', xml_id)

    def xml_to_yac(self, cr, uid, imp_data_id, context=None):
        product_model = self.pool.get('product.product')
        cont_nr_model = self.pool.get('lct.container.number')
        invoice_model = self.pool.get('account.invoice')
        pending_yac_model = self.pool.get('lct.pending.yard.activity')
        imd_model = self.pool.get('ir.model.data')

        module = 'lct_tos_integration'

        imp_data = self.pool.get('lct.tos.import.data').browse(cr, uid, imp_data_id, context=context)
        content = re.sub('<\?xml.*\?>','',imp_data.content).replace(u"\ufeff","")
        yactivities = ET.fromstring(content)
        yactivity_ids = []

        invoice_lines = {}
        for yactivity in yactivities.findall('yactivity'):
            lines = yactivity.find('lines')
            if lines is None:
                continue

            for line in lines.findall('line'):
                yard_activity = self._get_elmnt_text(line, 'yard_activity')
                if yard_activity in ['EXPST', 'REEFE']:
                    pending_yac_model.create_activity(cr, uid, line, context=context)
                    continue

                partner_id = self._get_partner(cr, uid, line, 'container_operator_id', context=context)
                if partner_id not in invoice_lines:
                    invoice_lines[partner_id] = {}
                category_id = self._get_yac_category(cr, uid, yard_activity)

                if yard_activity == 'SERVI':
                    service_ids = []
                    for service_code_id in line.findall('service_code_id'):
                        service_ids.append(self._get_yac_service(cr, uid, service_code_id.text))
                else:
                    service_ids = [False]

                size = self._get_elmnt_text(line, 'container_size')
                size_id = self._get_size(cr, uid, size)

                status = self._get_elmnt_text(line, 'status')
                status_id = self._get_status(cr, uid, status)

                if status != 'E':
                    p_type = self._get_elmnt_text(line, 'container_type_id')
                    type_id = self._get_yac_type(cr, uid, p_type)
                else:
                    type_id = False

                properties = {
                    'category_id': category_id,
                    'service_ids': service_ids,
                    'size_id': size_id,
                    'status_id': status_id,
                    'type_id': type_id,
                }
                product_ids = product_model.get_products_by_properties(cr, uid, properties, context=context)
                bundle = self._get_elmnt_text(line, 'bundles')
                if bundle=='YES':
                    product_ids.append(imd_model.get_record_id(cr, uid, module, 'bundle'))
                cont_nr_vals = {
                    'name': self._get_elmnt_text(line, 'container_number'),
                    'quantity': 1,
                    'pricelist_qty': 1,
                }
                for product_id in product_ids:
                    if product_id not in invoice_lines[partner_id]:
                        invoice_lines[partner_id][product_id] = []
                    cont_nr_id = cont_nr_model.create(cr, uid, dict(cont_nr_vals), context=context)
                    invoice_lines[partner_id][product_id].append(cont_nr_id)
        invoice_ids = self._create_invoices(cr, uid, invoice_lines, context=context)
        invoice_model.write(cr, uid, invoice_ids, {'type2': 'yactivity'})



class account_invoice_group(osv.osv_memory):
    _name = 'account.invoice.group'

    def invoice_group(self, cr, uid, ids, context=None):
        context = context or {}
        invoice_model = self.pool.get('account.invoice')
        invoice_ids = context.get('active_ids', [])
        if invoice_model.search(cr, uid, [('id','in',invoice_ids), ('state','not in',['draft','proforma','proforma2'])], context=context):
            raise osv.except_osv(('Warning!'), ("You can only group invoices if they are in 'Draft' or 'Pro-Forma' state."))

        invoice_model.group_invoices(cr, uid, invoice_ids, context=context)
        return {'type': 'ir.actions.act_window_close'}
