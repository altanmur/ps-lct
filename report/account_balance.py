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


class account_balance_report(report_sxw.rml_parse):
    _name = 'account_balance_report'
    _description = "Trial Balance"

    def __init__(self, cr, uid, name, context):
        super(account_balance_report, self).__init__(cr, uid, name, context=context)
        company_obj = self.pool.get('res.company')
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        company = company_obj.browse(cr, uid, user.company_id.id)
        total_debit = total_credit = total_balance = \
            total_prev_debit = total_prev_credit = 0.0
        lines = self.get_lines(cr, uid, context=context)
        for line in lines:
            total_debit += line.get('debit')
            total_credit += line.get('credit')
            total_balance += line.get('balance')
        self.localcontext.update({
            # FIXME: these come from the wizard.
            'company_name': company.name,
            'start_date': 'foo',
            'end_date': 'foo',
            'total_prev_debit': 0.0,
            'total_prev_credit': 0.0,
            'total_debit': total_debit,
            'total_credit': total_credit,
            'total_balance': total_balance,
            'lines': lines,
            })

    def get_lines(self, cr, uid, context=None):
        retval = []
        account_obj = self.pool.get('account.account')
        account_ids = context.get('active_ids')
        accounts = account_obj.browse(cr, uid, account_ids, context=context)
        for account in accounts:
            retval.append({
                'account_nbr': 'acct_nbr',
                'account_name': 'accdt_name',
                'prev_debit': 0.0,
                'prev_credit': 0.0,
                'debit': 0.0,
                'credit': 0.0,
                'balance': 0.0,
            })
        return retval



report_sxw.report_sxw('report.webkit.account_balance_report',
                      'account.voucher',
                      'lct_finance/report/account_balance.html.mako',
                      parser=account_balance_report)
