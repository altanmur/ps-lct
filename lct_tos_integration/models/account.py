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
            ('dockage', 'Vessel Dockage')
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

    def _get_partner(self, cr, uid, elmnt, tag, context=None):
        partner_id = self._get_elmnt_text(elmnt, tag)
        if not partner_id.isdigit():
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
            raise osv.except_osv(('Error'), ('No customer with this name (%s) was found' % vals['partner_id'] ))

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
        })
        return vals


    # APP

    def _get_app_type_service(self, cr, uid, line):
        p_type = self._get_elmnt_text(line, 'container_type')
        if p_type == 'GP':
            type_xml_id = 'lct_product_type_gp'
            service_xml_id = 'lct_product_service_stevedoringcharges'
        elif p_type == 'RE':
            type_xml_id = 'lct_product_type_reeferdg'
            service_xml_id = 'lct_product_service_stevedoringcharges'
        elif p_type == 'NO':
            type_xml_id = 'lct_product_type_gatereceive'
            service_xml_id = 'lct_product_service_shorehandling'
        elif p_type == 'YES':
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
        sub_category = line.find('sub_category')
        if sub_category is None or not sub_category.text:
            xml_id = 'lct_product_sub_category_localimport'
        else:
            sub_category = sub_category.text
            if sub_category == 'T1':
                xml_id = 'lct_product_sub_category_transitsahel'
            elif sub_category == 'T2':
                xml_id = 'lct_product_sub_category_transitcoastal'
            elif sub_category == 'FZ':
                xml_id = 'lct_product_sub_category_freezone'
            else:
                xml_id = 'lct_product_sub_category_localimport'
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
            plugged_time = self._get_elmnt_text(line, 'plugged_time')
            if plugged_time is not None:
                plugged_time = plugged_time.text
                if plugged_time and plugged_time.isdigit():
                    return int(plugged_time)
        return 0

    def _get_app_import_line_quantities_by_products(self, cr, uid, line, context=None):
        imd_model = self.pool.get('ir.model.data')
        module = 'lct_tos_integration'

        category_id = imd_model.get_record_id(cr, uid, module, 'lct_product_category_import')
        quantities_by_services = {}

        storage = self._get_app_import_storage(line)
        if storage > 0:
            service_id = imd_model.get_record_id(cr, uid, module, 'lct_product_service_storage')
            quantities_by_services[service_id] = storage

        plugged_time = self._get_app_import_plugged_time(line)
        if plugged_time > 0:
            service_id = imd_model.get_record_id(cr, uid, module, 'lct_product_service_reeferelectricity')
            quantities_by_services[service_id] = plugged_time

        type_id, service_id = self._get_app_type_service(cr, uid, line)
        quantities_by_services[service_id] = 1

        size_id = self._get_app_size(cr, uid, line)
        sub_category_id = self._get_app_sub_category(cr, uid, line)

        properties = {
            'category_id': category_id,
            'type_id': type_id,
            'size_id': size_id,
            'status_id': False,
            'sub_category_id': sub_category_id,
        }

        quantities_by_products = {}
        for service_id, quantity in quantities_by_services.iteritems():
            properties['service_ids'] = [service_id]
            product_id = self.pool.get('product.product').get_products_by_properties(cr, uid, properties, context=context)[0]
            quantities_by_products[product_id] = quantity

        return quantities_by_products

    def _get_app_export_line_quantities_by_products(self, cr, uid, line, context=None):
        category_id = self.pool.get('ir.model.data').get_record_id(cr, uid, 'lct_tos_integration', 'lct_product_category_export')
        type_id, service_id = self._get_app_type_service(cr, uid, line)
        size_id = self._get_app_size(cr, uid, line)
        sub_category_id = self._get_app_sub_category(cr, uid, line)

        properties = {
            'category_id': category_id,
            'type_id': type_id,
            'size_id': size_id,
            'status_id': False,
            'sub_category_id': sub_category_id,
            'service_ids': [service_id],
        }

        product_id = self.pool.get('product.product').get_products_by_properties(cr, uid, properties, context=context)[0]
        quantities_by_products = {product_id: 1}

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

    def _get_shc_product(self, cr, uid, line, context=None):
        shc = line.find('special_handling_code_id')
        if shc is None:
            return False

        service_id = self._get_shc_service(cr, uid, shc.text)
        if not service_id:
            return False

        category_id = self.pool.get('ir.model.data').get_record_id(cr, uid, 'lct_tos_integration', 'lct_product_category_specialhandlingcode')
        size_id = self._get_app_size(cr, uid, line)

        properties = {
            'category_id': category_id,
            'service_ids': [service_id],
            'size_id': size_id,
        }
        return self.pool.get('product.product').get_products_by_properties(cr, uid, properties, context=context)[0]

    def _create_app(self, cr, uid, appointment, context=None):
        imd_model = self.pool.get('ir.model.data')
        product_model = self.pool.get('product.product')
        cont_nr_model = self.pool.get('lct.container.number')
        invoice_line_model = self.pool.get('account.invoice.line')
        partner_model = self.pool.get('res.partner')
        pricelist_model = self.pool.get('product.pricelist')

        ind_cust = self._get_elmnt_text(appointment, 'individual_customer')
        partner_id = self._get_partner(cr, uid, appointment, 'customer_id', context=context)
        partner = partner_model.browse(cr, uid, partner_id, context=context)
        account = partner.property_account_receivable
        if not account:
            raise osv.except_osv(('Error'), ('No account receivable could be found on customer %s' % partner.name))
        date_invoice = datetime.today().strftime('%Y-%m-%d')

        app_vals = {
            'individual_cust': True if ind_cust == 'IND' else False,
            'partner_id': self._get_partner(cr, uid, appointment, 'customer_id', context=context),
            'appoint_ref': self._get_elmnt_text(appointment, 'appointment_reference'),
            'appoint_date': self._get_elmnt_text(appointment, 'appointment_date'),
            'date_due': self._get_elmnt_text(appointment, 'pay_through_date'),
            'account_id': account.id,
            'date_invoice': date_invoice,
            'type2': 'appointment',
        }

        app_id = self.create(cr, uid, app_vals, context=context)

        pricelist_id = partner.property_product_pricelist.id

        lines = appointment.find('lines')
        if lines is None:
            return app_id

        invoice_lines = {}
        for line in lines.findall('line'):
            category = self._get_elmnt_text(line, 'category')
            if category == 'I':
                quantities_by_products = self._get_app_import_line_quantities_by_products(cr, uid, line, context=context)
            elif category == 'E':
                quantities_by_products = self._get_app_export_line_quantities_by_products(cr, uid, line, context=context)
            shc_product_id = self._get_shc_product(cr, uid, line, context=context)
            if shc_product_id:
                quantities_by_products[shc_product_id] = 1
            import ipdb; ipdb.set_trace()

            cont_nr_vals = {
                'name': self._get_elmnt_text(line, 'container_number'),
                'cont_operator': self._get_elmnt_text(line, 'container_operator'),
            }
            for product_id, quantity in quantities_by_products.iteritems():
                if product_id not in invoice_lines:
                    invoice_lines[product_id] = []
                cont_nr_id = cont_nr_model.create(cr, uid, dict(cont_nr_vals, pricelist_qty=quantity, quantity=1), context=context)
                invoice_lines[product_id].append(cont_nr_id)

        for product_id, cont_nr_ids in  invoice_lines.iteritems():
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

    def xml_to_app(self, cr, uid, imp_data_id, context=None):
        imp_data = self.pool.get('lct.tos.import.data').browse(cr, uid, imp_data_id, context=context)
        content = re.sub('<\?xml.*\?>','',imp_data.content).replace(u"\ufeff","")
        appointments = ET.fromstring(content)

        for appointment in appointments:
            self._create_app(cr, uid, appointment, context=context)


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

    def _get_vbl_status(self, cr, uid, status):
        imd_model = self.pool.get('ir.model.data')
        module = 'lct_tos_integration'
        if status == 'F':
            status_id = imd_model.get_record_id(cr, uid, module, 'lct_product_status_full')
        elif status == 'E':
            status_id = imd_model.get_record_id(cr, uid, module, 'lct_product_status_empty')
        else:
            status_id = False
        return status_id

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
        module = 'lct_tos_integration'

        imp_data = self.pool.get('lct.tos.import.data').browse(cr, uid, imp_data_id, context=context)
        content = re.sub('<\?xml.*\?>','',imp_data.content).replace(u"\ufeff","")
        vbillings = ET.fromstring(content)

        invoice_lines = {}
        for vbilling in vbillings.findall('vbilling'):
            partner_id = self._get_partner(cr, uid, vbilling, 'vessel_operator_id')
            partner = partner_model.browse(cr, uid, partner_id, context=context)
            pricelist_id = partner.property_product_pricelist

            cont_nr_vals ={
                'call_sign': self._get_elmnt_text(vbilling, 'call_sign'),
                'lloyds_nr': self._get_elmnt_text(vbilling, 'lloyds_number'),
                'vessel_ID': self._get_elmnt_text(vbilling, 'vessel_id'),
                'berth_time': self._get_elmnt_text(vbilling, 'berthing_time'),
                'dep_time': self._get_elmnt_text(vbilling, 'departure_time'),
            }
            n_hcm = self._xml_get_digit(vbilling, 'hatchcovers_moves')
            if n_hcm > 0:
                service_id = imd_model.get_record_id(cr, uid, module, 'lct_product_service_hatchcovermove')
                product_id = product_model.search(cr, uid, [('service_id','=',service_id)], context=context)[0]
                vals = dict(cont_nr_vals, pricelist_qty=n_hcm, quantity=n_hcm)
                cont_nr_id = cont_nr_model.create(cr, uid, vals, context=context)
                invoice_lines[partner_id] = {product_id: [cont_nr_id]}

            n_gbc = self._xml_get_digit(vbilling, 'gearbox_count')
            if n_gbc > 0:
                service_id = imd_model.get_record_id(cr, uid, module, 'lct_product_service_gearboxcount')
                product_id = product_model.search(cr, uid, [('service_id','=',service_id)], context=context)[0]
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
                if partner_id not in invoice_lines:
                    invoice_lines[partner_id] = {}

                cont_nr_vals['name'] = self._get_elmnt_text(line, 'container_number')
                pricelist_qty = 1

                category = self._get_elmnt_text(line, 'transaction_category_id')
                category_id, service_ids = self._get_vbl_category_service(cr, uid, category)

                size = self._get_elmnt_text(line, 'container_size')
                size_id = imd_model.get_record_id(cr, uid, module, 'lct_product_size_' + size)

                status = self._get_elmnt_text(line, 'container_status')
                status_id = self._get_vbl_status(cr, uid, status)

                p_type = self._get_elmnt_text(line, 'container_type_id')
                type_id = self._get_vbl_type(cr, uid, p_type)

                properties = {
                    'category_id': category_id,
                    'service_ids': service_ids,
                    'size_id': size_id,
                    'status_id': status_id,
                    'type_id': type_id,
                }
                product_ids = product_model.get_products_by_properties(cr, uid, properties, context=context)
                for product_id in product_ids:
                    if product_id not in invoice_lines[partner_id]:
                        invoice_lines[partner_id][product_id] = []
                    cont_nr_id = cont_nr_model.create(cr, uid, dict(cont_nr_vals, pricelist_qty=1, quantity=1), context=context)
                    invoice_lines[partner_id][product_id].append(cont_nr_id)
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

    def _group_vbl_by_partner(self, cr, uid, ids, context=None):
        vbl_by_partner = {}
        for vbl in self.browse(cr, uid, ids, context=context):
            if vbl.partner_id.id in vbl_by_partner:
                vbl_by_partner[vbl.partner_id.id].append(vbl.id)
            else:
                vbl_by_partner[vbl.partner_id.id] = [vbl.id]
        for vbl_ids in vbl_by_partner.values():
            self._merge_vbls(cr, uid, vbl_ids, context=context)


    # GROUP INVOICES

    def group_invoices(self, cr, uid, ids, context=None):
        vbl_ids = self.search(cr, uid, [('id','in',ids), ('type2','=','vessel')], context=context)
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
            vdockage_ids.append(invoice_model.create(cr, uid, dockage_vals, context=context))
        return vdockage_ids

class account_invoice_group(osv.osv_memory):
    _name = 'account.invoice.group'

    def invoice_group(self, cr, uid, ids, context=None):
        invoice_model = self.pool.get('account.invoice')
        invoice_ids = context.get('active_ids', [])
        if invoice_model.search(cr, uid, [('id','in',invoice_ids), ('state','not in',['draft','proforma','proforma2'])], context=context):
            raise osv.except_osv(('Warning!'), ("You can only group invoices if they are in 'Draft' or 'Pro-Forma' state."))

        invoice_model.group_invoices(cr, uid, invoice_ids, context=context)
        return {'type': 'ir.actions.act_window_close'}
