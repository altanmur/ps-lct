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

class account_move_line(osv.osv):
    _inherit = "account.move.line"

    _columns = {
        'to_update_asset_id': fields.many2one('account.asset.asset', string='Asset'),
    }

    def create(self, cr, uid, vals, context=None):
        res = super(account_move_line, self).create(cr, uid, vals, context=context)
        if vals.get("to_update_asset_id"):
            value = vals.get("debit", 0) - vals.get("credit", 0)
            self.pool.get("account.asset.asset").add_value(cr, uid, vals.get("to_update_asset_id"), value, context=context)
        return res

    def get_asset_move_type(self, cr, uid, id, context=None):
        context = context or {}
        move_line = self.browse(cr, uid, id[0], context)
        credit, debit = False, False
        for line in move_line.move_id.line_id:
            if line.to_update_asset_id:
                if line.credit:
                    credit = True
                if line.debit:
                    debit = True
        return [
            None,
            "aquisition",
            "scrap",
            "transfer",
        ][2*credit + debit]
