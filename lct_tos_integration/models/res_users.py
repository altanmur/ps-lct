# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#    Copyright (C) 2010-2013 OpenERP s.a. (<http://openerp.com>).
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
import openerp
from openerp import SUPERUSER_ID
from openerp.osv import fields,osv
from lxml import etree

CATEGORIES = ['Accounting & Finance', 'Human Resources', 'Administration', 'TOS']
GROUPS = ['Invoicing & Payments', 'HR Base group', 'Officer', 'Access Rights', 'Accountant']

class res_users(osv.osv):

    _inherit = 'res.users'

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        res = super(res_users,self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        group_ids = self.pool.get('res.groups').search(cr, uid, [('name', 'in', GROUPS)], context=context)
        groups_to_hide = ['in_group_'+str(group_id) for group_id in group_ids]
        doc = etree.XML(res['arch'])
        for node in doc.xpath("//page[@string='Access Rights']"):
            for elmt in node:
                to_invisible = True
                for sub_elmt in elmt:
                    if sub_elmt.tag == 'separator':
                        if 'string' in sub_elmt.attrib and sub_elmt.attrib['string'] in CATEGORIES:
                            to_invisible = False
                        else:
                            to_invisible = True
                    if to_invisible:
                        sub_elmt.set('modifiers', '{"invisible": 1}')
                    else:
                        if 'name' in sub_elmt.attrib and sub_elmt.attrib['name'] in groups_to_hide:
                            sub_elmt.set('modifiers', '{"invisible": 1}')
        res['arch'] = etree.tostring(doc)
        return res
