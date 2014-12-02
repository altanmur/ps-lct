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

from openerp.osv import fields, osv


class lct_multiplying_rate(osv.osv):
    _name = 'lct.multiplying.rate'

    _columns = {
        'name': fields.char('Name', required=True),
        'multiplying_rate': fields.float('Multiplying Rate For oog Containers', required=True),
        'active': fields.boolean('Active'),
    }

    def _check_active(self, cr, uid, ids, context=None):
        multi_rate_ids = self.search(cr, uid, [('active','=',True)], context=context)
        return len(multi_rate_ids) <= 1

    _constraints = [
        (_check_active, 'There can only be one active multiplying rate', ['active']),
    ]

    def get_active_rate(self, cr, uid, context=None):
        mult_rate_ids = self.search(cr, uid, [('active', '=', True)], context=context)
        return mult_rate_ids and self.browse(cr, uid, mult_rate_ids[0], context=context).multiplying_rate or 1.
