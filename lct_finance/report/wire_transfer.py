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

from report import report_sxw
from openerp.tools.amount_to_text import amount_to_text


class wire_transfer_report(report_sxw.rml_parse):
    _name = 'wire_transfer_report'
    _description = "Internal Wire Transfer"

    def __init__(self, cr, uid, name, context):
        super(wire_transfer_report, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'vouchers': self.get_vouchers(cr, uid, context=context),
            })

    # Not sure how well this will perform on big data sets. The yearly stuff is
    # duplicating a ton of lookups. If it turns out this performs badly, rewrite
    # to use queries instead of ORM.
    def get_vouchers(self, cr, uid, context=None):
        retval = {}
        voucher_obj = self.pool.get('account.voucher')
        voucher_ids = context.get('active_ids')
        vouchers = voucher_obj.browse(cr, uid, voucher_ids, context=context)
        for voucher in vouchers:
            currency_obj = self.pool.get('res.currency')
            voucher_curr_id = voucher.currency_id.id
            company_obj = self.pool.get('res.company')
            user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
            company = company_obj.browse(cr, uid, user.company_id.id)
            default_curr_id = company.currency_id.id
            default_currency = currency_obj.browse(cr, uid, default_curr_id, context=context).symbol
            amount_default = currency_obj.compute(cr, uid, voucher_curr_id, default_curr_id,
                voucher.amount)
            retval[voucher] = {
                # Yup, hardcpoding lang for this one. It's only gonna be used
                # in French.
                'amount_text': amount_to_text(voucher.amount, lang='fr',
                    currency=voucher.currency_id.symbol),
                'amount_default': amount_default,
                'amount_text_default': amount_to_text(amount_default, lang='fr',
                    currency=default_currency),
                'default_currency': default_currency,
                'diff_currencies': voucher_curr_id != default_curr_id,

            }
        return retval



report_sxw.report_sxw('report.webkit.wire_transfer_report',
                      'account.voucher',
                      'lct_finance/report/wire_transfer.html.mako',
                      parser=wire_transfer_report)
