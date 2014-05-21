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
from xl_tools import *
import timeit

class liasse_fiscale(osv.osv_memory):

    _name = "lct_finance.liasse.fiscale"

    _columns = {
        "fiscalyear_id" : fields.many2one('account.fiscalyear',  required=True, string="Fiscal Year"),
    }

    _defaults = {
        "fiscalyear_id" : lambda self, cr, uid, context: self.__get_curr_fy(cr, uid, context=None)
    }

    def __get_curr_fy(self, cr, uid, context=None):
        fy_obj = self.pool.get('account.fiscalyear')
        domain = [('date_start','<=',fields.date.today()),('date_stop','>=',fields.date.today())]
        fy_ids = fy_obj.search(cr, uid, domain, context=context)
        return fy_ids and fy_ids[0] or None

    def _get_children_account_ids(self, cr, uid, account_id, context=None):
        children_ids = [account_id]
        ids_to_check = [account_id]
        obj = self.pool.get('account.account')
        while len(ids_to_check) > 0 :
            ids_to_check_next = obj.search(cr, uid, [('parent_id','in',ids_to_check)], context=context) or []
            children_ids.extend(ids_to_check_next)
            ids_to_check = ids_to_check_next
        return children_ids

    def _read_accounts(self, cr, uid, sheet, rows, col, acc_rows, acc_ids, suffix='', context=None):
        obj = self.pool.get('account.account')
        for i in range(0,len(rows)):
            if sheet.cell(rows[i],col).ctype != XL_CELL_BLANK :
                ids = obj.search(cr, uid, [('code','ilike',str(int(sheet.cell(rows[i],col).value)) + suffix)], context=context)
                acc_id = ids and ids[0] or False
                if acc_id :
                    acc_ids.append(acc_id)
                    acc_rows.append(rows[i])

    def _get_accounts_info(self, cr, uid, sheet, col, rows, suffix='', context=None):
        acc_obj = self.pool.get('account.account')
        acc_info = {
            'rows' : [],
            'ids' : [],
            'move_debit' : [],
            'move_credit' : [],
            'prev_debit' : [],
            'prev_credit' : [],
        }
        self._read_accounts(cr, uid, sheet, rows, col, acc_info['rows'], acc_info['ids'], suffix=suffix, context=context)
        period_ids = self.pool.get('account.period').search(cr, uid, [('fiscalyear_id','=',context.get('fiscalyear'))], context=context)
        ml_obj = self.pool.get('account.move.line')
        for i in range(0,len(acc_info['rows'])):
            account = acc_obj.browse(cr, uid, acc_info['ids'][i], context=context)
            acc_info['prev_debit'].append(account.prev_debit)
            acc_info['prev_credit'].append(account.prev_credit)
            acc_and_children_ids = self._get_children_account_ids(cr, uid, acc_info['ids'][i], context=context)
            domain = [('period_id','in',period_ids),('account_id','in',acc_and_children_ids)]
            ml_obj.browse(cr, uid, ml_obj.search(cr, uid, domain, context=context))
            move_lines = ml_obj.browse(cr, uid, ml_obj.search(cr, uid, domain, context=context))
            acc_info['move_debit'].append(0)
            acc_info['move_credit'].append(0)
            for ml in move_lines :
                acc_info['move_debit'][i] += ml.debit
                acc_info['move_credit'][i] += ml.credit
        return acc_info

    def _write_calc(self, cr, uid, ids, context=None):
        module_path = __file__.split('wizard')[0]
        template = open_workbook(module_path + 'data/calc_liasse.xls',formatting_info=True)
        report = copy(template)
        acc_obj = self.pool.get('account.account')

        # Classe 1
        template_sheet = template.sheet_by_index(2)
        work_sheet = report.get_sheet(2)

        ## Credit
        rows = [9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,
                29,30,31,32,33,34,36,37,38,39,40,41,42,43,68,71,72,73,74,
                92,93,94,95,96,97,98,99]
        acc_info = self._get_accounts_info(cr, uid, template_sheet, 1, rows, '00000', context=context)

        for i in range(0,len(acc_info['rows'])) :
            account =  acc_obj.browse(cr, uid, acc_info['ids'][i], context=context)
            if acc_info['prev_credit'][i] != 0.0 or acc_info['prev_debit'][i] != 0 :
                if acc_info['prev_credit'][i] != 0.0 :
                    setOutCell(work_sheet, 4, acc_rows[i], acc_info['prev_credit'][i])
                else :
                    setOutCell(rs, 3, acc_info['rows'][i], acc_info['prev_debit'][i])
            setOutCell(work_sheet, 5, acc_info['rows'][i], acc_info['move_credit'][i])
            setOutCell(work_sheet, 6, acc_info['rows'][i], acc_info['move_debit'][i])

        #~ accounts = []
        #~ acc_rows = []
        #~ self._read_accounts(cr, uid, ts, rows, 1, acc_rows, accounts, context=context)
        #~ move_credits = []
        #~ move_debits = []
        #~ self._get_move(cr, uid, accounts, move_credits, move_debits, context=context)

        return report

    def print_report(self, cr, uid, ids, name, context=None):
        if context is None:
            context = {}
        fiscalyear = self.browse(cr, uid, ids, context=context)[0].fiscalyear_id
        context['fiscalyear']= fiscalyear and fiscalyear.id
        report = self._write_calc(cr,uid,ids,context=context)

        f = StringIO.StringIO()
        report.save(f)
        xls_file = base64.b64encode(f.getvalue())
        dlwizard = self.pool.get('cash.flow.download').create(cr, uid, {'xls_report' : xls_file}, context=dict(context, active_ids=ids))
        return {
            'view_mode': 'form',
            'view_id': False,
            'view_type': 'form',
            'res_model': 'cash.flow.download',
            'res_id': dlwizard,
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'new',
            'domain': '[]',
            'context': dict(context, active_ids=ids)
        }

