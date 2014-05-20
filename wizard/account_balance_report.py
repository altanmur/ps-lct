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

from openerp.osv import fields, osv

class account_balance_report(osv.osv_memory):
    _inherit = "account.common.account.report"
    _name = 'lct_finance.balance.report'
    _description = 'Trial Balance Report'

    _columns = {
        'prev_fiscalyear_id': fields.many2one('account.fiscalyear', 'Previous Fiscal Year', help='Keep empty for all open fiscal year'),
        'journal_ids': fields.many2many('account.journal', 'account_balance_report_journal_rel', 'account_id', 'journal_id', 'Journals', required=True),
    }

    _defaults = {
        'journal_ids': [],
    }

    def onchange_fiscalyear_id(self, cr, uid, ids, fiscalyear_id, context=None):
        retval = {}
        if fiscalyear_id:
            fy_obj = self.pool.get('account.fiscalyear')
            curr_year = fy_obj.browse(cr, uid, fiscalyear_id, context=context)
            prev_year_ids = fy_obj.search(cr, uid,
                [('date_stop', '<', curr_year.date_start)],
                order='date_stop DESC', limit=1)
            if prev_year_ids:
                retval['value'] = {'prev_fiscalyear_id': prev_year_ids[0]}
        return retval


    def _print_report(self, cr, uid, ids, data, context=None):
        data = self.pre_print_report(cr, uid, ids, data, context=context)
        context.update(data)
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'webkit.account_balance_report',
            'context': context}

    def check_report(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        data = {}
        data['ids'] = context.get('active_ids', [])
        data['model'] = context.get('active_model', 'ir.ui.menu')
        data['form'] = self.read(cr, uid, ids, ['date_from',  'date_to',
            'fiscalyear_id', 'prev_fiscalyear_id', 'journal_ids', 'period_from',
            'period_to',  'filter',  'chart_account_id', 'target_move'],
            context=context)[0]
        for field in ['fiscalyear_id', 'prev_fiscalyear_id', 'chart_account_id',
                      'period_from', 'period_to']:
            if isinstance(data['form'][field], tuple):
                data['form'][field] = data['form'][field][0]
        used_context = self._build_contexts(cr, uid, ids, data, context=context)
        data['form']['periods'] = used_context.get('periods', False) and used_context['periods'] or []
        data['form']['used_context'] = dict(used_context, lang=context.get('lang', 'en_US'))
        return self._print_report(cr, uid, ids, data, context=context)

account_balance_report()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
