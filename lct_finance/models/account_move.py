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

from openerp.osv import fields, orm, osv

class account_move(orm.Model):
    _inherit = 'account.move'

    _columns = {
        'create_date': fields.datetime("Creation Date", readonly=True),
        'is_negative': fields.boolean("Negative entry"),
    }


class account_move_line(osv.osv):
    _inherit = "account.move.line"

    _columns = {
        'name': fields.char('Name', required=True),
        }

    def onchange_partner_id_lct_fix_datetime(self, cr, uid, ids, move_id, partner_id, account_id=None, debit=0, credit=0, date=False, journal=False, context=None):
        if date and ' ' in date:
            date = date.split()[0]
        return self.onchange_partner_id(cr, uid, ids, move_id, partner_id, account_id, debit, credit, date, journal, context)

    def _check_no_view(self, cr, uid, ids, context=None):
        # No super because it is not adaptable.
        lines = self.browse(cr, uid, ids, context=context)
        for l in lines:
            if l.account_id.type in ('view'):
                return False
        return True

    _constraints = [
        (_check_no_view, 'You cannot create journal items on an account of type view or consolidation.', ['account_id']),
    ]