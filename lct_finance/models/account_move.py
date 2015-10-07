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

from openerp.osv import fields, orm


class account_move(orm.Model):
    _inherit = 'account.move'

    _columns = {
        'create_date': fields.datetime("Creation Date", readonly=True),
    }

class account_move_line(orm.Model):
    _inherit = 'account.move.line'


    def _get_move_lines(self, cr, uid, ids, context=None):
        result = []
        for move in self.pool.get('account.move').browse(cr, uid, ids, context=context):
            for line in move.line_id:
                result.append(line.id)
        return result


    _columns = {
        'is_negative' : fields.related('move_id', 'is_negative', string='egative entry', type='boolean',
                                store = {
                                    'account.move': (_get_move_lines, ['is_negative'], 20)
                                }),
    }


class account_move(orm.Model):
    _inherit = 'account.move'

    _columns = {
        'is_negative': fields.boolean("Negative entry"),
    }

