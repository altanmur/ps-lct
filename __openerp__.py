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

{
    'name': 'LCT Finance',
    'version': '1.0',
    'category': 'Tools',
    'description': """
Finance Module for LCT
======================

Small modifications to the account and account_budget modules.
    """,
    'author': 'OpenERP SA',
    'depends': ['account', 'account_budget', 'account_voucher', 'report_webkit', 'LCT_assets', 'LCT_supplier_invoice'],
    'data': [
        'views/crossovered_budget.xml',
        'views/crossovered_budget_line.xml',
        'views/account_move.xml',
        'views/account_voucher.xml',
        'data/ir.header_webkit.xml',
        'views/account_invoice.xml',
        'views/res_partner_bank.xml',
        'data/ir_header_webkit_finance_portrait.xml',
        'data/ir_header_webkit_finance_landscape.xml',
        'report/reports.xml',
        'wizard/account_report_menu.xml',
        'wizard/cash_flow.xml',
        'wizard/depreciation_table.xml',
        'wizard/liasse_fiscale.xml',
        'wizard/balance_sheet.xml',
        'wizard/profit_loss.xml',
        'wizard/account_balance_report.xml',
        'wizard/partner_ledger_report.xml',
        'wizard/general_ledger_report.xml',
        'wizard/file_download.xml',
    ],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
    'images': [],
    'css': [],
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
