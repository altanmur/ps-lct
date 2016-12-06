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

from openerp.addons.account.report.account_tax_report import tax_report

# Monkey see, monkey patch !
# Fix when missing period_from / period_to
# Previous behavior when missing one of those leads to take periods from the first fiscal year in db.
def patch_set_context(self, objects, data, ids, report_type=None):
    new_ids = ids
    res = {}
    self.period_ids = []
    period_obj = self.pool.get('account.period')
    self.display_detail = data['form']['display_detail']
    res['periods'] = ''
    fy_id = data['form'].get('fiscalyear_id', False)
    res['fiscalyear'] = fy_id

    if not data['form'].get('period_from') and fy_id:
        period_ids = period_obj.search(self.cr, self.uid, [('fiscalyear_id', '=', fy_id)], order='date_start', limit=1)
        data['form'].update({
                'period_from': period_ids[0] if period_ids else False,
            })
    if not data['form'].get('period_to') and fy_id:
        period_ids = period_obj.search(self.cr, self.uid, [('fiscalyear_id', '=', fy_id)], order='date_start desc', limit=1)
        data['form'].update({
                'period_to': period_ids[0] if period_ids else False,
            })

    if data['form'].get('period_from', False) and data['form'].get('period_to', False):
        self.period_ids = period_obj.build_ctx_periods(self.cr, self.uid, data['form']['period_from'], data['form']['period_to'])
        periods_l = period_obj.read(self.cr, self.uid, self.period_ids, ['name'])
        for period in periods_l:
            if res['periods'] == '':
                res['periods'] = period['name']
            else:
                res['periods'] += ", "+ period['name']
    return super(tax_report, self).set_context(objects, data, new_ids, report_type=report_type)


tax_report.set_context = patch_set_context