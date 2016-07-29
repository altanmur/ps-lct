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
    'name': 'LCT security',
    'author': 'OpenERP SA',
    'version': '0.1',
    'depends': [
        'base',
        'auth_crypt',
        'LCT_supplier_invoice',
    ],
    'category' : 'Tools',
    'summary': 'LCT security',
    'description': """
        LCT security
    """,
    'data': [
        'views/res_groups.xml',
        'views/change_password_user.xml',
        'cron/update_tmp_acl.xml',
        ],
    'js': ['static/src/js/coresetup.js'],
    'images': [],
    'demo': [],
    'installable': True,
    'application' : True,
}
