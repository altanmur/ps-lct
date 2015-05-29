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

class account_voucher(osv.osv):
    _inherit = 'account.voucher'

    _columns = {
        'origin_bank_id': fields.many2one('res.partner.bank', 'Origin bank account'),
        'internal_transfer': fields.boolean('Internal transfer'),
        'destination_bank_id': fields.many2one('res.partner.bank', 'Destination bank account'),
        'pos1_id': fields.many2one('auth_signature_position', 'Position 1'),
        'pos2_id': fields.many2one('auth_signature_position', 'Position 2'),
        'signee1_id': fields.many2one('res.partner', 'Signee 1'),
        'signee2_id': fields.many2one('res.partner', 'Signee 2'),
    }

    # account.voucher => account.voucher.line => account.move.line => invoice
    def get_invoice(self, cr, uid, ids, context=None):
        retval = None
        if isinstance(ids, list):
            ids = ids[0]
        voucher = self.browse(cr, uid, ids, context=context)
        if voucher and voucher.line_dr_ids:
            retval = voucher.line_dr_ids[0].move_line_id.invoice
        return retval

    def onchange_line_ids_lct(self, cr, uid, ids, line_dr_ids, line_cr_ids, amount, voucher_currency, type, context=None):
        context = context or {}
        if not line_dr_ids and not line_cr_ids:
            return {'value':{'writeoff_amount': 0.0}}
        line_osv = self.pool.get("account.voucher.line")
        line_dr_ids = resolve_o2m_operations(cr, uid, line_osv, line_dr_ids, ['amount'], context)
        line_cr_ids = resolve_o2m_operations(cr, uid, line_osv, line_cr_ids, ['amount'], context)
        fields = ['account_id', 'currency_id', 'move_line_id']
        for line in line_dr_ids + line_cr_ids:
            for field in fields:
                if isinstance(line.get(field), (tuple, list)):
                    line[field] = line[field][0]
        is_multi_currency = False
        for voucher_line in line_dr_ids+line_cr_ids:
            line_id = voucher_line.get('id') and self.pool.get('account.voucher.line').browse(cr, uid, voucher_line['id'], context=context).move_line_id.id or voucher_line.get('move_line_id')
            if line_id and self.pool.get('account.move.line').browse(cr, uid, line_id, context=context).currency_id:
                is_multi_currency = True
                break
        return {'value': {'writeoff_amount': self._compute_writeoff_amount(cr, uid, line_dr_ids, line_cr_ids, amount, type), 'is_multi_currency': is_multi_currency}}

    def onchange_journal_lct(self, cr, uid, ids, journal_id, line_ids, tax_id, partner_id, date, amount, ttype, company_id, context=None):
        res = self.onchange_journal(cr, uid, ids, journal_id, line_ids, tax_id, partner_id, date, amount, ttype, company_id, context=context)
        self.id_to_name_get(cr, uid, res, context=context)
        return res

    def onchange_amount_lct(self, cr, uid, ids, amount, rate, partner_id, journal_id, currency_id, ttype, date, payment_rate_currency_id, company_id, context=None):
        res = self.onchange_amount(cr, uid, ids, amount, rate, partner_id, journal_id, currency_id, ttype, date, payment_rate_currency_id, company_id, context=context)
        self.id_to_name_get(cr, uid, res, context=context)
        return res

    def onchange_partner_id_lct(self, cr, uid, ids, partner_id, journal_id, amount, currency_id, ttype, date, context=None):
        res = self.onchange_partner_id(cr, uid, ids, partner_id, journal_id, amount, currency_id, ttype, date, context=context)
        self.id_to_name_get(cr, uid, res, context=context)
        return res

    def id_to_name_get(self, cr, uid, res, context=None):
        if not res or not res.get('value'):
            return
        lines = res['value']['line_cr_ids'] + res['value']['line_dr_ids']
        if not lines:
            return
        fields = {
            'account_id': 'account.account',
            'currency_id': 'res.currency',
            'move_line_id': 'account.move.line',
        }
        for field, model in fields.iteritems():
            ids = list(set([line[field] for line in lines if line.get(field)]))
            name_gets = {id: (id, name) for id, name in self.pool.get(model).name_get(cr, uid, ids, context=context)}
            for line in lines:
                line[field] = name_gets[line[field]]

def resolve_o2m_operations(cr, uid, target_osv, operations, fields, context):
    results = []
    for operation in operations:
        result = None
        if not isinstance(operation, (list, tuple)):
            result = target_osv.read(cr, uid, operation, fields, context=context)
        elif operation[0] == 0:
            # may be necessary to check if all the fields are here and get the default values?
            result = operation[2]
        elif operation[0] == 1:
            result = target_osv.read(cr, uid, operation[1], fields, context=context)
            if not result: result = {}
            result.update(operation[2])
        elif operation[0] == 4:
            result = target_osv.read(cr, uid, operation[1], fields, context=context)
        if result != None:
            results.append(result)
    return results

