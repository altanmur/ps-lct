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
from datetime import datetime

def transform_date(iso_format):
    return '/'.join([iso_format[8:], iso_format[5:7], iso_format[:4]])


class account_balance_report(report_sxw.rml_parse):
    _name = 'account_balance_report'
    _description = "Trial Balance"

    def __init__(self, cr, uid, name, context):
        self.context = context
        self.sum_debit = 0.00
        self.sum_credit = 0.00
        self.date_lst = []
        self.date_lst_string = ''
        self.result_acc = []
        super(account_balance_report, self).__init__(cr, uid, name, context=context)
        company_obj = self.pool.get('res.company')
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        company = company_obj.browse(cr, uid, user.company_id.id)
        total_debit = total_credit = total_balance = \
            total_prev_debit = total_prev_credit = 0.0
        fisc_obj = self.pool.get('account.fiscalyear')
        curr_fy = fisc_obj.browse(cr, uid, context['form']['fiscalyear_id'])
        prev_fy = fisc_obj.browse(cr, uid, context['form']['prev_fiscalyear_id'])
        period_obj = self.pool.get('account.period')
        if context.get('form').get('period_from') and context.get('form').get('period_to'):
            context.update({
                    'period_start_date': period_obj.browse(cr, uid, context['form']['period_from'], context=context).date_start,
                    'period_end_date': period_obj.browse(cr, uid, context['form']['period_to'], context=context).date_stop,
                })
        date_start = context.get('date_from') or context.get('period_start_date') or curr_fy.date_start
        date_stop = context.get('date_to') or context.get('period_end_date') or curr_fy.date_stop
        lines = self.lines(context['form'], [context['form'].get('chart_account_id')])
        for line in lines:
            total_debit += line.get('debit')
            total_credit += line.get('credit')
            total_balance += line.get('balance')
            total_prev_debit += line.get('prev_debit')
            total_prev_credit += line.get('prev_credit')
        now = datetime.now()
        then = datetime(now.year -1, 12, 31)
        disp_acc_raw = context['form']['display_account']
        wiz_obj = self.pool.get('lct_finance.balance.report')
        display_account = dict(wiz_obj.\
            fields_get(cr, uid, ['display_account'], context=context)\
            ['display_account']['selection'])[disp_acc_raw]
        self.localcontext.update({
            # FIXME: these come from the wizard.
            'company_name': company.name,
            'current_date': now.strftime('%d/%m/%Y'),
            'current_time': now.strftime('%H:%M:%S'),
            'display_account': display_account,
            'start_date': transform_date(date_start),
            'end_date': transform_date(date_stop),
            'prev_period_end': prev_fy.id and transform_date(prev_fy.date_stop) \
                                or then.strftime('%d/%m/%Y'),
            'total_prev_debit': total_prev_debit,
            'total_prev_credit': total_prev_credit,
            'total_debit': total_debit,
            'total_credit': total_credit,
            'total_balance': total_balance,
            'lines': lines,
            })

    def lines(self, form, ids=None, done=None):
        def _process_child(accounts, disp_acc, parent):
                account_rec = [acct for acct in accounts if acct['id']==parent][0]
                currency_obj = self.pool.get('res.currency')
                acc_id = self.pool.get('account.account').browse(self.cr, self.uid, account_rec['id'])
                currency = acc_id.currency_id and acc_id.currency_id or acc_id.company_id.currency_id
                res = {
                    'id': account_rec['id'],
                    'type': account_rec['type'],
                    'code': account_rec['code'],
                    'name': account_rec['name'],
                    'level': account_rec['level'],
                    'debit': account_rec['debit'],
                    'credit': account_rec['credit'],
                    'balance': account_rec['balance'],
                    'prev_debit': account_rec['prev_debit'],
                    'prev_credit': account_rec['prev_credit'],
                    'prev_balance': account_rec['prev_balance'],
                    'parent_id': account_rec['parent_id'],
                    'bal_type': '',
                }
                self.sum_debit += account_rec['debit']
                self.sum_credit += account_rec['credit']
                if disp_acc == 'movement':
                    if not currency_obj.is_zero(self.cr, self.uid, currency, res['credit']) \
                       or not currency_obj.is_zero(self.cr, self.uid, currency, res['debit']) \
                       or not currency_obj.is_zero(self.cr, self.uid, currency, res['balance']):
                        self.result_acc.append(res)
                elif disp_acc == 'not_zero':
                    if not currency_obj.is_zero(self.cr, self.uid, currency, res['balance']):
                        self.result_acc.append(res)
                else:
                    self.result_acc.append(res)
                if account_rec['child_id']:
                    for child in account_rec['child_id']:
                        _process_child(accounts,disp_acc,child)

        obj_account = self.pool.get('account.account')
        if not ids:
            ids = self.ids
        if not ids:
            return []
        if not done:
            done={}

        ctx = self.context.copy()

        ctx['fiscalyear'] = form['fiscalyear_id']
        ctx['prev_fiscalyear'] = form['prev_fiscalyear_id']
        if form['filter'] == 'filter_period':
            ctx['period_from'] = form['period_from']
            ctx['period_to'] = form['period_to']
        elif form['filter'] == 'filter_date':
            ctx['date_from'] = form['date_from']
            ctx['date_to'] =  form['date_to']
        ctx['state'] = form['target_move']
        parents = ids
        child_ids = obj_account._get_children_and_consol(self.cr, self.uid, ids, ctx)
        if child_ids:
            ids = child_ids
        accounts = obj_account.read(self.cr, self.uid, ids,
            ['type', 'code', 'name',
             'debit', 'credit', 'balance',
             'prev_debit', 'prev_credit', 'prev_balance',
             'parent_id', 'level', 'child_id'],
            ctx)

        for parent in parents:
                if parent in done:
                    continue
                done[parent] = 1
                _process_child(accounts,form['display_account'],parent)
        return self.result_acc



report_sxw.report_sxw('report.webkit.account_balance_report',
                      'account.voucher',
                      'lct_finance/report/account_balance.html.mako',
                      parser=account_balance_report)
