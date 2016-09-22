# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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

import time

from openerp.tools.translate import _
from openerp.report import report_sxw
from openerp.addons.account.report.account_partner_balance import partner_balance
import datetime

def d2s(d, s="%Y-%m-%d"):
    return d.strftime(s)

def _get_prev_range_periods(self, start_period_id, end_period_id):
    period_obj = self.pool.get('account.period')
    start_period = period_obj.browse(self.cr, self.uid, start_period_id)
    date_start = "1900-01-01"
    date_stop = start_period.date_stop

    oldest_period_id = period_obj.search(self.cr, self.uid, [], order='end_date', limit=1)[0]
    before_start_period_ids = period_obj.search(self.cr, self.uid, [('date_stop', '<', date_stop)], order='end_date desc', limit=1)
    if not before_start_period_ids:
        return {}
    before_start_period_id = before_start_period_ids[0]

    period_ids = period_obj.search(self.cr, self.uid, [('date_start', '>', date_start), ('date_stop','<', date_stop)])

    return {
        'period_from': oldest_period_id,
        'period_to': before_start_period_id,
        'periods': period_ids,
        'fiscalyear': None,
    }

def _get_prev_fiscalyears(self, fy_id):
    fy_obj = self.pool.get('account.fiscalyear')
    fy = fy_obj.browse(self.cr, self.uid, fy_id)
    before_fy_ids = fy_obj.search(self.cr, self.uid, [('date_stop', '<', fy.date_start)])
    if not before_fy_ids:
        return {}
    return {
        'fiscalyear': before_fy_ids,
    }

def _get_prev_ctx(self, ctx):
    df = ctx.get('date_from')
    period_from = ctx.get('period_from')
    period_to = ctx.get('period_to')
    fiscalyear = ctx.get('fiscalyear')
    if df and ctx.get('date_to'):
        before_date_from = datetime.datetime.strptime(df, "%Y-%m-%d") - datetime.timedelta(days=1)
        begin_date = datetime.datetime(1900, 1, 1)
        ctx.update({
            'date_from': d2s(begin_date),
            'date_to': d2s(before_date_from),
            'fiscalyear': None,
            })
    elif period_from and period_to:
        ctx_update = _get_prev_range_periods(self, period_from, period_to)
        if not ctx_update:
            return {}
        ctx.update(ctx_update)
    elif fiscalyear:
        ctx_update = _get_prev_fiscalyears(self, fiscalyear)
        if not ctx_update:
            return {}
        ctx.update(ctx_update)
    else:
        return {}
    return ctx

# Monkey patching
def set_context(self, objects, data, ids, report_type=None):
    self.display_partner = data['form'].get('display_partner', 'non-zero_balance')
    obj_move = self.pool.get('account.move.line')
    self.query = obj_move._query_get(self.cr, self.uid, obj='l', context=data['form'].get('used_context', {}))
    self.result_selection = data['form'].get('result_selection')
    self.target_move = data['form'].get('target_move', 'all')

    if (self.result_selection == 'customer' ):
        self.ACCOUNT_TYPE = ('receivable',)
    elif (self.result_selection == 'supplier'):
        self.ACCOUNT_TYPE = ('payable',)
    else:
        self.ACCOUNT_TYPE = ('payable', 'receivable')

    self.cr.execute("SELECT a.id " \
            "FROM account_account a " \
            "LEFT JOIN account_account_type t " \
                "ON (a.type = t.code) " \
                "WHERE a.type IN %s " \
                "AND a.active", (self.ACCOUNT_TYPE,))
    self.account_ids = [a for (a,) in self.cr.fetchall()]
    res = super(partner_balance, self).set_context(objects, data, ids, report_type=report_type)
    lines = self.lines()
    sum_debit = sum_credit = sum_litige = 0
    for line in filter(lambda x: x['type'] == 3, lines):
        sum_debit += line['debit'] or 0
        sum_credit += line['credit'] or 0
        sum_litige += line['enlitige'] or 0
    self.localcontext.update({
        'lines': lambda: lines,
        'sum_debit': lambda: sum_debit,
        'sum_credit': lambda: sum_credit,
        'sum_litige': lambda: sum_litige,
    })

    ctx = data['form'].get('used_context', {})
    opening_ctx = _get_prev_ctx(self, ctx)
    if opening_ctx:
        self.query = obj_move._query_get(self.cr, self.uid, obj='l', context=opening_ctx)
        opening_lines = self.lines()
    else:
        opening_lines = []

    mix_lines = {}
    for line in lines:
        code = line.get('code')
        if code not in mix_lines:
            mix_lines.update({
                code: {},
                })
        name = line.get('name')
        mix_lines[code].update({
            name: {
                'move_debit': line.get('debit'),
                'move_credit': line.get('credit'),
                'code': line.get('code'),
                'type': line.get('type'),
                },
            })

    for line in opening_lines:
        code = line.get('code')
        if code not in mix_lines:
            mix_lines.update({
                code: {},
                })
        name = line.get('name')
        opening_data = {
            'opening_debit': line.get('debit'),
            'opening_credit': line.get('credit'),
            'code': line.get('code'),
            'type': line.get('type'),
            }
        if name in mix_lines[code]:
            mix_lines[code][name].update(opening_data)
        else:
            mix_lines[code].update({
                name: opening_data,
                })

    lines = []
    for mix_acc_lines in mix_lines.values():
        acc_lines = [line for line in mix_acc_lines.values()]


    return res


partner_balance.set_context = set_context
