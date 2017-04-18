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
from datetime import datetime, timedelta
import re
import openerp.addons.decimal_precision as dp

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
        'from_day': fields.integer('From'),
        'to_day': fields.integer('To'),
        'storage_offset': fields.integer("Storage Offset"),
    }


class account_invoice_line_group(osv.osv):
    _name = "account.invoice.line.group"
    _columns = {
        'name': fields.char(),
        'line_ids': fields.one2many("account.invoice.line", "group_id"),
    }


class account_invoice_line(osv.osv):
    _inherit = 'account.invoice.line'

    def _amount_line(self, cr, uid, ids, prop, unknow_none, unknow_dict):
        res = {}
        tax_obj = self.pool.get('account.tax')
        cur_obj = self.pool.get('res.currency')
        for line in self.browse(cr, uid, ids):
            price = line.price_unit * (1-(line.discount or 0.0)/100.0)
            taxes = tax_obj.compute_all(cr, uid, line.invoice_line_tax_id, price, line.billed_quantity, product=line.product_id, partner=line.invoice_id.partner_id)
            res[line.id] = taxes['total']
            if line.invoice_id:
                cur = line.invoice_id.currency_id
                res[line.id] = cur_obj.round(cr, uid, cur, res[line.id])
        return res

    def _get_ids_from_invoice(self, cr, uid, ids, context=None):
        return self.pool.get("account.invoice.line").search(cr, uid, [('invoice_id', 'in', ids)], context=context)

    def _billed_quantity(self, cr, uid, ids, fields, arg, context=None):
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            product = line.product_id
            invoice = line.invoice_id
            pricelist = invoice and invoice.partner_id.property_product_pricelist or False

            pricelist_qties = [cont_nr.pricelist_qty for cont_nr in line.cont_nr_ids]
            if line.group_id:
                billed_quantity = sum(cont.pricelist_qty for cont in line.cont_nr_ids)
            else:
                billed_quantity = self._compute_billed_quantity(cr, uid, product and product.id or False,
                    pricelist and pricelist.id or False,
                    line.cont_nr_editable, line.quantity, pricelist_qties, context=context)

            res[line.id] = {
                'billed_quantity': billed_quantity,
                'billed_price_unit': line.price_unit,
            }
        return res

    def _type2(self, cr, uid, ids, fields, arg, context=None):
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            res.update({
                line.id: line.invoice_id.type2 or None,
            })
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
        'billed_quantity': fields.function(_billed_quantity, type='float', string="Quantity", multi='billed_unit_price_quantity'),
        'billed_price_unit': fields.function(_billed_quantity, type='float', string="Unit Price", multi='billed_unit_price_quantity'),
        'group_id': fields.many2one("account.invoice.line.group"),
        'slab_desc': fields.char("Slab"),
        'price_subtotal': fields.function(_amount_line, string='Amount', type="float", digits_compute= dp.get_precision('Account'), store=True),
        'type2': fields.function(_type2, type='selection', selection=[
            ('vessel','Vessel Billing'),
            ('appointment','Appointment'),
            ('dockage', 'Vessel Dockage'),
            ('yactivity', 'Yard Activity'),
            ], string="Invoice Type", store=True),
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
        def _compute_offset(a, b):
            return max(a-b, 0), max(b-a, 0)

        def _get_timedelta_days(td):
            return td.days + (td.seconds !=0)

        context = context or {}
        pricelist_obj = self.pool.get('product.pricelist')
        cont_nr_obj = self.pool["lct.container.number"]
        group_obj = self.pool["account.invoice.line.group"]
        invoice_obj = self.pool["account.invoice"]

        if 'invoice_id' in vals and vals['invoice_id']:
            invoice = self.pool.get('account.invoice').browse(cr, uid, vals['invoice_id'], context=context)
            if invoice.type2 and 'partner_id' in invoice and invoice.partner_id:
                tax = invoice.partner_id.tax_id
                if tax:
                    vals['invoice_line_tax_id'] = [(6, False, [tax.id])]
        if 'invoice_line_tax_id' not in vals and "product_id" in vals:
            product = self.pool.get('product.product').browse(cr, uid, vals["product_id"], context=context)
            if product.taxes_id:
                vals['invoice_line_tax_id'] = [(6, False, [taxe.id for taxe in product.taxes_id])]

        if not vals.get("invoice_id"):
            return super(account_invoice_line, self).create(cr, uid, vals, context=context)
        invoice = self.pool["account.invoice"].browse(cr, uid, vals["invoice_id"], context=context)

        if invoice.pay_through_date and invoice.berth_time:
            pay_through = datetime.strptime(invoice.pay_through_date, "%Y-%m-%d %H:%M:%S")
            berth = datetime.strptime(invoice.berth_time, "%Y-%m-%d %H:%M:%S")
            diff_days = _get_timedelta_days(pay_through - berth)

            if not invoice.expiry_date:
                invoice.write({
                    "expiry_date": berth if diff_days < 0 else pay_through,
                    })

        if not vals.get("product_id"):
            return super(account_invoice_line, self).create(cr, uid, vals, context=context)
        product = self.pool["product.product"].browse(cr, uid, vals["product_id"], context=context)

        storage_service = self.pool["ir.model.data"].get_object(cr, uid, "lct_tos_integration", "lct_product_service_storage")
        if not product.service_id or not storage_service or product.service_id.name != storage_service.name:
            return super(account_invoice_line, self).create(cr, uid, vals, context=context)

        if not invoice.partner_id or not invoice.partner_id.property_product_pricelist:
            return super(account_invoice_line, self).create(cr, uid, vals, context=context)
        pricelist = invoice.partner_id.property_product_pricelist

        if len(pricelist.version_id) != 1:
            return super(account_invoice_line, self).create(cr, uid, vals, context=context)
        version = pricelist.version_id[0]

        items = [item for item in version.items_id if item.product_tmpl_id == product.product_tmpl_id] or [item for item in version.items_id if not item.product_tmpl_id and not item.product_id]
        if len(items) != 1:
            return super(account_invoice_line, self).create(cr, uid, vals, context=context)
        item = items[0]

        if not item.slab_rate:
            return super(account_invoice_line, self).create(cr, uid, vals, context=context)

        if isinstance(vals.get('cont_nr_ids', [(0,0,[])])[0][2], dict):
            return super(account_invoice_line, self).create(cr, uid, vals, context=context)
        cont_ids = vals.pop("cont_nr_ids", [(0,0,[])])[0][2]
        line_ids = [None]*4

        pay_through = datetime.strptime(invoice.pay_through_date, "%Y-%m-%d %H:%M:%S")
        berth = datetime.strptime(invoice.berth_time, "%Y-%m-%d %H:%M:%S")
        diff_days = _get_timedelta_days(pay_through - berth)
        invoice.write({
            "expiry_date": berth + timedelta(days=item.free_period -1) if diff_days < item.free_period else pay_through,
            })

        def _compute_duration_offset(max_duration, remaining, offset):
            duration = min(remaining, max(max_duration - offset, 0))
            return duration, max(offset - max_duration, 0)

        for container in cont_nr_obj.browse(cr, uid, cont_ids, context=context):
            if not container:
                continue
            offset = container.storage_offset
            cumul_duration = offset

            remaining_days = diff_days if diff_days < item.free_period else container.pricelist_qty
            free_duration, offset = _compute_duration_offset(item.free_period, remaining_days, offset)
            remaining_days -= free_duration

            slab1_max_duration = item.first_slab_last_day - item.free_period
            slab1_duration, offset = _compute_duration_offset(slab1_max_duration, remaining_days, offset)
            remaining_days -= slab1_duration

            slab2_max_duration = item.second_slab_last_day - item.first_slab_last_day
            slab2_duration, offset = _compute_duration_offset(slab2_max_duration, remaining_days, offset)
            remaining_days -= slab2_duration

            slab3_duration = remaining_days

            cpt_line = 0
            for duration in [free_duration, slab1_duration, slab2_duration, slab3_duration]:
                if duration:
                    if not line_ids[cpt_line]:
                        line_ids[cpt_line] = super(account_invoice_line, self).create(cr, uid, vals, context=context)
                    cont_nr_obj.copy(cr, uid, container.id, {
                        "pricelist_qty": duration,
                        "invoice_line_id": line_ids[cpt_line],
                        "from_day": cumul_duration,
                        "to_day": cumul_duration + duration,
                        }, context=context)
                cumul_duration += duration
                cpt_line += 1

        slab_str = [
            "Free (%s days)" %item.free_period,
            "Slab-1 (%s days)" %(item.first_slab_last_day - item.free_period),
            "Slab-2 (%s days)" %(item.second_slab_last_day - item.first_slab_last_day),
            "Slab-3 (Unlimited)",
            ]

        group = group_obj.create(cr, uid, {'name': 'noname'}, context=context)
        mult_rate = self.pool.get('lct.multiplying.rate').get_active_rate(cr, uid, context=context)
        for line_id in line_ids:
            if line_id:
                line = self.browse(cr, uid, line_id, context=context)
                price, qty = 0, 0
                for cont in line.cont_nr_ids:
                    price_multi = pricelist_obj.price_get_multi_from_to(cr, uid, [pricelist.id], [(product.id, cont.from_day, cont.to_day, line.invoice_id.partner_id.id)], context=context)
                    price += cont.pricelist_qty * price_multi[product.id][pricelist.id] * (mult_rate if cont.oog else 1)
                    qty += cont.pricelist_qty

                context.update({"price_update": True})
                self.write(cr, uid, line_id, {
                    "quantity": qty,
                    "price_unit": price/qty if qty else 0,
                    "slab_desc": slab_str[line_ids.index(line_id)],
                    "group_id": group,
                    }, context=context)
        return max(line_ids) or super(account_invoice_line, self).create(cr, uid, vals, context=context)

    def write(self, cr, uid, ids, vals, context=None):
        if context==None:
            context={}
        lines = self.browse(cr, uid, ids, context)
        is_slab_rate = any([line.slab_desc for line in lines]) if isinstance(lines, list) else lines.slab_desc
        if is_slab_rate and not context.pop("price_update", None):
            vals.pop("price_unit", None)
        return super(account_invoice_line, self).write(cr, uid, ids, vals, context=context)

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
            'price_unit': price_subtotal/quantity if quantity else 0,
        }
        self.write(cr, uid, [invoice_line.id], vals, context=context)
        return {}


class account_voucher(osv.osv):
    _inherit = 'account.voucher'

    _columns = {
        'cashier_rcpt_nr': fields.char('Cashier receipt number'),
        'generic_customer_name': fields.char("Customer Name"),
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
            if inv.partner_id.id == self.pool.get('ir.model.data').get_object_reference(cr, uid, 'lct_tos_integration', 'lct_generic_customer')[1]:
                self.write(cr, uid, ids, {'generic_customer_name': inv.generic_customer_name}, context=context)
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


class account_direction(osv.osv):
    _name = 'account.direction'

    _columns = {
        'name': fields.char('Name'),
        'cfs_activity': fields.selection([
            ('YES', 'YES'),
            ('NO', 'NO'),
            ], 'CFS Activity'),
        'categ_id': fields.many2one('lct.product.category', string='Category'),
        'sub_categ_id': fields.many2one('lct.product.sub.category', string='Sub-category'),
    }

    _sql_constraints = [
        ('cfs_categ_subcateg_uniq', 'unique(cfs_activity, categ, sub_categ)', 'CFS Activity, Category and Sub-category must be unique combinaison'),
    ]

class account_invoice(osv.osv):
    _inherit = 'account.invoice'

    def _get_vessel_name(self, cr, uid, ids, fields, arg, context=None):
        res = {}
        vsl_model = self.pool.get('lct.tos.vessel')
        for line in self.browse(cr, uid, ids, context=context):
            if line.vessel_id:
                res[line.id]  = vsl_model.browse(cr,uid, vsl_model.search(cr, uid, [('vessel_id','=',line.vessel_id)],context=context), context=context)[0].name
        return res

    _columns = {
        'type2': fields.selection([
            ('vessel','Vessel Billing'),
            ('appointment','Appointment'),
            ('dockage', 'Vessel Dockage'),
            ('yactivity', 'Yard Activity'),
            ], 'Type of invoice'),
        'call_sign': fields.char('Call sign'),
        'lloyds_nr': fields.char('Lloyds number'),
        'vessel_name': fields.function(_get_vessel_name, type='char', string="Vessel name"),
        'vessel_id': fields.char('Vessel ID'),
        'berth_time': fields.datetime('Berthing time'),
        'dep_time': fields.datetime('Departure time'),
        'call_sign_vbl': fields.related('call_sign', type='char', string='Call sign'),
        'lloyds_nr_vbl': fields.related('lloyds_nr', type='char', string='Lloyds number'),
        'vessel_id_vbl': fields.related('vessel_id', type='char', string='Vessel ID'),
        'vessel_name_vbl': fields.related('vessel_name', type='char', string='Vessel name'),
        'berth_time_vbl': fields.related('berth_time', type='datetime', string='Berthing time'),
        'dep_time_vbl': fields.related('dep_time', type='datetime', string='Departure time'),
        'vessel_id_yac': fields.related('vessel_id', type='char', string='Vessel ID'),
        'vessel_name_yac': fields.related('vessel_name', type='char', string='Vessel name'),
        'vessel_name_app': fields.char('Vessel Name'),
        'berth_time_app': fields.datetime('Berthing Time'),

        'individual_cust': fields.boolean('Individual customer'),
        'appoint_ref': fields.char('Appointment reference'),
        'appoint_date': fields.datetime('Appointment date'),
        'invoice_line_vessel': fields.related('invoice_line', type='one2many', relation='account.invoice.line', string="Invoice lines"),
        'invoice_line_appoint': fields.related('invoice_line', type='one2many', relation='account.invoice.line', string="Invoice lines"),
        'voyage_number_in': fields.char('Voyage Number In'),
        'voyage_number_out': fields.char('Voyage Number Out'),
        'voyage_number_in_vbl': fields.related('voyage_number_in', type='char', string='Voyage Number In'),
        'voyage_number_out_vbl': fields.related('voyage_number_out', type='char', string='Voyage Number Out'),
        'voyage_number_in_yac': fields.related('voyage_number_in', type='char', string='Voyage Number In'),
        'voyage_number_out_yac': fields.related('voyage_number_out', type='char', string='Voyage Number Out'),
        'voyage_number_in_app': fields.char('Vessel In Voyage Number'),
        'voyage_number_out_app': fields.char('Vessel Out Voyage Number'),
        'off_window': fields.boolean('OFF window'),
        'loa': fields.integer('Length'),
        'woa': fields.integer('Width'),
        'loa_vbl': fields.related('loa', type='integer', string='Length'),
        'woa_vbl': fields.related('woa', type='integer', string='Width'),
        'loa_yac': fields.related('loa', type='integer', string='Length'),
        'woa_yac': fields.related('woa', type='integer', string='Width'),
        'imported_file_id': fields.many2one('lct.tos.import.data', string="Imported File", ondelete='restrict'),
        'printed': fields.integer('Already printed'),
        'generic_customer': fields.related('partner_id', 'generic_customer', type='boolean', string="Generic customer"),
        'generic_customer_id': fields.char('Customer ID'),
        'generic_customer_name': fields.char("Customer Name"),
        'generic_customer_information': fields.char('Customer Information'),
        'direction_id': fields.many2one('account.direction', string='Destination'),
        'expiry_date': fields.date(string='Expiry Date'),
        'pay_through_date': fields.datetime(string='Pay Through Date'),

        'bill_of_lading': fields.char('Bill of Lading'),
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
        if invoice.state in ['open', 'paid']:
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

    def _get_elmnt_text(self, elmnt, tag, raise_if_not_found=True):
        sub_elmnt = elmnt.find(tag)
        if sub_elmnt is not None:
            return sub_elmnt.text
        elif raise_if_not_found:
            raise osv.except_osv(('Error'),('Unable to find tag %s\nin element : %s' % (tag, elmnt.tag)))
        else:
            return False

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
                'woa': 'beam',
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
            onchange_partner = self.onchange_partner_id(cr, uid, [], 'out_invoice', partner.id, context=context)
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

    def _get_additional_storage(self, cr, uid, additional_storage):
        if additional_storage == 'YES':
            return True
        else:
            return False

    # APP

    def _get_app_type_service_by_type(self, cr, uid, line):
        p_type = self._get_elmnt_text(line, 'container_type')
        if not p_type:
            return (False, False)
        if p_type in ['RE', 'RS', 'RT', 'TH', 'HR']:
            type_xml_id = 'lct_product_type_reeferdg'
            service_xml_id = 'lct_product_service_stevedoringcharges'
        elif p_type in ['BU', 'GP', 'UT', 'PC', 'PF', 'TA', 'TN']:
            type_xml_id = 'lct_product_type_gp'
            service_xml_id = 'lct_product_service_stevedoringcharges'
        else:
            raise osv.except_osv(('Error'), ('Unknown container_type: %s') % (p_type,))

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

    def _get_app_category(self, cr, uid, line):
        category = line.find('category')
        category_xml_id = {
            'E': 'lct_product_category_export',
            'I': 'lct_product_category_import',
        }
        if category is None or not category.text or category.text not in category_xml_id:
            return False
        return self.pool.get('ir.model.data').get_record_id(cr, uid, 'lct_tos_integration', category_xml_id.get(category.text))

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

    def _get_app_direction(self, cr, uid, line):
        sub_categ_id = self._get_app_sub_category(cr, uid, line)
        categ_id = self._get_app_category(cr, uid, line)
        cfs_activity = self._get_elmnt_text(line, 'cfs_activity')
        res = self.pool.get('account.direction').search(cr, uid, [
            ('cfs_activity', '=', cfs_activity),
            ('categ_id', '=', categ_id),
            ('sub_categ_id', '=', sub_categ_id),
            ], limit=1)
        if res:
            return res[0]

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

    def _get_shc_products(self, cr, uid, line, additional_storage, context=None):
        category_id = self.pool.get('ir.model.data').get_record_id(cr, uid, 'lct_tos_integration', 'lct_product_category_specialhandlingcode')
        size_id = self._get_app_size(cr, uid, line)

        properties = {
            'category_id': category_id,
            'size_id': size_id,
            'additional_storage': additional_storage,
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

    def _get_version(self, partner):
        if not partner or not partner.property_product_pricelist:
            return
        pricelist = partner.property_product_pricelist

        versions = [v for v in pricelist.version_id if (v.date_start or '1') <= fields.datetime.now() <= (v.date_end or '9')]
        if len(versions) == 1:
            return versions[0]

    def _get_storage_val(self, cr, uid, appointment, line, product, version):
        storage_val = self._get_elmnt_text(line, 'storage')
        storage_service = self.pool["ir.model.data"].get_object(cr, uid, "lct_tos_integration", "lct_product_service_storage")
        child_storages = [rel.child_id for rel in product.child_ids if rel.child_id.service_id == storage_service]
        if not child_storages:
            if product.service_id == storage_service:
                storage_product = product
            else:
                return storage_val
        else:
            storage_product = child_storages[0]

        items = [item for item in version.items_id if item.product_tmpl_id == storage_product.product_tmpl_id] or [item for item in version.items_id if not item.product_tmpl_id and not item.product_id]
        if len(items) != 1:
            raise('Pricelist Version %s do not have unique item for the product %s (based on template_id)' %(version.name, product.name))
        item = items[0]

        if not item.slab_rate:
            return storage_val

        free_period = item.free_period
        pay_through_date = datetime.strptime(self._get_elmnt_text(appointment, 'pay_through_date'), "%Y-%m-%d %H:%M:%S")
        berthing_time = datetime.strptime(self._get_elmnt_text(appointment, 'berthing_time'), "%Y-%m-%d %H:%M:%S")
        if (pay_through_date - berthing_time).days < free_period:
            return (pay_through_date - berthing_time).days + 1
        return storage_val

    def _line2vals(self, cr, uid, appointment, line, product, version):
        storage = self._get_storage_val(cr, uid, appointment, line, product, version)
        return {
            'storage': self._get_storage_val(cr, uid, appointment, line, product, version),
            'plugged_time': self._get_elmnt_text(line, 'plugged_time'),
        }

    def _split(self, cr, uid, quantities_by_products, appointment, line, version, context=None):
        context = context or {}
        product_model = self.pool.get('product.product')
        res = {}

        for product_id, qty in quantities_by_products.items():
            product = product_model.browse(cr, uid, product_id, context=context)
            vals = self._line2vals(cr, uid, appointment, line, product, version)
            if not product.child_ids:
                res.update({
                    product_id: qty,
                })
            for child_line in product.child_ids:
                qty_fixed = child_line.qty_fixed if child_line.qty_fixed else 1
                qty_based_on = vals.get(child_line.qty_based_on, 1)
                child_qty = qty * qty_fixed * (qty_based_on or 0)
                if child_qty:
                    res.update({
                        child_line.child_id.id: child_qty,
                    })
        return res

    def _get_product_id(self, cr, uid, line, type_, additional_storage='NO', context=None):
        context = context or {}

        def _xml2bool(xml):
            if not xml or xml == 'NO':
                return False
            return True

        def _code2id(obj, cr, uid, code, context=None):
            context = context or {}
            res = obj.search(cr, uid, [('code', '=', code)], context=context)
            if res:
                return res[0]
            return False

        if type_ == 'APP':
            cfs_activity = self._get_elmnt_text(line, 'cfs_activity')
            status = self._get_elmnt_text(line, 'status')
            category = self._get_elmnt_text(line, 'category')
            subcategory = self._get_elmnt_text(line, 'subcategory')
            container_size = self._get_elmnt_text(line, 'container_size')
            container_hazardous_class = self._get_elmnt_text(line, 'container_hazardous_class')
            active_reefer = self._get_elmnt_text(line, 'active_reefer')
            oog = self._get_elmnt_text(line, 'oog')
            bundles = self._get_elmnt_text(line, 'bundles')

            product_ids = self.pool.get('product.product').search(cr, uid, [
                ('ptype', '=', 'generic'),
                ('cfs_activity', '=', _xml2bool(cfs_activity)),
                ('status_id', '=', _code2id(self.pool.get('lct.product.status'), cr, uid, status, context=context)),
                ('category_id', '=', _code2id(self.pool.get('lct.product.category'), cr, uid, category, context=context)),
                ('sub_category_id', '=', _code2id(self.pool.get('lct.product.sub.category'), cr, uid, subcategory, context=context)),
                ('size_id', '=', _code2id(self.pool.get('lct.product.size'), cr, uid, container_size, context=context)),
                ('hazardous_class', '=', _xml2bool(container_hazardous_class)),
                ('active_reefer', '=', _xml2bool(active_reefer)),
                ('oog', '=', _xml2bool(oog)),
                ('bundles', '=', _xml2bool(bundles)),
                ('additional_storage', '=', _xml2bool(additional_storage)),
            ], context=context)

            if not len(product_ids):
                raise osv.except_osv(('Error'), ("No Generic Product found."))
            else:
                return product_ids[0]

        if type_ == 'SHC':
            container_size = self._get_elmnt_text(line, 'container_size')
            service_ids = []
            for shc_tag in line.findall('special_handling_code_id'):
                if shc_tag.text:
                    if shc_tag.text == 'CFS':
                        continue
                    service_ids.append(
                        _code2id(self.pool.get('lct.product.service'), cr, uid, shc_tag.text, context=context)
                    )

            product_ids = self.pool.get('product.product').search(cr, uid, [
                ('ptype', '=', 'shc'),
                ('size_id', '=', _code2id(self.pool.get('lct.product.size'), cr, uid, container_size, context=context)),
                ('service_id', 'in', service_ids),
            ], context=context)
            return product_ids

        if type_ == 'VBL':
            category = self._get_elmnt_text(line, 'transaction_category_id')
            container_size = self._get_elmnt_text(line, 'container_size')
            container_type = self._get_elmnt_text(line, 'container_type_id')
            container_hazardous_class = self._get_elmnt_text(line, 'container_hazardous_class_id')
            active_reefer = self._get_elmnt_text(line, 'active_reefer')
            oog = self._get_elmnt_text(line, 'oog')
            bundles = self._get_elmnt_text(line, 'bundles')
            service_code_id = self._get_elmnt_text(line, 'transaction_direction')

            product_ids = self.pool.get('product.product').search(cr, uid, [
                ('ptype', '=', 'generic'),
                ('category_id', '=', _code2id(self.pool.get('lct.product.category'), cr, uid, category, context=context)),
                ('size_id', '=', _code2id(self.pool.get('lct.product.size'), cr, uid, container_size, context=context)),
                ('type_id', '=', _code2id(self.pool.get('lct.product.type'), cr, uid, container_type, context=context)),
                ('hazardous_class', '=', _xml2bool(container_hazardous_class)),
                ('active_reefer', '=', _xml2bool(active_reefer)),
                ('oog', '=', _xml2bool(oog)),
                ('bundles', '=', _xml2bool(bundles)),
            ], context=context)

        if type_ == 'YAC':
            status = self._get_elmnt_text(line, 'status')
            category = self._get_elmnt_text(line, 'category')
            container_size = self._get_elmnt_text(line, 'container_size')
            container_type = self._get_elmnt_text(line, 'container_type_id')
            container_hazardous_class = self._get_elmnt_text(line, 'container_hazardous_class_id')
            active_reefer = self._get_elmnt_text(line, 'active_reefer')
            oog = self._get_elmnt_text(line, 'oog')
            bundles = self._get_elmnt_text(line, 'bundles')
            service_code_id = self._get_elmnt_text(line, 'transaction_direction')

            product_ids = self.pool.get('product.product').search(cr, uid, [
                ('ptype', '=', 'generic'),
                ('status_id', '=', _code2id(self.pool.get('lct.product.status'), cr, uid, status, context=context)),
                ('category_id', '=', _code2id(self.pool.get('lct.product.category'), cr, uid, category, context=context)),
                ('size_id', '=', _code2id(self.pool.get('lct.product.size'), cr, uid, container_size, context=context)),
                ('type_id', '=', _code2id(self.pool.get('lct.product.type'), cr, uid, container_type, context=context)),
                ('hazardous_class', '=', _xml2bool(container_hazardous_class)),
                ('active_reefer', '=', _xml2bool(active_reefer)),
                ('oog', '=', _xml2bool(oog)),
                ('bundles', '=', _xml2bool(bundles)),
                ('service_id', '=', _code2id(self.pool.get('lct.product.service'), cr, uid, service_code_id, context=context)),
            ], context=context)

        if product_ids:
            return product_ids[0]

    def _create_app(self, cr, uid, appointment, context=None):
        imd_model = self.pool.get('ir.model.data')
        product_model = self.pool.get('product.product')
        cont_nr_model = self.pool.get('lct.container.number')
        invoice_line_model = self.pool.get('account.invoice.line')
        partner_model = self.pool.get('res.partner')
        pricelist_model = self.pool.get('product.pricelist')
        module = 'lct_tos_integration'

        ind_cust = self._get_elmnt_text(appointment, 'individual_customer')
        additional_storage = self._get_additional_storage(cr, uid, self._get_elmnt_text(appointment, 'additional_storage'))
        if ind_cust=='IND':
            individual_cust = True
            partner_id = imd_model.get_record_id(cr, uid, 'lct_tos_integration', 'lct_generic_customer')
        elif ind_cust=='STD':
            individual_cust = False
            partner_id = self._get_partner(cr, uid, appointment, 'customer_id', context=context)
        else:
            raise osv.except_osv(('Error'), ("Unknown value for tag 'individual_customer': %s" % ind_cust))
        partner = partner_model.browse(cr, uid, partner_id, context=context)
        version = self._get_version(partner)
        account = partner.property_account_receivable
        if not account:
            raise osv.except_osv(('Error'), ('No account receivable could be found on customer %s' % partner.name))
        date_invoice = datetime.today().strftime('%Y-%m-%d')

        onchange_partner = self.onchange_partner_id(cr, uid, [], 'out_invoice', partner_id, context=context)
        app_vals = onchange_partner and onchange_partner.get('value', {})

        customer_id = self._get_elmnt_text(appointment, 'customer_id')
        customer_name = self._get_elmnt_text(appointment, 'individual_customer_name')
        customer_info = self._get_elmnt_text(appointment, 'individual_customer_info')
        vessel_name = self._get_elmnt_text(appointment, 'name')
        voyage_number_in = self._get_elmnt_text(appointment, 'vessel_in_voyage_number')
        voyage_number_out = self._get_elmnt_text(appointment, 'vessel_out_voyage_number')
        berth_time = self._get_elmnt_text(appointment, 'berthing_time')

        app_vals.update({
                'individual_cust': individual_cust,
                'partner_id': partner_id,
                'appoint_ref': self._get_elmnt_text(appointment, 'appointment_reference'),
                'appoint_date': self._get_elmnt_text(appointment, 'appointment_date'),
                'date_due': self._get_elmnt_text(appointment, 'pay_through_date'),
                'pay_through_date': self._get_elmnt_text(appointment, 'pay_through_date'),
                'berth_time': berth_time,
                'account_id': account.id,
                'date_invoice': date_invoice,
                'type2': 'appointment',
                'currency_id': partner.property_product_pricelist.currency_id.id,

                'voyage_number_in_app': voyage_number_in,
                'voyage_number_out_app': voyage_number_out,
                'vessel_name_app': vessel_name,
                'generic_customer_id': customer_id,
                'generic_customer_name': customer_name,
                'generic_customer_information': customer_info,
                'berth_time_app': berth_time,
            })

        app_id = self.create(cr, uid, app_vals, context=context)

        pricelist_id = partner.property_product_pricelist.id

        lines = appointment.find('lines')
        if lines is None:
            return app_id

        app_direction_id = None
        bill_of_lading = None
        first_line = True

        mult_rate = self.pool.get('lct.multiplying.rate').get_active_rate(cr, uid, context=context)
        invoice_lines = {}
        for line in lines.findall('line'):
            if first_line:
                first_line = False
                app_direction_id = self._get_app_direction(cr, uid, line)
                bill_of_lading = self._get_elmnt_text(line, 'BL')

            parent_quantities_by_products = {}
            product_id = self._get_product_id(cr, uid, line, 'APP', additional_storage=additional_storage, context=context)
            if product_id:
                parent_quantities_by_products.update({
                    product_id: 1,
                })

            special_handling_product_ids = self._get_product_id(cr, uid, line, 'SHC', context=context)
            for special_handling_product_id in special_handling_product_ids:
                parent_quantities_by_products.update({
                    special_handling_product_id: 1,
                })

            quantities_by_products = self._split(cr, uid, parent_quantities_by_products, appointment, line, version, context=context)

            # shc_product_ids = self._get_shc_products(cr, uid, line, additional_storage, context=context)

            oog = self._get_elmnt_text(line, 'oog')
            oog = True if oog=='YES' else False

            offset = 0
            if additional_storage:
                pay_through_date = self._get_elmnt_text(appointment, "pay_through_date")
                berthing_time = self._get_elmnt_text(appointment, "berthing_time")
                pay_through_day = datetime.strptime(pay_through_date, "%Y-%m-%d %H:%M:%S").replace(hour=12, minute=0, second=0)
                berthing_day = datetime.strptime(berthing_time, "%Y-%m-%d %H:%M:%S").replace(hour=12, minute=0, second=0)
                storage = self._get_elmnt_text(line, "storage")
                storage_days = int(storage) if storage else 0
                delta_day = pay_through_day - berthing_day
                offset = max(delta_day.days + 1 - storage_days, 0)


            cont_nr_vals = {
                'name': self._get_elmnt_text(line, 'container_number'),
                'cont_operator': self._get_elmnt_text(line, 'container_operator'),
                'oog': oog,
                'storage_offset': offset,
            }

            for product_id, quantity in quantities_by_products.iteritems():
                if product_id not in invoice_lines:
                    invoice_lines[product_id] = []
                product = product_model.browse(cr, uid, product_id, context=context)
                cont_nr_id = cont_nr_model.create(cr, uid, dict(cont_nr_vals, pricelist_qty=quantity, quantity=1), context=context)
                invoice_lines[product_id].append(cont_nr_id)

            # for shc_product_id in shc_product_ids:
            #     if shc_product_id not in invoice_lines:
            #         invoice_lines[shc_product_id] = []
            #     product = product_model.browse(cr, uid, shc_product_id, context=context)
            #     cont_nr_id = cont_nr_model.create(cr, uid, dict(cont_nr_vals, pricelist_qty=1, quantity=1), context=context)
            #     invoice_lines[shc_product_id].append(cont_nr_id)

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
                'cont_nr_ids': [(6, 0, cont_nr_ids)],
            }
            line_id = invoice_line_model.create(cr, uid, line_vals, context=context)

        self.write(cr, uid, app_id, {
            "direction_id": app_direction_id,
            "bill_of_lading": bill_of_lading,
        })
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
        if p_type in ['BU', 'GP', 'UT', 'PC', 'PF', 'TA', 'TN']:
            type_id = imd_model.get_record_id(cr, uid, module, 'lct_product_type_gp')
        elif p_type in ['RE', 'RS', 'RT', 'TH', 'HR']:
            type_id = imd_model.get_record_id(cr, uid, module, 'lct_product_type_reeferdg')
        else:
            raise osv.except_osv(('Error'), ('Unknown container_type: %s') % (p_type,))
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
        isps_lines = {}
        plugged_hours = {}
        oog_lines = {}
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
            restow_qty = 0
            full_container = 0
            plugged_time = 0
            isps_qty = 0
            oog_qty = 0
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

                origin_type_id = None
                if status != 'E':
                    p_type = self._get_elmnt_text(line, 'container_type_id')
                    origin_type_id = self._get_vbl_type(cr, uid, p_type)
                    hazardous_class = self._get_elmnt_text(line, 'container_hazardous_class_id')
                    if p_type and hazardous_class:
                        type_id = imd_model.get_record_id(cr, uid, module, 'lct_product_type_imo')
                    else:
                        type_id = origin_type_id
                        origin_type_id = None
                else:
                    type_id = False
                properties = {
                    'category_id': category_id,
                    'service_ids': service_ids,
                    'size_id': size_id,
                    'status_id': status_id,
                    'type_id': type_id,
                }
                if status == 'F':
                    full_container += 1
                if category == 'R' and status == 'F':
                    restow_qty += 1
                if status == "F" and category in "IE":
                    isps_qty += 1

                oog = self._get_elmnt_text(line, 'oog')
                if oog == "YES":
                    properties.update({
                        'type_id': imd_model.get_record_id(cr, uid, module, 'lct_product_type_oog')
                        })

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
                    cont_nr_id = cont_nr_model.create(cr, uid, dict(cont_nr_vals, pricelist_qty=1, quantity=1), context=context)
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
                    if origin_type_id:
                        expst_properties['type_id'] = origin_type_id

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

                ref_power_days = self._get_elmnt_text(line, 'ref_power_days', False)
                if ref_power_days and ref_power_days.isdigit():
                    plugged_time +=  float(ref_power_days)*24

            plugged_hours[vessel_id] = plugged_time
            isps_lines[vessel_id] = isps_qty
            oog_lines[vessel_id] = oog_qty
        invoice_ids = self._create_invoices(cr, uid, invoice_lines, isps_lines, plugged_hours, oog_lines, docking_fees=True, context=context)
        invoice_model.write(cr, uid, invoice_ids, {'type2': 'vessel'})

    def _create_invoices(self, cr, uid, invoice_lines, isps_lines=None, plugged_hours=None, oog_lines=None, docking_fees=False, context=None):
        if isps_lines is None:
            isps_lines = {}
        if plugged_hours is None:
            plugged_hours = {}
        oog_lines = oog_lines or {}

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
                new_invoice_vals.update(self._get_data_from_last_vcl(cr, uid, vessel_id, context=context))

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

                product_isps_id = self.pool.get('ir.model.data').get_record_id(cr, uid, 'lct_tos_integration', 'isps')
                product_isps = product_model.browse(cr, uid, product_isps_id, context=context)
                price_multi_isps = pricelist_model.price_get_multi(cr, uid, [pricelist_id], [(product_isps_id, pricelist_qty, partner_id)], context=context)
                price_unit_isps = price_multi_isps[product_isps_id][pricelist_id]
                if isps_lines.get(vessel_id,False):
                    account_isps = product_isps.property_account_income or (product_isps.categ_id and product_isps.categ_id.property_account_income_categ) or False
                    isps_line_vals = {
                        'invoice_id': invoice_id,
                        'product_id': product_isps_id,
                        'name': product_isps.name,
                        'quantity': isps_lines.get(vessel_id,False),
                        'price_unit': price_unit_isps,
                        'account_id': account_isps.id,
                        'cont_nr_ids': [(0,0,{
                                'quantity': isps_lines.get(vessel_id,False),
                                'pricelist_qty': isps_lines.get(vessel_id,False),
                            })],
                    }
                    invoice_line_model.create(cr, uid, isps_line_vals, context=context)

                product_elec_id = self.pool.get('ir.model.data').get_record_id(cr, uid, 'lct_tos_integration', 'reefer_electricity')
                product_elec = product_model.browse(cr, uid, product_elec_id, context=context)
                price_multi_elec = pricelist_model.price_get_multi(cr, uid, [pricelist_id], [(product_elec_id, pricelist_qty, partner_id)], context=context)
                price_unit_elec = price_multi_elec[product_elec_id][pricelist_id]
                if plugged_hours.get(vessel_id,False):
                    account_elec = product_elec.property_account_income or (product_elec.categ_id and product_elec.categ_id.property_account_income_categ) or False
                    elec_line_vals = {
                        'invoice_id': invoice_id,
                        'product_id': product_elec_id,
                        'name': product_elec.name,
                        'quantity': plugged_hours.get(vessel_id,False),
                        'price_unit': price_unit_elec,
                        'account_id': account_elec.id,
                        'cont_nr_ids': [(0,0,{
                                'quantity': plugged_hours.get(vessel_id,False),
                                'pricelist_qty': plugged_hours.get(vessel_id,False),
                            })],
                    }
                    invoice_line_model.create(cr, uid, elec_line_vals, context=context)

                if oog_lines.get(vessel_id):
                    product_oog_id = self.pool.get('ir.model.data').get_record_id(cr, uid, 'lct_tos_integration', 'oog')
                    product_oog = product_model.browse(cr, uid, product_oog_id, context=context)
                    price_multi_oog = pricelist_model.price_get_multi(cr, uid, [pricelist_id], [(product_oog_id, pricelist_qty, partner_id)], context=context)
                    account_oog = product_elec.property_account_income or (product_oog.categ_id and product_oog.categ_id.property_account_income_categ) or False
                    oog_line_vals = {
                        'invoice_id': invoice_id,
                        'product_id': product_oog_id,
                        'name': product_oog.name,
                        'quantity': oog_lines.get(vessel_id),
                        'price_unit': price_multi_oog.get(product_oog_id, {}).get(pricelist_id, 0),
                        'account_id': account_oog.id if account_oog else None,
                        'cont_nr_ids': [(0, 0, {
                            'quantity':oog_lines.get(vessel_id),
                            'pricelist_qty': oog_lines.get(vessel_id),
                        })]
                    }
                    invoice_line_model.create(cr, uid, oog_line_vals, context=context)


                product_dockage_id = self.pool.get('ir.model.data').get_record_id(cr, uid, 'lct_tos_integration', 'dockage_fixed')
                product_dockage = product_model.browse(cr, uid, product_dockage_id, context=context)
                price_multi_dockage = pricelist_model.price_get_multi(cr, uid, [pricelist_id], [(product_dockage_id, pricelist_qty, partner_id)], context=context)
                price_unit_dockage = price_multi_dockage[product_dockage_id][pricelist_id]
                account_dockage = product_dockage.property_account_income or (product_dockage.categ_id and product_dockage.categ_id.property_account_income_categ) or False
                dockage_line_vals = {
                    'invoice_id': invoice_id,
                    'product_id': product_dockage_id,
                    'name': product_dockage.name,
                    'quantity': 1,
                    'price_unit': price_unit_dockage,
                    'account_id': account_dockage.id,
                    'cont_nr_ids': [(0,0,{
                            'quantity': 1,
                            'pricelist_qty': 1,
                        })],
                }
                invoice_line_model.create(cr, uid, dockage_line_vals, context=context)

                if docking_fees:
                    product_docking_day_fee_id = self.pool.get('ir.model.data').get_record_id(cr, uid, 'lct_tos_integration', 'dockage_day')
                    product_docking_day_fee = product_model.browse(cr, uid, product_docking_day_fee_id, context=context)
                    account_dockage = product_dockage.property_account_income or (product_dockage.categ_id and product_dockage.categ_id.property_account_income_categ) or False
                    invoice = invoice_model.browse(cr, uid, invoice_id, context=context)
                    dockage_day_line_vals = {
                        'invoice_id': invoice_id,
                        'product_id': product_docking_day_fee_id,
                        'name': product_docking_day_fee.name,
                        'quantity': (datetime.strptime(invoice.dep_time, "%Y-%m-%d %H:%M:%S").date() -  datetime.strptime(invoice.berth_time, "%Y-%m-%d %H:%M:%S").date()).days + 1,
                        'price_unit': 0.14*( (invoice.woa_vbl*invoice.loa_vbl)**1.5 )/1000,
                        'uos_id': product_docking_day_fee.uom_id.id,
                        'account_id': account_dockage.id,
                        'cont_nr_ids': [(0,0,{
                                'quantity': (datetime.strptime(invoice.dep_time, "%Y-%m-%d %H:%M:%S").date() -  datetime.strptime(invoice.berth_time, "%Y-%m-%d %H:%M:%S").date()).days + 1,
                                'pricelist_qty': (datetime.strptime(invoice.dep_time, "%Y-%m-%d %H:%M:%S").date() -  datetime.strptime(invoice.berth_time, "%Y-%m-%d %H:%M:%S").date()).days + 1,
                            })],
                    }
                    invoice_line_model.create(cr, uid, dockage_day_line_vals, context=context)

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
        vsl_model = self.pool.get('lct.tos.vessel')
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

            vsl_vals = {field_name: dockage_vals[field_name] for field_name in ['loa', 'woa'] if dockage_vals.get(field_name)}
            if dockage_vals.get('vessel_id') and vsl_vals:
                vessel_ids = vsl_model.search(cr, uid, [('vessel_id', '=', dockage_vals.get('vessel_id'))], context=context)
                vsl_model.write(cr, uid, vessel_ids, vsl_vals, context=context)
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
        if p_type in ['BU', 'GP', 'UT', 'PC', 'PF', 'TA', 'TN']:
            xml_id = 'lct_product_type_gp'
        elif p_type in ['RE', 'RS', 'RT', 'TH', 'HR']:
            xml_id = 'lct_product_type_reeferdg'
        else:
            raise osv.except_osv(('Error'), ('Unknown container_type: %s') % (p_type,))
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

    def _get_data_from_last_vcl(self, cr, uid, vessel_id, context=None):
        context = context or {}
        vessel_model = self.pool.get('lct.tos.vessel')
        domain = [('vessel_id', '=', vessel_id)]
        vessel_ids = vessel_model.search(cr, uid, domain, context=context)
        if len(vessel_ids) != 1:
            return {}
        vessel = vessel_model.browse(cr, uid, vessel_ids[0], context=context)
        return {
            'voyage_number_out': vessel.vessel_out_voyage_number,
            'voyage_number_in': vessel.vessel_in_voyage_number,
            'loa': vessel.loa,
            'woa': vessel.woa,
            'vessel_id': vessel_id,
        }

    def _prepare_refund(self, cr, uid, invoice, date=None, period_id=None, description=None, journal_id=None, context=None):
        def _get_line(invoice, line_data):
            for line in invoice.invoice_line:
                if line.product_id.id == line_data.get('product_id') and line.price_unit == line_data.get('price_unit'):
                    return line

        def _get_cont_nr_datas(line):
            ans = []
            for cont_nr in line.cont_nr_ids:
                ans.append(
                    (0, 0, {
                        'name': cont_nr.name,
                        'date_start': cont_nr.date_start,
                        'quantity': cont_nr.quantity,
                        'pricelist_qty': cont_nr.pricelist_qty,
                        'cont_operator': cont_nr.cont_operator,
                        'call_sign': cont_nr.call_sign,
                        'lloyds_nr': cont_nr.lloyds_nr,
                        'vessel_id': cont_nr.vessel_id,
                        'berth_time': cont_nr.berth_time,
                        'dep_time': cont_nr.dep_time,
                        # 'invoice_line_id': cont_nr.invoice_line_id,
                        'type2': cont_nr.type2,
                        'oog': cont_nr.oog,
                        'from_day': cont_nr.from_day,
                        'to_day': cont_nr.to_day,
                        'storage_offset': cont_nr.storage_offset,
                        }),
                    )
            return ans


        res = super(account_invoice, self)._prepare_refund(cr, uid, invoice, date=date, period_id=period_id, description=description, journal_id=journal_id, context=context)
        res['type2'] = invoice.type2
        old_group_ids = set([x[2].get('group_id') for x in res.get('invoice_line') if x[2].get('group_id')])
        newgroup_dict = {}
        for old_group_id in old_group_ids:
            old_group = self.pool.get('account.invoice.line.group').browse(cr, uid, old_group_id, context=context)
            newgroup_dict[old_group_id] = self.pool.get('account.invoice.line.group').create(cr, uid, {'name': old_group.name}, context=context)
        for line in res.get('invoice_line'):
            line[2]['group_id'] = newgroup_dict.get(line[2]['group_id'], False)
        res.update({
            'pay_through_date': invoice.pay_through_date,
            'berth_time': invoice.berth_time,
            'individual_cust': invoice.individual_cust,
            'appoint_date': invoice.appoint_date,
            'expiry_date': invoice.expiry_date,
            'appoint_ref': invoice.appoint_ref,
            'direction_id': invoice.direction_id.id if invoice.direction_id else None,
            'vessel_name': invoice.vessel_name,
            'call_sign': invoice.call_sign,
            'voyage_number_in': invoice.voyage_number_in,
            'loa': invoice.loa,
            'vessel_id': invoice.vessel_id,
            'lloyds_nr': invoice.lloyds_nr,
            'dep_time': invoice.dep_time,
            'voyage_number_out': invoice.voyage_number_out,
            'woa': invoice.woa,
            })
        for _, _, line_data in res.get('invoice_line', (0, 0, {})):
            line = _get_line(invoice, line_data)
            cont_datas = _get_cont_nr_datas(line)
            line_data.update({
                'cont_nr_ids': cont_datas,
                })
        return res

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
