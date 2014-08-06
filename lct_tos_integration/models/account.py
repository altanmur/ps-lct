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

class lct_container_number(osv.osv):
    _name = 'lct.container.number'

    _columns = {
        'name': fields.char('Container Number'),
    }


class account_invoice_line(osv.osv):
    _inherit = 'account.invoice.line'

    _columns = {
        'cont_nr_ids': fields.many2many('lct.container.number', 'lct_container_number_rel', 'invoice_line_id', 'cont_nr_id', 'Container numbers'),
        'cont_operator': fields.char('Container operator'),
        'book_nr': fields.char('Booking number'),
    }

class account_voucher(osv.osv):
    _inherit = 'account.voucher'

    _columns = {
        'cashier_rcpt_nr': fields.char('Cashier receipt number'),
    }

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

    def create(self, cr, uid, vals, context=None):
        if 'cashier_rcpt_nr' not in vals:
            vals['cashier_rcpt_nr'] = self._get_sequence(cr, uid, 'lct_tos_integration', 'sequence_cashier_receipt_number', context=context)
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

