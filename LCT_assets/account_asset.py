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
from datetime import datetime, date
from openerp.exceptions import Warning


class account_asset_asset(osv.osv):

    _inherit = "account.asset.asset"

    def _get_move_line(self, cr, uid, ids, move_type, context=None):
        result = {}
        for record in self.browse(cr, uid, ids, context=context):
            result.update({
                record.id: [move_line.id for move_line in record.move_line_ids if move_line.get_asset_move_type() == move_type],
            })
        return result

    def _get_aquisition_ids(self, cr, uid, ids, field_name, arg, context=None):
        return self._get_move_line(cr, uid, ids, "aquisition", context)

    def _get_transfer_ids(self, cr, uid, ids, field_name, arg, context=None):
        return self._get_move_line(cr, uid, ids, "transfer", context)

    def _get_scrap_ids(self, cr, uid, ids, field_name, arg, context=None):
        return self._get_move_line(cr, uid, ids, "scrap", context)

    _columns = {
        'purchase_date_2': fields.date('Purchase Date', required=True),
        'allocation' : fields.char('Allocation'),
        'dep_2013' : fields.float('Sum of depreciations until 31/12/2013'),
        'move_line_ids': fields.one2many("account.move.line", "to_update_asset_id", string="Move Lines"),
        'aquisition_ids': fields.function(_get_aquisition_ids, type="many2many", relation="account.move.line", string="Aquisitions"),
        'transfer_ids': fields.function(_get_transfer_ids, type="many2many", relation="account.move.line", string="Transfers"),
        'scrap_ids': fields.function(_get_scrap_ids, type="many2many", relation="account.move.line", string="Scraps"),
    }

    def create(self, cr, uid, vals, context=None):
        if not vals.get('purchase_date_2', False):
            vals['purchase_date_2'] = vals.get('purchase_date', False)
        return super(account_asset_asset, self).create(cr, uid, vals, context=context)

    def add_value(self, cr, uid, id, value, context=None):
        record = self.browse(cr, uid, id, context)
        if record.value_residual + value < 0:
            raise Warning("Credit is too important.\nResidual Value of the asset cannot be negative.")
        save_state = record.state
        if save_state not in "opendraft":
            return
        if save_state == "open":
            record.set_to_draft()
        record.write({
            "purchase_value": record.purchase_value + value,
        })
        if save_state == "open":
            record.validate()
        record.compute_depreciation_board()


    def _compute_board_amount(self, cr, uid, asset, i, residual_amount, amount_to_depr, undone_dotation_number, posted_depreciation_line_ids, total_days, depreciation_date, context=None):
        #by default amount = 0
        amount = 0
        if i == undone_dotation_number:
            amount = residual_amount
        else:
            if asset.method == 'linear':
                amount = amount_to_depr / (undone_dotation_number - len(posted_depreciation_line_ids))
            elif asset.method == 'degressive':
                amount = residual_amount * asset.method_progress_factor
        return amount

    def _compute_board_undone_dotation_nb(self, cr, uid, asset, depreciation_date, total_days, context=None):
        return asset.method_number - len(asset.depreciation_line_ids)


class account_asset_depreciation_line(osv.osv):

    _inherit = "account.asset.depreciation.line"

    def cron_post_lines(self, cr, uid, context=None):
        """
        Find depreciation lines that meet the following criteria:

         - depreciation_date is in the past
         - parent asset is marked as "depreciation_journal"
         - parent state is "open"
         - move_check is False (not posted yet)

        Then for each created line whose month is not the current month, set the date to
        DAY_OF_PARENT_ASSET_purchase_date / MONTH_OF_LINE_depreciation_date / YEAR_OF_LINE_depreciation_date

        Then automatically post all the lines (i.e. creating account moves)

        Then update the move_id's and all their lines to have the same date as the depreciation line

        This function is called every month on the 31st by a cron.
        """
        ids = self.search(cr, uid, [('asset_id.category_id.journal_id.depreciation_journal', '=', True),
                                    ('asset_id.category_id.account_asset_id.type', '!=', 'view'),
                                    ('asset_id.category_id.account_depreciation_id.type', '!=', 'view'),
                                    ('asset_id.category_id.account_expense_depreciation_id.type', '!=', 'view'),
                                    ('move_check','=',False),
                                    ('depreciation_date','<','now()'),
                                    ('parent_state','=','open')])

        # fix depreciation_date if line is from a previous month
        previous_month_lines = {}
        for line in self.browse(cr, uid, ids, context=context):
            depreciation_date = datetime.strptime(line.depreciation_date, '%Y-%m-%d').date()

            if date.today().month != depreciation_date.month:

                asset_purchase_date = datetime.strptime(line.asset_id.purchase_date, '%Y-%m-%d').date()
                previous_month_lines[line.id] = date(depreciation_date.year, depreciation_date.month, asset_purchase_date.day)
                self.write(cr, uid, line.id, {'depreciation_date': previous_month_lines[line.id]})

        # create moves for depreciation lines
        self.create_move(cr, uid, ids, context=context)

        # update dates on move_id's and move_id line's on all lines from previous months
        for line_id, line_date in previous_month_lines.items():
            line = self.browse(cr, uid, line_id, context=context)
            line.move_id.write({'date': line_date})
            for move_line in line.move_id.line_id:
                move_line.write({'date': line_date})

        return True
