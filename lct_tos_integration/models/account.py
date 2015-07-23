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
from openerp import SUPERUSER_ID

from lxml import etree as ET
from datetime import datetime
import re

class lct_container_number(osv.osv):
    _name = 'lct.container.number'

    _columns = {
        'name': fields.char('Container Number'),
        'date_start': fields.date('Arrival date'),
        'quantity': fields.integer('Quantity', help="Real quantity of product on invoice line"),
        'pricelist_qty': fields.integer('Pricelist quantity', help="Quantity used for pricelist computation"),
        'cont_operator': fields.char('Container operator'),
        'call_sign': fields.char('Call sign'),
        'lloyds_nr': fields.char('Lloyds number'),
        'vessel_id': fields.char('Vessel ID'),
        'berth_time': fields.datetime('Berthing time'),
        'dep_time': fields.datetime('Departure time'),
        'invoice_line_id': fields.many2one('account.invoice.line', string="Invoice line"),
        'type2': fields.related('invoice_line_id', 'invoice_id', 'type2', type='char', string="Invoice Type", readonly=True),
        'oog': fields.boolean('OOG'),
    }


class account_invoice_line(osv.osv):
    _inherit = 'account.invoice.line'

    def _get_ids_from_invoice(self, cr, uid, ids, context=None):
        return self.pool.get("account.invoice.line").search(cr, uid, [('invoice_id', 'in', ids)], context=context)

    def _billed_quantity(self, cr, uid, ids, fields, arg, context=None):
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            product = line.product_id
            invoice = line.invoice_id
            pricelist = invoice and invoice.partner_id.property_product_pricelist or False

            pricelist_qties = [cont_nr.pricelist_qty for cont_nr in line.cont_nr_ids]
            billed_quantity = self._compute_billed_quantity(cr, uid, product and product.id or False,
                pricelist and pricelist.id or False,
                line.cont_nr_editable, line.quantity, pricelist_qties, context=context)

            res[line.id] = {
                'billed_quantity': billed_quantity,
                'billed_price_unit': billed_quantity > 0 and line.price_unit * line.quantity / billed_quantity or 0,
            }

        return res

    _columns = {
        'cont_nr_ids': fields.one2many('lct.container.number', 'invoice_line_id', 'Containers'),
        'book_nr': fields.char('Booking number'),
        'cont_nr_editable': fields.related('product_id', 'cont_nr_editable', type='boolean', string='Container Number editable', store={
            'account.invoice.line': (lambda self, cr, uid, ids, context={}: ids, ['product_id'], 20),
            }),
        'state': fields.related('invoice_id', 'state', type="char", string="Status", store={
            'account.invoice.line': (lambda self, cr, uid, ids, context={}: ids, ['invoice_id'], 20),
            'account.invoice': (_get_ids_from_invoice, ['state'], 20),
            }),
        'billed_quantity': fields.function(_billed_quantity, type='float', string="Billed quantity", multi='billed_unit_price_quantity'),
        'billed_price_unit': fields.function(_billed_quantity, type='float', string="Unit Price", multi='billed_unit_price_quantity'),

    }


    def _compute_billed_quantity(self, cr, uid, product_id, pricelist_id, cont_nr_editable, quantity, pricelist_qties, context=None):
        price_item_model = self.pool.get('product.pricelist.item')
        item_id = (product_id and pricelist_id) and price_item_model.find_active_item(cr, uid, product_id, pricelist_id, context=context) or False
        item = item_id and price_item_model.browse(cr, uid, item_id, context=context) or False

        if not item or not item.slab_rate:
            if cont_nr_editable:
                return sum(pricelist_qties)
            else:
                return quantity

        if cont_nr_editable:
            return sum(max(pricelist_qty - item.free_period, 0.) for pricelist_qty in pricelist_qties)
        else:
            return max(quantity - item.free_period, 0.)

    def onchange_cont_nr_ids(self, cr, uid, ids, cont_nr_ids, context=None):
        if not ids or not cont_nr_ids:
            return {}

        value = {'quantity': 0, 'price_subtotal': 0.}
        pricelist_qties_and_oog = []
        for cont_nr in self.resolve_2many_commands(cr, uid, "cont_nr_ids", cont_nr_ids):
            value['quantity'] += cont_nr.get('quantity', 0)
            pricelist_qties_and_oog.append((cont_nr.get('pricelist_qty', 0), cont_nr.get('oog')))

        invoice_line = self.browse(cr, uid, ids[0], context=context)
        partner = invoice_line.invoice_id.partner_id
        pricelist_id = partner.property_product_pricelist.id
        product_id = invoice_line.product_id.id
        mult_rate = self.pool.get('lct.multiplying.rate').get_active_rate(cr, uid, context=context)

        for pricelist_qty, oog in pricelist_qties_and_oog:
            price_multi = self.pool.get('product.pricelist').price_get_multi(cr, uid, [pricelist_id], [(product_id, pricelist_qty, partner.id)], context=context)
            value['price_subtotal'] += pricelist_qty*price_multi[product_id][pricelist_id] * (oog and mult_rate or 1.)
        return {'value': value}

    def _compute_price_unit(self, cr, uid, product_id, quantity, cont_nr_ids, partner_id, context=None):
        if quantity <= 0.:
            return 0.
        pricelist_model = self.pool.get('product.pricelist')
        partner = self.pool.get('res.partner').browse(cr, uid, partner_id, context=context)
        pricelist_id = partner.property_product_pricelist.id
        mult_rate = self.pool.get('lct.multiplying.rate').get_active_rate(cr, uid, context=context)
        if self.pool.get('product.product').browse(cr, uid, product_id, context=context).cont_nr_editable:
            price_subtotal = 0.
            for cont_nr in self.pool.get('lct.container.number').browse(cr, uid, cont_nr_ids, context=context):
                pricelist_qty = cont_nr.pricelist_qty
                price_multi = pricelist_model.price_get_multi(cr, uid, [pricelist_id], [(product_id, pricelist_qty, partner_id)], context=context)
                price_subtotal += pricelist_qty * price_multi[product_id][pricelist_id] * (cont_nr.oog and mult_rate or 1.)
            return price_subtotal / quantity
        else:
            price_multi = pricelist_model.price_get_multi(cr, uid, [pricelist_id], [(product_id, quantity, partner_id)], context=context)
            return price_multi[product_id][pricelist_id]

    def product_id_change(self, cr, uid, ids, product_id, uom_id, qty=0, name='', type='out_invoice', partner_id=False, fposition_id=False, price_unit=False, currency_id=False, context=None, company_id=None, cont_nr_ids=[]):
        res = super(account_invoice_line, self).product_id_change(cr, uid, ids, product_id, uom_id, qty=qty, name=name, type=type, partner_id=partner_id, fposition_id=fposition_id, price_unit=price_unit, currency_id=currency_id, context=context, company_id=company_id)
        res['value'] = res.get('value', {})
        if product_id:
            res['value']['cont_nr_editable'] = self.pool.get('product.product').browse(cr, uid, product_id, context=context).cont_nr_editable
            if partner_id:
                cont_nr_ids = [cont_nr[1] for cont_nr in cont_nr_ids]
                price_unit = self._compute_price_unit(cr, uid, product_id, qty, cont_nr_ids, partner_id, context=context)
                res['value']['price_unit'] = price_unit
                res['value']['price_subtotal'] = price_unit * qty
        return res

    def onchange_quantity(self, cr, uid, ids, product_id, quantity, cont_nr_ids, partner_id, context=None):
        value = {}
        cont_nr_ids = [cont_nr[1] for cont_nr in cont_nr_ids]
        if product_id and partner_id:
            price_unit = self._compute_price_unit(cr, uid, product_id, quantity, cont_nr_ids, partner_id, context=context)
            value['price_unit'] = price_unit
            value['price_subtotal'] = price_unit * quantity
        return {'value': value}

    def _merge_invoice_line_pair(self, cr, uid, id1, id2, context=None):
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

    def create(self, cr, uid, vals, context=None):
        if 'invoice_id' in vals and vals['invoice_id']:
            invoice = self.pool.get('account.invoice').browse(cr, uid, vals['invoice_id'], context=context)
            if invoice.type2 and 'partner_id' in invoice and invoice.partner_id:
                tax = invoice.partner_id.tax_id
                if tax:
                    vals['invoice_line_tax_id'] = [(6, False, [tax.id])]
        return super(account_invoice_line, self).create(cr, uid, vals, context=context)

    def button_edit(self, cr, uid, ids, context=None):
        return {
            'view_mode': 'form',
            'view_id': self.pool.get('ir.model.data').get_record_id(cr, uid, 'lct_tos_integration', 'view_invoice_line_form_lct', context=context),
            'view_type': 'form',
            'res_model': 'account.invoice.line',
            'res_id': ids[0],
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'new',
            'domain': '[]',
            'context': context,
        }

    def button_confirm_edit(self, cr, uid, ids, context=None):
        if not ids:
            return {}

        invoice_line = self.browse(cr, uid, ids[0], context=context)
        cont_nrs = invoice_line.cont_nr_ids

        quantity = sum(cont_nr.quantity for cont_nr in cont_nrs)

        pricelist_model = self.pool.get('product.pricelist')
        invoice_line = self.browse(cr, uid, ids[0], context=context)
        partner = invoice_line.invoice_id.partner_id
        partner_id = partner.id
        pricelist_id = partner.property_product_pricelist.id
        product_id = invoice_line.product_id.id
        mult_rate = self.pool.get('lct.multiplying.rate').get_active_rate(cr, uid, context=context)

        price_subtotal = 0.
        for cont_nr in cont_nrs:
            pricelist_qty = cont_nr.pricelist_qty
            oog = cont_nr.oog
            price_multi = pricelist_model.price_get_multi(cr, uid, [pricelist_id], [(product_id, pricelist_qty, partner_id)], context=context)
            price_subtotal += pricelist_qty*price_multi[product_id][pricelist_id] * (oog and mult_rate or 1.)

        vals = {
            'quantity': quantity,
            'price_unit': price_subtotal/quantity,
        }
        self.write(cr, uid, [invoice_line.id], vals, context=context)
        return {}

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
            if inv.type2 != 'appointment' or not inv.individual_cust:
                return res
            amount = 0.0
            for payment in inv.payment_ids:
                amount += payment.credit - payment.debit
            if amount >= inv.amount_total:
                self.pool.get('lct.tos.export.data').export_app(cr, uid, invoice_id, ids[0], context=context)
        return res

    def button_proforma_voucher_bypass(self, cr, uid, ids, context=None):
        self.button_proforma_voucher(cr, SUPERUSER_ID, ids, context=context)


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
        'vessel_id': fields.char('Vessel ID'),
        'berth_time': fields.datetime('Berthing time'),
        'dep_time': fields.datetime('Departure time'),
        'call_sign_vbl': fields.related('call_sign', type='char', string='Call sign'),
        'lloyds_nr_vbl': fields.related('lloyds_nr', type='char', string='Lloyds number'),
        'vessel_id_vbl': fields.related('vessel_id', type='char', string='Vessel ID'),
        'berth_time_vbl': fields.related('berth_time', type='datetime', string='Berthing time'),
        'dep_time_vbl': fields.related('dep_time', type='datetime', string='Departure time'),
        'vessel_id_yac': fields.related('vessel_id', type='char', string='Vessel ID'),
        'individual_cust': fields.boolean('Individual customer'),
        'appoint_ref': fields.char('Appointment reference'),
        'appoint_date': fields.datetime('Appointment date'),
        'invoice_line_vessel': fields.related('invoice_line', type='one2many', relation='account.invoice.line', string="Invoice lines"),
        'invoice_line_appoint': fields.related('invoice_line', type='one2many', relation='account.invoice.line', string="Invoice lines"),
        'voyage_number_in': fields.char('Voyage Number In'),
        'voyage_number_out': fields.char('Voyage Number Out'),
        'off_window': fields.boolean('OFF window'),
        'loa': fields.integer('LOA'),
        'imported_file_id': fields.many2one('lct.tos.import.data', string="Imported File", ondelete='restrict'),
        'printed': fields.integer('Already printed'),
        'generic_customer': fields.related('partner_id', 'generic_customer', type='boolean', string="Generic customer"),
        'generic_customer_name': fields.char("Customer Name"),
    }

    _defaults = {
        'printed': 0,
    }

    def invoice_open_bypass(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        self.pool.get('account.invoice.confirm').invoice_confirm(cr, SUPERUSER_ID, [], context=dict(context, active_ids=ids))

    def invoice_validate(self, cr, uid, ids, context=None):
        res = super(account_invoice, self).invoice_validate(cr, uid, ids, context=context)
        if not ids:
            return res
        return self.print_invoice(cr, uid, ids[0], context=context)

    def print_invoice(self, cr, uid, invoice_id, context=None):
        if not invoice_id:
            return {}
        invoice = self.browse(cr, uid, invoice_id, context=context)
        self.write(cr, uid, [invoice_id], {'printed': invoice.printed + 1}, context=context)
        report_model = self.pool.get('ir.actions.report.xml')
        report_ids = report_model.search(cr, uid, [('report_name', '=', 'account.invoice')], context=context)
        if not report_ids:
            raise osv.except_osv(('Error'), ('Unable to find the invoice report'))
        report_values = report_model.read(cr, uid, report_ids[0], context=context)
        return dict(report_values, context=context)

    def onchange_partner_id(self, cr, uid, ids, type, partner_id,\
            date_invoice=False, payment_term=False, partner_bank_id=False, company_id=False, context=None):
        res = super(account_invoice, self).onchange_partner_id(cr, uid, ids, type=type, partner_id=partner_id,\
            date_invoice=date_invoice, payment_term=payment_term, partner_bank_id=partner_bank_id, company_id=company_id)
        res['value'] = res.get('value', {})
        res['value']['generic_customer'] = self.pool.get('res.partner').browse(cr, uid, partner_id, context=context).generic_customer
        return res

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
        if invoice_type == 'vcl':
            invoice_map = {
                'partner_id': 'customer_id',
                'call_sign': 'call_sign',
                'lloyds_nr': 'lloyds_number',
                'vessel_id': 'vessel_id',
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
            onchange_partner = self.onchange_partner_id(cr, uid, [], 'out_invoice', partner_id, context=context)
            onchange_vals = onchange_partner and onchange_partner.get('value', {})
            onchange_vals.update(vals)
            vals = dict(onchange_vals, partner_id=partner.id)
        else:
            raise osv.except_osv(('Error'), ('No customer with this id (%s) was found' % vals['partner_id'] ))

        invoice_line = []
        if invoice_type == 'vcl':
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
            'currency_id': partner.property_product_pricelist.currency_id.id,
        })
        return vals


    # APP

    def _get_app_type_service_by_type(self, cr, uid, line):
        p_type = self._get_elmnt_text(line, 'container_type')
        if not p_type:
            return (False, False)
        if p_type in ['RE', 'RS', 'RT', 'TH', 'HR']:
            type_xml_id = 'lct_product_type_reeferdg'
            service_xml_id = 'lct_product_service_stevedoringcharges'
        else:
            type_xml_id = 'lct_product_type_gp'
            service_xml_id = 'lct_product_service_stevedoringcharges'

        imd_model = self.pool.get('ir.model.data')
        type_id = imd_model.get_record_id(cr, uid, 'lct_tos_integration', type_xml_id)
        service_id = imd_model.get_record_id(cr, uid, 'lct_tos_integration', service_xml_id)
        return (type_id, service_id)

    def _get_app_import_type_service_by_cfs_activity(self, cr, uid, line):
        cfs_activity = self._get_elmnt_text(line, 'cfs_activity')
        if cfs_activity == 'NO':
            type_xml_id = 'lct_product_type_gatedelivery'
            service_xml_id = 'lct_product_service_shorehandling'
        elif cfs_activity == 'YES':
            type_xml_id = 'lct_product_type_cfs'
            service_xml_id = 'lct_product_service_shorehandling'
        else:
            return (False, False)

        imd_model = self.pool.get('ir.model.data')
        type_id = imd_model.get_record_id(cr, uid, 'lct_tos_integration', type_xml_id)
        service_id = imd_model.get_record_id(cr, uid, 'lct_tos_integration', service_xml_id)
        return (type_id, service_id)

    def _get_app_export_type_service_by_cfs_activity(self, cr, uid, line):
        cfs_activity = self._get_elmnt_text(line, 'cfs_activity')
        if cfs_activity == 'NO':
            type_xml_id = 'lct_product_type_gatereceive'
            service_xml_id = 'lct_product_service_shorehandling'
        elif cfs_activity == 'YES':
            type_xml_id = 'lct_product_type_cfs'
            service_xml_id = 'lct_product_service_shorehandling'
        else:
            return (False, False)

        imd_model = self.pool.get('ir.model.data')
        type_id = imd_model.get_record_id(cr, uid, 'lct_tos_integration', type_xml_id)
        service_id = imd_model.get_record_id(cr, uid, 'lct_tos_integration', service_xml_id)
        return (type_id, service_id)

    def _get_app_size(self, cr, uid, line):
        size = self._get_elmnt_text(line, 'container_size')
        if size == '20':
            xml_id = 'lct_product_size_20'
        elif size == '40':
            xml_id = 'lct_product_size_40'
        else:
            return False
        return self.pool.get('ir.model.data').get_record_id(cr, uid, 'lct_tos_integration', xml_id)

    def _get_app_sub_category(self, cr, uid, line):
        sub_category = line.find('subcategory')
        if sub_category is None or not sub_category.text:
            return False
        else:
            sub_category = sub_category.text
            if sub_category == 'T1':
                xml_id = 'lct_product_sub_category_transitsahel'
            elif sub_category == 'T2':
                xml_id = 'lct_product_sub_category_transitcoastal'
            elif sub_category == 'FZ':
                xml_id = 'lct_product_sub_category_freezone'
            else:
                return False
        return self.pool.get('ir.model.data').get_record_id(cr, uid, 'lct_tos_integration', xml_id)

    def _get_app_import_storage(self, line):
        storage = line.find('storage')
        if storage is not None:
            storage = storage.text
            if storage and storage.isdigit():
                return int(storage)
        return 0

    def _get_app_import_plugged_time(self, line):
        active_reefer = self._get_elmnt_text(line, 'active_reefer')
        if active_reefer == 'YES':
            plugged_time = line.find('plugged_time')
            if plugged_time is not None:
                plugged_time = plugged_time.text
                if plugged_time and plugged_time.isdigit():
                    return int(plugged_time)
        return 0

    def _get_app_import_line_quantities_by_products(self, cr, uid, line, context=None):
        imd_model = self.pool.get('ir.model.data')
        module = 'lct_tos_integration'

        type_quantities_by_services = {}

        category_id = imd_model.get_record_id(cr, uid, module, 'lct_product_category_import')
        size_id = self._get_app_size(cr, uid, line)
        sub_category_id = self._get_app_sub_category(cr, uid, line)
        type_id, service_id = self._get_app_type_service_by_type(cr, uid, line)
        if not sub_category_id:
            sub_category_id = imd_model.get_record_id(cr, uid, module, 'lct_product_sub_category_localimport')

        type_quantities_by_services[service_id] = (type_id, 1)

        storage = self._get_app_import_storage(line)
        if storage > 0:
            service_id = imd_model.get_record_id(cr, uid, module, 'lct_product_service_storage')
            type_quantities_by_services[service_id] = (type_id, storage)

        plugged_time = self._get_app_import_plugged_time(line)
        if plugged_time > 0:
            service_id = imd_model.get_record_id(cr, uid, module, 'lct_product_service_reeferelectricity')
            type_quantities_by_services[service_id] = (type_id, plugged_time)

        type_id, service_id = self._get_app_import_type_service_by_cfs_activity(cr, uid, line)
        type_quantities_by_services[service_id] = (type_id, 1)

        properties = {
            'category_id': category_id,
            'size_id': size_id,
            'status_id': False,
            'sub_category_id': sub_category_id,
        }

        quantities_by_products = {}
        for service_id, type_quantity in type_quantities_by_services.iteritems():
            properties['service_ids'] = [service_id]
            properties['type_id'] = type_quantity[0]
            product_id = self.pool.get('product.product').get_products_by_properties(cr, uid, properties, line.sourceline, context=context)[0]
            quantities_by_products[product_id] = type_quantity[1]

        return quantities_by_products

    def _get_app_export_line_quantities_by_products(self, cr, uid, line, empty_release=False, context=None):
        if empty_release:
            category_id = self.pool.get('ir.model.data').get_record_id(cr, uid, 'lct_tos_integration', 'lct_product_category_export_e_r')
        else:
            category_id = self.pool.get('ir.model.data').get_record_id(cr, uid, 'lct_tos_integration', 'lct_product_category_export')
        size_id = self._get_app_size(cr, uid, line)
        sub_category_id = self._get_app_sub_category(cr, uid, line)
        if not sub_category_id:
            type_id = False
        type_id, service_id = self._get_app_type_service_by_type(cr, uid, line)
        properties = {
            'category_id': category_id,
            'type_id': type_id,
            'size_id': size_id,
            'status_id': False,
            'sub_category_id': sub_category_id,
            'service_ids': [service_id],
        }
        product_ids = self.pool.get('product.product').get_products_by_properties(cr, uid, properties, line.sourceline, context=context)

        type_id, service_id = self._get_app_export_type_service_by_cfs_activity(cr, uid, line)
        properties.update({
            'type_id': type_id,
            'service_ids': [service_id],
        })
        product_ids.extend(self.pool.get('product.product').get_products_by_properties(cr, uid, properties, line.sourceline, context=context))

        quantities_by_products = dict([(product_id, 1) for product_id in product_ids])

        return quantities_by_products

    def _get_shc_service(self, cr, uid, shc):
        if shc == 'SCC':
            xml_id = 'lct_product_service_scanning'
        elif shc == 'CFS':
            xml_id = 'lct_product_service_cfs'
        elif shc == 'CLN':
            xml_id = 'lct_product_service_cleaning'
        elif shc == 'CUS':
            xml_id = 'lct_product_service_customs'
        elif shc == 'DDA':
            xml_id = 'lct_product_service_directdelivery'
        elif shc == 'EXM':
            xml_id = 'lct_product_service_deliveryforexamination'
        elif shc == 'INS':
            xml_id = 'lct_product_service_inspection'
        elif shc == 'PTI':
            xml_id = 'lct_product_service_pretripinspection'
        elif shc == 'REP':
            xml_id = 'lct_product_service_repaired'
        elif shc == 'UMC':
            xml_id = 'lct_product_service_umccinspection'
        elif shc == 'WAS':
            xml_id = 'lct_product_service_washing'
        else:
            raise osv.except_osv(('Error'), ('Could not find a service for this special handling code: %s' % shc))

        return self.pool.get('ir.model.data').get_record_id(cr, uid, 'lct_tos_integration', xml_id)

    def _get_shc_products(self, cr, uid, line, context=None):
        category_id = self.pool.get('ir.model.data').get_record_id(cr, uid, 'lct_tos_integration', 'lct_product_category_specialhandlingcode')
        size_id = self._get_app_size(cr, uid, line)

        properties = {
            'category_id': category_id,
            'size_id': size_id,
        }
        cfs_activity = line.find('cfs_activity')
        ignore_ins = (cfs_activity is not None and cfs_activity.text == 'YES')
        service_ids = []
        for shc in line.findall('special_handling_code_id'):
            if shc is None or not shc.text or (ignore_ins and shc.text == 'INS'):
                continue
            service_ids.append(self._get_shc_service(cr, uid, shc.text))
        if service_ids:
            properties['service_ids'] = service_ids
            return self.pool.get('product.product').get_products_by_properties(cr, uid, properties, line.sourceline, context=context)
        else:
            return []

    def _create_app(self, cr, uid, appointment, context=None):
        imd_model = self.pool.get('ir.model.data')
        product_model = self.pool.get('product.product')
        cont_nr_model = self.pool.get('lct.container.number')
        invoice_line_model = self.pool.get('account.invoice.line')
        partner_model = self.pool.get('res.partner')
        pricelist_model = self.pool.get('product.pricelist')

        ind_cust = self._get_elmnt_text(appointment, 'individual_customer')
        if ind_cust=='IND':
            individual_cust = True
            partner_id = imd_model.get_record_id(cr, uid, 'lct_tos_integration', 'lct_generic_customer')
        elif ind_cust=='STD':
            individual_cust = False
            partner_id = self._get_partner(cr, uid, appointment, 'customer_id', context=context)
        else:
            raise osv.except_osv(('Error'), ("Unknown value for tag 'individual_customer': %s" % ind_cust))
        partner = partner_model.browse(cr, uid, partner_id, context=context)
        account = partner.property_account_receivable
        if not account:
            raise osv.except_osv(('Error'), ('No account receivable could be found on customer %s' % partner.name))
        date_invoice = datetime.today().strftime('%Y-%m-%d')

        onchange_partner = self.onchange_partner_id(cr, uid, [], 'out_invoice', partner_id, context=context)
        app_vals = onchange_partner and onchange_partner.get('value', {})

        app_vals.update({
                'individual_cust': individual_cust,
                'partner_id': partner_id,
                'appoint_ref': self._get_elmnt_text(appointment, 'appointment_reference'),
                'appoint_date': self._get_elmnt_text(appointment, 'appointment_date'),
                'date_due': self._get_elmnt_text(appointment, 'pay_through_date'),
                'account_id': account.id,
                'date_invoice': date_invoice,
                'type2': 'appointment',
                'currency_id': partner.property_product_pricelist.currency_id.id,
            })

        app_id = self.create(cr, uid, app_vals, context=context)

        pricelist_id = partner.property_product_pricelist.id

        lines = appointment.find('lines')
        if lines is None:
            return app_id

        mult_rate = self.pool.get('lct.multiplying.rate').get_active_rate(cr, uid, context=context)
        invoice_lines = {}
        for line in lines.findall('line'):
            category = self._get_elmnt_text(line, 'category')
            if category == 'I':
                quantities_by_products = self._get_app_import_line_quantities_by_products(cr, uid, line, context=context)
            elif category in ['E', 'Z']:
                quantities_by_products = self._get_app_export_line_quantities_by_products(cr, uid, line, empty_release=(category == 'Z'), context=context)


            bundle = self._get_elmnt_text(line, 'bundles')
            if bundle=='YES':
                bundle_product_id = imd_model.get_record_id(cr, uid, 'lct_tos_integration', 'bundle')
                quantities_by_products[bundle_product_id] = 1

            shc_product_ids = self._get_shc_products(cr, uid, line, context=context)

            oog = self._get_elmnt_text(line, 'oog')
            oog = True if oog=='YES' else False

            cont_nr_vals = {
                'name': self._get_elmnt_text(line, 'container_number'),
                'cont_operator': self._get_elmnt_text(line, 'container_operator'),
                'oog': oog,
            }

            for product_id, quantity in quantities_by_products.iteritems():
                if product_id not in invoice_lines:
                    invoice_lines[product_id] = []
                cont_nr_id = cont_nr_model.create(cr, uid, dict(cont_nr_vals, pricelist_qty=quantity, quantity=1), context=context)
                invoice_lines[product_id].append(cont_nr_id)

            for shc_product_id in shc_product_ids:
                if shc_product_id not in invoice_lines:
                    invoice_lines[shc_product_id] = []
                cont_nr_id = cont_nr_model.create(cr, uid, dict(cont_nr_vals, pricelist_qty=1, quantity=1), context=context)
                invoice_lines[shc_product_id].append(cont_nr_id)

        for product_id, cont_nr_ids in  invoice_lines.iteritems():
            product = product_model.browse(cr, uid, product_id, context=context)
            account = product.property_account_income or (product.categ_id and product.categ_id.property_account_income_categ) or False
            if not account:
                raise osv.except_osv(('Error'), ('Could not find an income account on product %s ') % product.name)

            quantity = 0.
            price = 0.
            for cont_nr in cont_nr_model.browse(cr, uid, cont_nr_ids, context=context):
                pricelist_qty = cont_nr.pricelist_qty
                oog = cont_nr.oog
                quantity += pricelist_qty
                price_multi = pricelist_model.price_get_multi(cr, uid, [pricelist_id], [(product_id, pricelist_qty, partner_id)], context=context)
                price += pricelist_qty*price_multi[product_id][pricelist_id] * (oog and mult_rate or 1.)
            line_vals = {
                'invoice_id': app_id,
                'product_id': product_id,
                'name': product.name,
                'account_id': account.id,
                'partner_id': partner_id,
                'quantity': quantity,
                'price_unit': price/quantity,
            }
            line_id = invoice_line_model.create(cr, uid, line_vals, context=context)
            cont_nr_model.write(cr, uid, cont_nr_ids, {'invoice_line_id': line_id}, context=context)

        return app_id

    def xml_to_app(self, cr, uid, imp_data_id, context=None):
        imp_data = self.pool.get('lct.tos.import.data').browse(cr, uid, imp_data_id, context=context)
        content = re.sub('<\?xml.*\?>','',imp_data.content).replace(u"\ufeff","")
        appointments = ET.fromstring(content)

        for appointment in appointments:
            app_id = self._create_app(cr, uid, appointment, context=context)
            self.write(cr, uid, app_id, {'imported_file_id': imp_data_id}, context=context)

    # VBL

    def _get_vbl_category_service(self, cr, uid, category, direction=None):
        imd_model = self.pool.get('ir.model.data')
        module = 'lct_tos_integration'
        if category == 'I':
            category_id = imd_model.get_record_id(cr, uid, module, 'lct_product_category_import')
            service_ids = [imd_model.get_record_id(cr, uid, module, 'lct_product_service_discharge')]
        elif category == 'E':
            category_id = imd_model.get_record_id(cr, uid, module, 'lct_product_category_export')
            service_ids = [imd_model.get_record_id(cr, uid, module, 'lct_product_service_load')]
        elif category == 'T':
            if direction == 'D':
                service_ids = [imd_model.get_record_id(cr, uid, module, 'lct_product_service_reload')]
            elif direction == 'R':
                service_ids = [imd_model.get_record_id(cr, uid, module, 'lct_product_service_discharge')]
            else:
                return (False, False)
            category_id = imd_model.get_record_id(cr, uid, module, 'lct_product_category_transshipment')
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

    def _prepare_invoice_line_dict(self, invoice_lines, partner_id, vessel_id, product_id):
        if partner_id not in invoice_lines:
            invoice_lines[partner_id] = {vessel_id: {product_id: []}}
        elif vessel_id not in invoice_lines[partner_id]:
            invoice_lines[partner_id][vessel_id] = {product_id: []}
        elif product_id not in invoice_lines[partner_id][vessel_id]:
            invoice_lines[partner_id][vessel_id][product_id] = []

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
            partner_id = self._get_partner(cr, uid, vbilling, 'customer_id')
            partner = partner_model.browse(cr, uid, partner_id, context=context)

            vessel_id = self._get_elmnt_text(vbilling, 'vessel_id')
            cont_nr_vals ={
                'call_sign': self._get_elmnt_text(vbilling, 'call_sign'),
                'lloyds_nr': self._get_elmnt_text(vbilling, 'lloyds_number'),
                'vessel_id': vessel_id,
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
                self._prepare_invoice_line_dict(invoice_lines, partner_id, vessel_id, product_id)
                invoice_lines[partner_id][vessel_id][product_id].append(cont_nr_id)

            n_gbc = self._xml_get_digit(vbilling, 'gearbox_count')
            if n_gbc > 0:
                service_id = imd_model.get_record_id(cr, uid, module, 'lct_product_service_gearboxcount')
                product_id = product_model.search(cr, uid, [('service_id', '=', service_id)], context=context)
                if not product_id:
                    raise osv.except_osv(('Error'), ('The product "Gearbox Count" cannot be found.'))
                product_id = product_id[0]
                vals = dict(cont_nr_vals, pricelist_qty=n_gbc, quantity=n_gbc)
                cont_nr_id = cont_nr_model.create(cr, uid, vals, context=context)
                self._prepare_invoice_line_dict(invoice_lines, partner_id, vessel_id, product_id)
                invoice_lines[partner_id][vessel_id][product_id].append(cont_nr_id)

            lines = vbilling.find('lines')
            if lines is None:
                continue
            for line in lines.findall('line'):
                partner_id = self._get_partner(cr, uid, line, 'container_customer_id', context=context)

                cont_nr_name = self._get_elmnt_text(line, 'container_number')
                cont_nr_vals['name'] = cont_nr_name
                pricelist_qty = 1

                category = self._get_elmnt_text(line, 'transaction_category_id')
                if category == 'R':
                    partner_id = self._get_partner(cr, uid, vbilling, 'customer_id', context=context)

                if category == 'T':
                    direction = self._get_elmnt_text(line, 'transaction_direction')
                    category_id, service_ids = self._get_vbl_category_service(cr, uid, category, direction)
                else:
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

                oog = self._get_elmnt_text(line, 'oog')
                oog = True if oog=='YES' else False

                product_ids = product_model.get_products_by_properties(cr, uid, dict(properties), line.sourceline, context=context)
                if not all(product_ids):
                    error  = 'One or more product(s) could not be found with these combinations: '
                    error += ', '.join([key + ': ' + str(val) for key, val in properties.iteritems()])
                    raise osv.except_osv(('Error'), (error))

                bundle = self._get_elmnt_text(line, 'bundles')
                if bundle=='YES':
                    product_ids.append(imd_model.get_record_id(cr, uid, module, 'bundle'))

                for product_id in product_ids:
                    self._prepare_invoice_line_dict(invoice_lines, partner_id, vessel_id, product_id)
                    cont_nr_id = cont_nr_model.create(cr, uid, dict(cont_nr_vals, pricelist_qty=1, quantity=1, oog=oog), context=context)
                    invoice_lines[partner_id][vessel_id][product_id].append(cont_nr_id)
                if category in ['E', 'T']:
                    domain = [('vessel_id', '=', vessel_id), ('name', '=', cont_nr_name), ('status', '=', 'pending')]
                    pending_yac_ids = pending_yac_model.search(cr, uid, domain, context=context)

                    reefe_properties = dict(properties)
                    expst_properties = dict(properties)

                    reefe_properties['service_ids'] = [imd_model.get_record_id(cr, uid, module, 'lct_product_service_reeferelectricity')]
                    reefe_properties['status_id'] = False
                    reefe_properties['type_id'] = False
                    expst_properties['service_ids'] = [imd_model.get_record_id(cr, uid, module, 'lct_product_service_storage')]

                    reefe_product_id = product_model.get_products_by_properties(cr, uid, reefe_properties, line.sourceline, context=context)[0]
                    expst_product_id = product_model.get_products_by_properties(cr, uid, expst_properties, line.sourceline, context=context)[0]

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
                        self._prepare_invoice_line_dict(invoice_lines, partner_id, vessel_id, reefe_product_id)
                        for quantity in reefe_qties:
                            cont_nr_id = cont_nr_model.create(cr, uid, dict(cont_nr_vals, pricelist_qty=quantity, quantity=quantity), context=context)
                            invoice_lines[partner_id][vessel_id][reefe_product_id].append(cont_nr_id)
                    if expst_qties:
                        self._prepare_invoice_line_dict(invoice_lines, partner_id, vessel_id, expst_product_id)
                        for quantity in expst_qties:
                            cont_nr_id = cont_nr_model.create(cr, uid, dict(cont_nr_vals, pricelist_qty=quantity, quantity=quantity), context=context)
                            invoice_lines[partner_id][vessel_id][expst_product_id].append(cont_nr_id)

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
        mult_rate_model = self.pool.get('lct.multiplying.rate')

        mult_rate_ids = mult_rate_model.search(cr, uid, [('active', '=', True)], context=context)
        mult_rate = mult_rate_ids and mult_rate_model.browse(cr, uid, mult_rate_ids[0], context=context).multiplying_rate or 1.

        date_invoice = datetime.today().strftime('%Y-%m-%d')

        mult_rate = self.pool.get('lct.multiplying.rate').get_active_rate(cr, uid, context=context)

        invoice_ids = []
        for partner_id, invoice in invoice_lines.iteritems():
            partner = partner_model.browse(cr, uid, partner_id, context=context)
            account = partner.property_account_receivable
            if not account:
                raise osv.except_osv(('Error'), ('No account receivable could be found on customer %s' % partner.name))
            pricelist_id = partner.property_product_pricelist.id
            onchange_partner = self.onchange_partner_id(cr, uid, [], 'out_invoice', partner_id, context=context)
            invoice_vals = onchange_partner and onchange_partner.get('value', {})
            invoice_vals.update({
                    'partner_id': partner_id,
                    'account_id': account.id,
                    'date_invoice': date_invoice,
                    'currency_id': partner.property_product_pricelist.currency_id.id,
                })
            for vessel_id, invoices_by_product in invoice.iteritems():
                invoice_id = invoice_model.create(cr, uid, invoice_vals, context=context)
                invoice_ids.append(invoice_id)
                line_vals = {
                    'invoice_id': invoice_id,
                }
                new_invoice_vals = {'vessel_id': vessel_id}

                for product_id, cont_nr_ids in invoices_by_product.iteritems():
                    product = product_model.browse(cr, uid, product_id, context=context)
                    account = product.property_account_income or (product.categ_id and product.categ_id.property_account_income_categ) or False
                    if not account:
                        raise osv.except_osv(('Error'), ('Could not find an income account on product %s ') % product.name)
                    cont_nrs = cont_nr_model.browse(cr, uid, cont_nr_ids, context=context)
                    if not cont_nrs:
                        continue
                    new_invoice_vals.update({
                        'call_sign': cont_nrs[0].call_sign,
                        'lloyds_nr': cont_nrs[0].lloyds_nr,
                        'berth_time': cont_nrs[0].berth_time,
                        'dep_time': cont_nrs[0].dep_time,
                    })
                    invoice_model.write(cr, uid, invoice_id, new_invoice_vals, context=context)

                    quantity = sum([cont_nr.quantity for cont_nr in cont_nrs])
                    price = 0.
                    for cont_nr in cont_nrs:
                        pricelist_qty = cont_nr.pricelist_qty
                        oog = cont_nr.oog
                        price_multi = pricelist_model.price_get_multi(cr, uid, [pricelist_id], [(product_id, pricelist_qty, partner_id)], context=context)
                        price += pricelist_qty*price_multi[product_id][pricelist_id] * (oog and mult_rate or 1.)

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


    # GROUP INVOICES

    def _merge_invoice_pair(self, cr, uid, id1, id2, context=None):
        invoice_line_model = self.pool.get('account.invoice.line')
        invoice1, invoice2 = self.browse(cr, uid, [id1, id2], context=context)
        new_lines = dict([(line.product_id.id, line) for line in invoice1.invoice_line])
        for line in invoice2.invoice_line:
            product_id = line.product_id.id
            if product_id in new_lines:
                line_id = invoice_line_model._merge_invoice_line_pair(cr, uid, new_lines[product_id].id, line.id, context=context)
            else:
                line_id = line.id
            invoice_line_model.write(cr, uid, [line_id], {'invoice_id': invoice1.id}, context=context)
        self.unlink(cr, uid, [invoice2.id], context=context)
        date_invoice = datetime.today().strftime('%Y-%m-%d'),
        self.write(cr, uid, [invoice1.id], {'date_invoice': date_invoice}, context=context)
        return invoice1.id

    def _merge_invoices(self, cr, uid, ids, context=None):
        n_ids = len(ids)
        if n_ids < 1:
            return False
        elif n_ids == 1:
            return ids[0]
        elif n_ids == 2:
            return self._merge_invoice_pair(cr, uid, ids[0], ids[1], context=context)
        else:
            id1 = self._merge_invoices(cr, uid, ids[:n_ids/2], context=context)
            id2 = self._merge_invoices(cr, uid, ids[n_ids/2:], context=context)
            return self._merge_invoice_pair(cr, uid, id1, id2, context=context)

    def _group_invoices_by_partner(self, cr, uid, ids, auto=False, context=None):
        if not ids:
            return []
        invoice_by_currency_by_vessel_id_by_partner = {}
        for invoice in self.browse(cr, uid, ids, context=context):
            partner_id = invoice.partner_id.id
            currency_id = invoice.currency_id.id
            vessel_id = invoice.vessel_id
            if partner_id not in invoice_by_currency_by_vessel_id_by_partner:
                invoice_by_currency_by_vessel_id_by_partner[partner_id] = {vessel_id: {currency_id: []}}
            elif vessel_id not in invoice_by_currency_by_vessel_id_by_partner[partner_id]:
                invoice_by_currency_by_vessel_id_by_partner[partner_id][vessel_id] = {currency_id: []}
            elif currency_id not in invoice_by_currency_by_vessel_id_by_partner[partner_id][vessel_id]:
                invoice_by_currency_by_vessel_id_by_partner[partner_id][vessel_id][currency_id] = []
            invoice_by_currency_by_vessel_id_by_partner[partner_id][vessel_id][currency_id].append(invoice.id)

        if not auto:
            if len(invoice_by_currency_by_vessel_id_by_partner) > 1:
                raise osv.except_osv(('Error'), ("You can't group invoices with different customers"))
            elif len(invoice_by_currency_by_vessel_id_by_partner.values()[0]) > 1:
                raise osv.except_osv(('Error'), ("You can't group invoices with different vessel IDs"))
            elif len(invoice_by_currency_by_vessel_id_by_partner.values()[0].values()[0]) > 1:
                raise osv.except_osv(('Error'), ("You can't group invoices with different currencies"))
        for invoice_by_currency_by_vessel in invoice_by_currency_by_vessel_id_by_partner.values():
            for invoice_by_currency in invoice_by_currency_by_vessel.values():
                for invoice_ids in invoice_by_currency.values():
                    self._merge_invoices(cr, uid, invoice_ids, context=context)

    def group_invoices(self, cr, uid, ids, context=None):
        vbl_ids = self.search(cr, uid, [('id','in',ids), ('type2','=','vessel')], context=context)
        yac_ids = self.search(cr, uid, [('id','in',ids), ('type2','=','yactivity')], context=context)
        if len(ids) == len(yac_ids):
            self._group_invoices_by_partner(cr, uid, yac_ids, context=context)
        elif len(ids) == len(vbl_ids):
            self._group_invoices_by_partner(cr, uid, vbl_ids, context=context)
        else:
            raise osv.except_osv(('Error'), "You can only group invoices of the same type")



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

                partner_id = self._get_partner(cr, uid, line, 'container_customer_id', context=context)
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
                product_ids = product_model.get_products_by_properties(cr, uid, properties, line.sourceline, context=context)

                oog = self._get_elmnt_text(line, 'oog')
                oog = True if oog=='YES' else False

                bundle = self._get_elmnt_text(line, 'bundles')
                if bundle=='YES':
                    product_ids.append(imd_model.get_record_id(cr, uid, module, 'bundle'))
                cont_nr_vals = {
                    'name': self._get_elmnt_text(line, 'container_number'),
                    'quantity': 1,
                    'pricelist_qty': 1,
                    'arr_timestamp': self._get_elmnt_text(line, 'arrival_timestamp'),
                    'dep_timestamp': self._get_elmnt_text(line, 'departure_timestamp'),
                    'plugged_time': self._get_elmnt_text(line, 'plugged_time'),
                    'oog': oog,
                }
                vessel_id = self._get_elmnt_text(line, 'vessel_id')
                for product_id in product_ids:
                    self._prepare_invoice_line_dict(invoice_lines, partner_id, vessel_id, product_id)
                    cont_nr_id = cont_nr_model.create(cr, uid, dict(cont_nr_vals), context=context)
                    invoice_lines[partner_id][vessel_id][product_id].append(cont_nr_id)
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
