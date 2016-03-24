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

from openerp.osv import fields, orm, osv


class account_invoice(orm.Model):
    _inherit = 'account.invoice'

    _columns = {
        'bank': fields.char('Bank', size=64),
        'bank_bic': fields.char('Swift', size=64),
        'iban': fields.char('IBAN', size=64),
        'bank_code': fields.char('Bank Code', size=64),
        'counter_code': fields.char('Counter Code', size=64),
        'acc_number': fields.char('Account Number', size=64),
        'rib': fields.char('RIB', size=64),
        'customer_nbr': fields.char('Customer Number', size=64),
        'reference' : fields.text('Reference'),
        # For the invoice report (fiche d'imputation)
        'create_date': fields.datetime('Creation Date' , readonly=True),
    }

    def action_move_create(self, cr, uid, ids, context=None):
        invoice_line_model = self.pool.get('account.invoice.line')
        for invoice in self.browse(cr, uid, ids, context=context):
            for line in invoice.invoice_line:
                if line.invoice_line_tax_id or not line.product_id:
                    continue
                if line.product_id.vat_free_income_account_id:
                    invoice_line_model.write(cr, uid, [line.id], {'account_id': line.product_id.vat_free_income_account_id.id}, context=context)
                elif line.product_id.categ_id and line.product_id.categ_id.vat_free_income_account_id:
                    invoice_line_model.write(cr, uid, [line.id], {'account_id': line.product_id.categ_id.vat_free_income_account_id.id}, context=context)
        return super(account_invoice, self).action_move_create(cr, uid, ids, context=context)

    def line_get_convert(self, cr, uid, x, part, date, context=None):
        res = super(account_invoice, self).line_get_convert(cr, uid, x, part, date, context)
        res['name'] = x['name']
        return res


class account_invoice_line(osv.osv):
    _inherit = "account.invoice.line"

    def move_line_get_item(self, cr, uid, line, context=None):
        res = super(account_invoice_line, self).move_line_get_item(cr, uid, line, context)
        res['name'] = line.name.split('\n')[0]
        return res