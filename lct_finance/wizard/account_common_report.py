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

import time
from openerp.addons.account.wizard.account_report_common import account_common_report

# Monkey patching so that we pick the opening period by default when we filter
# on periods in all reports inheriting from account.common.report
def onchange_filter(self, cr, uid, ids, filter='filter_no', fiscalyear_id=False, context=None):
    res = {'value': {}}
    if filter == 'filter_no':
        res['value'] = {'period_from': False, 'period_to': False, 'date_from': False ,'date_to': False}
    if filter == 'filter_date':
        res['value'] = {'period_from': False, 'period_to': False, 'date_from': time.strftime('%Y-01-01'), 'date_to': time.strftime('%Y-%m-%d')}
    if filter == 'filter_period' and fiscalyear_id:
        start_period = end_period = False
        cr.execute('''
            SELECT * FROM (SELECT p.id
                           FROM account_period p
                           LEFT JOIN account_fiscalyear f ON (p.fiscalyear_id = f.id)
                           WHERE f.id = %s
                           ORDER BY p.date_start ASC, p.special DESC
                           LIMIT 1) AS period_start
            UNION ALL
            SELECT * FROM (SELECT p.id
                           FROM account_period p
                           LEFT JOIN account_fiscalyear f ON (p.fiscalyear_id = f.id)
                           WHERE f.id = %s
                           AND p.date_start < NOW()
                           AND p.special = false
                           ORDER BY p.date_stop DESC
                           LIMIT 1) AS period_stop''', (fiscalyear_id, fiscalyear_id))
        periods =  [i[0] for i in cr.fetchall()]
        if periods and len(periods) > 1:
            start_period = periods[0]
            end_period = periods[1]
        res['value'] = {'period_from': start_period, 'period_to': end_period, 'date_from': False, 'date_to': False}
    return res

account_common_report.onchange_filter = onchange_filter
