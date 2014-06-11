# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2014 OpenERP (<openerp@openerp-HP-ProBook-430-G1>)
#    All Rights Reserved
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
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

from osv import fields, osv
from tools.translate import _
from xlwt import Workbook,easyxf
from xlrd import open_workbook,XL_CELL_BLANK
from xlutils.copy import copy
import StringIO
import base64
from datetime import datetime
from datetime import date, timedelta
from tempfile import TemporaryFile
import os

class cash_flow(osv.osv_memory):

    _inherit = "account.common.account.report"
    _name = "lct_finance.cash.flow.report"

    def _getOutCell(self, outSheet, colIndex, rowIndex):
        row = outSheet._Worksheet__rows.get(rowIndex)
        if not row: return None
        cell = row._Row__cells.get(colIndex)
        return cell

    def _setOutCell(self, outSheet, col, row, value):
        previousCell = self._getOutCell(outSheet, col, row)
        outSheet.write(row, col, value)
        if previousCell:
            newCell = self._getOutCell(outSheet, col, row)
            if newCell:
                newCell.xf_idx = previousCell.xf_idx

    def _sum_balance(self, cr, uid, ids, pos_codes=(), neg_codes=(), context=None) :
        def _get_balance( cr, uid, code, context=None) :
            acc_obj = self.pool.get('account.account')
            acc_ids = acc_obj.search(cr, uid, [('code','ilike',code)],context=context)
            acc_id = acc_ids and acc_ids[0] or False
            if acc_id : return acc_obj.browse(cr,uid,acc_id,context=context).balance
            else : return 0.0
        res = 0.0
        for code in pos_codes :
            res += _get_balance(cr, uid, code, context=context)
        for code in neg_codes :
            res -= _get_balance(cr, uid, code, context=context)
        return res

    def _comp_balance(self, cr, uid, ids, codes=(), context=None) :
        res = 0.0
        acc_obj = self.pool.get('account.account')
        for code in codes :
            acc_ids = acc_obj.search(cr, uid, [('code','ilike',code)],context=context)
            acc_id = acc_ids and acc_ids[0] or False
            if acc_id :
                acc = acc_obj.browse(cr,uid,acc_id,context=context)
                res += acc.prev_balance - acc.balance
        return res

    def _set_dates(self, cr, uid, ids, context=None, sheet=None):
        if not sheet : return
        browser = self.browse(cr,uid,ids,context=context)[0]
        today_s = datetime.today().strftime("%d-%m-%Y")
        date1 = None
        date2 = None
        if browser.date_from and browser.date_to :
            date1 = browser.date_from
            date2 = browser.date_to
        elif browser.period_from and browser.period_to :
            date1 = browser.period_from.date_start
            date2 = browser.period_to.date_stop
        else :
            self._setOutCell(sheet, 1, 5, "Date of report :")
            self._setOutCell(sheet, 2, 5, today_s)

        if date1 and date2 :
            context['date_from'] = date1
            context['date_to'] = date2
            self._setOutCell(sheet, 1, 5, "Start date :")
            self._setOutCell(sheet, 1, 6, "End date :")
            self._setOutCell(sheet, 2, 5, datetime.strptime(date1,"%Y-%m-%d").strftime("%d-%m-%Y"))
            self._setOutCell(sheet, 2, 6, datetime.strptime(date2,"%Y-%m-%d").strftime("%d-%m-%Y"))
            self._setOutCell(sheet, 1, 4, "Date of report :")
            self._setOutCell(sheet, 2, 4, today_s)

    def _write_report(self, cr, uid, ids, context=None):
        module_path = __file__.split('wizard')[0]
        xls_file = os.path.join(module_path, 'data', 'cashflow.xls')
        template = open_workbook(xls_file, formatting_info=True)
        report = copy(template)
        rs = report.get_sheet(0)

        self._set_dates(cr, uid, ids, context=context, sheet=rs)


        balances = [0.0] * 22

        # Income before Tax, Depreciation, & Amortization
        pos_codes = (
            '2300XXXX',
            '220XXXXX',
            '34003000',
            )
        neg_codes = (
            '23009000',
            '36303100',
            )
        balances[0] = self._sum_balance(cr, uid, ids, pos_codes, neg_codes, context=context)
        self._setOutCell(rs, 3, 11,balances[0])

        # Financial result
        pos_codes = (
            )
        neg_codes = (
            '1501XXXX',
            '1502XXXX',
            )
        balances[1] = self._sum_balance(cr, uid, ids, pos_codes, neg_codes, context=context)
        self._setOutCell(rs, 3, 12, balances[1])

        # Depreciation
        pos_codes = (
            )
        neg_codes = (
            '152XXXXX',
            '153XXXXX',
            )
        balances[2] = self._sum_balance(cr, uid, ids, pos_codes, neg_codes, context=context)
        self._setOutCell(rs, 3, 13, balances[2])

        # Changes in non-cash other
        balances[3] = 0.0
        self._setOutCell(rs, 3, 14, balances[3])    # Always zero

        # Changes in Operating profit before working capital
        balances[4] = sum(balances[0:4])
        self._setOutCell(rs, 3, 15, balances[4])


        # Change in other current assets (non ICP)
        codes = (
            '20XXXXXX',
            )
        balances[5] = self._comp_balance(cr, uid, ids, codes, context=context)
        self._setOutCell(rs, 3, 17, balances[5])

        # Change in Account Payable (ICP)
        codes = (
            '321XXXXX',
            )
        balances[6] = self._comp_balance(cr, uid, ids, codes, context=context)
        self._setOutCell(rs, 3, 18, balances[6])

        # Change in other current liabilities
        codes = (
            '36201100',
            '3630XXXX',
            '36303100',
            '3640XXXX',
            )
        balances[7] = self._comp_balance(cr, uid, ids, codes, context=context)
        self._setOutCell(rs, 3, 19, balances[7])

        # Income generated from operations
        balances[8] = sum(balances[5:8])
        self._setOutCell(rs, 3, 20, balances[8])

        # Net cash from operating activities
        balances[9] = balances[4] + balances[8]
        self._setOutCell(rs, 3, 21, balances[9])


        # Acquisition of tangible fixed assets
        codes = (
            '2200XXXX',
            )
        balances[10] = self._comp_balance(cr, uid, ids, codes,context=context)
        self._setOutCell(rs, 3, 23, balances[10])

        # Acquisition of intangible fixed assets
        codes = (
            '2100XXXX',
            )
        balances[11] = self._comp_balance(cr, uid, ids, codes,context=context)
        self._setOutCell(rs, 3, 24, balances[11])

        # Loans granted to investments
        codes = (
            '2301XXXX',
            )
        balances[12] = self._comp_balance(cr, uid, ids, codes,context=context)
        self._setOutCell(rs, 3, 25, balances[12])

        # Net cash flow from investing activities
        balances[13] = sum(balances[10:13])
        self._setOutCell(rs, 3, 26, balances[13])

        # Increase/Decrease debt
        codes = (
            '322XXXXX',
            )
        balances[14] = self._comp_balance(cr, uid, ids, codes,context=context)
        self._setOutCell(rs, 3, 28, balances[14])

        # Other non-cash financing activities
        pos_codes = (
            )
        neg_codes = (
            '16503000',
            '16503900',
            '17003900',
            )
        balances[15] = self._sum_balance(cr, uid, ids, pos_codes, neg_codes, context=context)
        self._setOutCell(rs, 3, 29, balances[15])

        # Net cash flow from financing activities
        balances[16] = balances[14] + balances[15]
        self._setOutCell(rs, 3, 30, balances[16])

        # Net cash inflows (outflows)
        balances[17] = balances[9] + balances[13] + balances[16]
        self._setOutCell(rs, 3, 32, balances[17])

        # Net increase in cash and cash equivalents
        codes = (
            '2700XXXX',
            )
        balances[18] = self._comp_balance(cr, uid, ids, codes,context=context)
        self._setOutCell(rs, 3, 34, balances[18])

        # Cash and cash equivalents at beginning  and end of period
        acc_obj = self.pool.get('account.account')
        code = '2700XXXX'
        acc_ids = acc_obj.search(cr, uid, [('code','ilike',code)],context=context)
        acc_id = acc_ids and acc_ids[0] or False
        if acc_id :
            acc = acc_obj.browse(cr,uid,acc_id,context=context)
            balances[19] = acc.prev_balance
            balances[20] = acc.balance
        else :
            balances[19] = 0.0
            balances[20] = 0.0
        self._setOutCell(rs, 3, 35, balances[19])
        self._setOutCell(rs, 3, 36, balances[20])

        # Cash and cash equivalents
        balances[21] = balances[17]
        self._setOutCell(rs, 3, 38, balances[21])






        return report


    def print_report(self, cr, uid, ids, name, context=None):
        if context is None:
            context = {}
        report = self._write_report(cr,uid,ids,context=context)

        f = StringIO.StringIO()
        report.save(f)
        xls_file = base64.b64encode(f.getvalue())
        dlwizard = self.pool.get('lct_finance.file.download').create(cr, uid, {'file' : xls_file, 'file_name' : 'Cash flow statement.xls'}, context=dict(context, active_ids=ids))
        return {
            'view_mode': 'form',
            'view_id': False,
            'view_type': 'form',
            'res_model': 'lct_finance.file.download',
            'res_id': dlwizard,
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'new',
            'domain': '[]',
            'context': dict(context, active_ids=ids)
        }

