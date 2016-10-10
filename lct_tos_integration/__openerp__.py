# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2012 Tiny SPRL (<http://tiny.be>).
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
    'name': 'LCT TOS integration',
    'author': 'OpenERP SA',
    'version': '0.1',
    'depends': ['base', 'account', 'product', 'account_voucher', 'hr',
                'base_vat', 'sale', 'account_check_writing', 'lct_finance',
                'LCT_supplier_invoice', 'LCT_supplier_invoice', 'lct_security'],
    'category' : 'Tools',
    'summary': 'LCT TOS integration',
    'description': """
        LCT TOS integration
    """,
    'data': [
        'views/settings_menu.xml',
        'security/group_category.xml',
        'security/ir.module.category.csv',
        'security/res.groups.csv',
        'security/ir.model.access.csv',
        'security/ir.rule.csv',

        'security_new/ir.module.category.csv',
        'security_new/res.groups.csv',
        'security_new/ir.model.access.csv',
        'security_new/ir_values.xml',

        'views/account.xml',
        'views/ftp_config.xml',
        'views/product.xml',
        'views/product_properties.xml',
        'data/product_properties.xml',
        'data/products.xml',
        'data/cron.xml',
        'data/ir_sequences.xml',
        'views/lct_tos_import_data.xml',
        'views/lct_tos_vessel.xml',
        'data/actions.xml',
        'views/pricelist.xml',
        'views/res_partner.xml',
        'views/tos_menu.xml',
        'views/lct_pending_yard_activity.xml',
        'views/lct_multiplying_rate.xml',
        'views/lct_tos_export_data.xml',
        'views/res_company.xml',
        'data/res_partner.xml',
        'reports/reports.xml',
        'views/res_users.xml',
        'views/export_button.xml',
        'reports/vessel_revenue.xml',
        'views/direction.xml',
        'data/direction.xml',
        'views/account_invoice.xml',
        ],
    'images': [],
    'demo': [],
    'installable': True,
    'application' : True,
}
