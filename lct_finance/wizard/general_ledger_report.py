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
from openerp.exceptions import Warning

class account_report_general_ledger(osv.osv_memory):
    _inherit = "account.report.general.ledger"

    _columns = {
        'filter_accounts': fields.boolean('Filter Accounts', required=False),
        'account_ids': fields.many2many('account.account', 'account_account_res_account_rel', 'account_id', 'account2_id', 'Accounts'),
        'accounts_to_print': fields.selection([
            ('all', 'All accounts'),
            ('parents', 'Parent accounts only'),
            ('children', 'Children accounts only'),
            ],
            string='Accounts to be printed',
            required=True)
    }

    _defaults = {
        'amount_currency': False,
        'accounts_to_print': 'all',
    }

    def _print_report(self, cr, uid, ids, data, context=None):
        if context is None:
            context = {}
        data = self.pre_print_report(cr, uid, ids, data, context=context)
        data['form'].update(self.read(cr, uid, ids, ['landscape',  'initial_balance', 'amount_currency', 'sortby'])[0])
        if not data['form']['fiscalyear_id']:# GTK client problem onchange does not consider in save record
            data['form'].update({'initial_balance': False})
        if context.get('xlsx_export'):
            return {'type': 'ir.actions.report.xml',
                    'report_name': 'xlsx.general_ledger',
                    'datas': data,
                    'context': context}
        if context.get('xls_export'):
            raise Warning("The xls report is deprecated, use the xlsx report")
        elif data['form']['landscape']:
            return { 'type': 'ir.actions.report.xml', 'report_name': 'account.general.ledger_landscape', 'datas': data}
        return { 'type': 'ir.actions.report.xml', 'report_name': 'account.general.ledger', 'datas': data}


    def check_report(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        data = {}
        data['ids'] = context.get('active_ids', [])
        data['model'] = context.get('active_model', 'ir.ui.menu')
        data['form'] = self.read(cr, uid, ids,
                        ['date_from',  'date_to',  'fiscalyear_id', 'journal_ids',
                        'period_from', 'period_to',  'filter',  'chart_account_id',
                        'target_move', 'filter_accounts', 'account_ids', 'accounts_to_print'],
                        context=context)[0]
        if data['form'].get('filter_accounts') and data['form'].get('account_ids'):
            data['ids'] = data['form']['account_ids']
            data['model'] = 'account.account'  # Not exactly clean, but it works.
        for field in ['fiscalyear_id', 'chart_account_id', 'period_from', 'period_to']:
            if isinstance(data['form'][field], tuple):
                data['form'][field] = data['form'][field][0]
        used_context = self._build_contexts(cr, uid, ids, data, context=context)
        data['form']['periods'] = used_context.get('periods', False) and used_context['periods'] or []
        data['form']['used_context'] = dict(used_context, lang=context.get('lang', 'en_US'))
        return self._print_report(cr, uid, ids, data, context=context)

    def xls_export(self, cr, uid, ids, context=None):
        return self.check_report(cr, uid, ids, context=context)

account_report_general_ledger()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
