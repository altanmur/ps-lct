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
from xlrd import open_workbook,XL_CELL_BLANK,XL_CELL_TEXT,XL_CELL_NUMBER
from xlutils.copy import copy
import StringIO
import base64
from datetime import datetime
from datetime import date, timedelta
from tempfile import TemporaryFile
from xl_module import *
import zipfile
import os


class liasse_fiscale(osv.osv_memory):

    _name = "lct_finance.liasse.fiscale"

    _columns = {
        "fiscalyear_id" : fields.many2one('account.fiscalyear',  required=True, string="Fiscal Year"),
        "date_of_report" : fields.date("Date of Report", required=True),
    }

    _defaults = {
        "fiscalyear_id" : lambda self, cr, uid, context: self.__get_curr_fy(cr, uid, context=None),
        "date_of_report" : date.today().strftime('%Y-%m-%d'),
    }

    def _check_date(self, cr, uid, ids, context=None):
        fiscalyear = self.browse(cr, uid, ids[0], context=context).fiscalyear_id
        date_start = datetime.strptime(fiscalyear.date_start,'%Y-%m-%d')
        date_stop = datetime.strptime(fiscalyear.date_stop,'%Y-%m-%d')
        date_report = datetime.strptime(self.browse(cr, uid, ids[0], context=context).date_of_report,'%Y-%m-%d')
        return date_report <= date_stop and date_report >= date_start or False

    _constraints = [
        (_check_date,'The date of report must be in fiscal year.', ['date_of_report','fiscalyear_id']),
    ]


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

    def _read_accounts(self, cr, uid, sheet, rows, col, acc_rows, acc_ids, suffix=None, codes=None, context=None):
        obj = self.pool.get('account.account')
        if codes :
            for i in range(0,len(rows)):
                ids = obj.search(cr, uid, [('code','ilike',codes[i])], context=context)
                acc_id = ids and ids[0] or False
                if acc_id :
                    acc_ids.append(acc_id)
                    acc_rows.append(rows[i])
        elif suffix :
            for i in range(0,len(rows)):
                if sheet.cell(rows[i],col).ctype != XL_CELL_BLANK :
                    ids = obj.search(cr, uid, [('code','ilike',str(int(sheet.cell(rows[i],col).value)) + suffix)], context=context)
                    acc_id = ids and ids[0] or False
                    if acc_id :
                        acc_ids.append(acc_id)
                        acc_rows.append(rows[i])
    def _get_accounts_info(self, cr, uid, sheet, col, rows, suffix=None, codes=None, context=None):
        acc_obj = self.pool.get('account.account')
        acc_infos = []
        acc_ids = []
        acc_rows = []
        if codes and len(rows) == len(codes):
            self._read_accounts(cr, uid, sheet, rows, col, acc_rows, acc_ids, codes=codes, context=context)
        elif suffix :
            self._read_accounts(cr, uid, sheet, rows, col, acc_rows, acc_ids, suffix=suffix, context=context)
        else :
            return []
        for i in range(0,len(acc_rows)) :
            account = acc_obj.browse(cr, uid, acc_ids[i], context=context)
            acc_infos.append({
                'acc_id' : acc_ids[i],
                'row' : acc_rows[i],
                'move_debit' : account.debit,
                'move_credit' : account.credit,
                'prev_debit' : account.prev_debit,
                'prev_credit' : account.prev_credit,
            })

        return acc_infos

    def _write_calc(self, cr, uid, ids, template, report, context=None):
        acc_obj = self.pool.get('account.account')
        fy_obj = self.pool.get('account.fiscalyear')
        fy_code = fy_obj.browse(cr, uid, context.get('fiscalyear'), context=context).code
        prev_fy_code = fy_obj.browse(cr, uid, context.get('prev_fiscalyear'), context=context).code

        # Info complémentaires
        template_sheet = template.sheet_by_index(0)
        work_sheet = report.get_sheet(0)
        setOutCell(work_sheet, 3, 2, fy_code)
        setOutCell(work_sheet, 3, 9, fy_code)
        setOutCell(work_sheet, 4, 9, prev_fy_code)
        setOutCell(work_sheet, 2, 3, prev_fy_code)
        setOutCell(work_sheet, 2, 4, prev_fy_code)

        # Classe 1
        template_sheet = template.sheet_by_index(1)
        work_sheet = report.get_sheet(1)
        setOutCell(work_sheet, 3, 6, prev_fy_code)
        setOutCell(work_sheet, 5, 6, fy_code)
        acc_infos = []
        rows = [9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,
                29,30,31,32,33,34,36,37,38,39,40,41,42,43,68,71,72,73,74,
                92,93,94,95,96,97,98,99]
        acc_infos.extend(self._get_accounts_info(cr, uid, template_sheet, 1, rows, suffix='00000', context=context))
        rows = [45,46,47,48,50,52,54,56,58,59,60,61,62,63,64,66,76,78,80,
                82,84,86,88,90]
        acc_infos.extend(self._get_accounts_info(cr, uid, template_sheet, 1, rows, suffix='0000', context=context))
        for i in range(0,len(acc_infos)) :
            acc_info = acc_infos[i]
            prev_balance = acc_info['prev_debit']-acc_info['prev_credit']
            if  prev_balance > 0 :
                setOutCell(work_sheet, 3, acc_info['row'], prev_balance)
            elif prev_balance < 0 :
                setOutCell(work_sheet, 4, acc_info['row'], -prev_balance)
            setOutCell(work_sheet, 5, acc_info['row'], acc_info['move_debit'] if acc_info['move_debit']!=0 else "")
            setOutCell(work_sheet, 6, acc_info['row'], acc_info['move_credit'] if acc_info['move_credit']!=0 else "")
        for i in [3,4,5,6] :
            setOutCell(work_sheet, i, 35, range_sum(32,i,34,i))
            setOutCell(work_sheet, i, 44, range_sum(36,i,43,i))
            setOutCell(work_sheet, i, 49, range_sum(45,i,48,i))
            setOutCell(work_sheet, i, 51, list_sum([[50,i,+1]]))
            setOutCell(work_sheet, i, 53, list_sum([[52,i,+1]]))
            setOutCell(work_sheet, i, 55, list_sum([[53,i,+1]]))
            setOutCell(work_sheet, i, 57, list_sum([[56,i,+1]]))
            setOutCell(work_sheet, i, 65, range_sum(58,i,64,i))
            setOutCell(work_sheet, i, 67, list_sum([[66,i,+1]]))
            setOutCell(work_sheet, i, 69, list_sum([[68,i,+1]]))
            rows = [49,51,53,55,57,57,65,67,69]
            setOutCell(work_sheet, i, 70, list_sum([[j,i,+1] for j in rows]))
            setOutCell(work_sheet, i, 75, range_sum(71,i,74,i))
            setOutCell(work_sheet, i, 77, list_sum([[76,i,+1]]))
            setOutCell(work_sheet, i, 79, list_sum([[78,i,+1]]))
            setOutCell(work_sheet, i, 81, list_sum([[80,i,+1]]))
            setOutCell(work_sheet, i, 83, list_sum([[82,i,+1]]))
            setOutCell(work_sheet, i, 85, list_sum([[84,i,+1]]))
            setOutCell(work_sheet, i, 87, list_sum([[86,i,+1]]))
            setOutCell(work_sheet, i, 89, list_sum([[88,i,+1]]))
            setOutCell(work_sheet, i, 91, list_sum([[90,i,+1]]))
            setOutCell(work_sheet, i, 100, range_sum(92,i,99,i))
            rows = range(9,32)
            rows.extend([35,44,70,75,77,79,81,83,85,87,89,91,100])
            setOutCell(work_sheet, i, 101, list_sum([[j,i,+1] for j in rows]))
        for i in range(9,102):
            setOutCell(work_sheet, 7, i, list_sum([[i,3,+1],[i,5,+1],[i,4,-1],[i,6,-1]]))

        # Classe 2
        template_sheet = template.sheet_by_index(2)
        work_sheet = report.get_sheet(2)
        setOutCell(work_sheet, 3, 5, prev_fy_code)
        setOutCell(work_sheet, 4, 5, fy_code)
        acc_infos = []
        rows = [9,10,11,13,14,15,16,17,18,19,20,25,26,27,28,29,30,31,32,
                33,35,36,37,38,39,40,41,44,46,47,48,49,50,51,52,53,64,65,
                67,68,69,70,71,72,74,75,76,77,78,79,80,81]
        acc_infos.extend(self._get_accounts_info(cr, uid, template_sheet, 1, rows, suffix='00000', context=context))
        rows = [21,22,23,44,54,55,56,57,58,59,60,61,85,86,87,88,89,90,91,
                92,94,96,97,98,99,100,101,102,104,105,106,107,108,109,110,
                111,114,115,116,117,118,119,120,125,127,128,129,130,131,132,
                133,137,138,139,140,141,142,143,144,145,146,148,150,152]
        acc_infos.extend(self._get_accounts_info(cr, uid, template_sheet, 1, rows, suffix='0000', context=context))
        rows = []
        codes = [] # ?
        acc_infos.extend(self._get_accounts_info(cr, uid, template_sheet, 1, rows, codes=codes, context=context))
        for i in range(0,len(acc_infos)) :
            acc_info = acc_infos[i]
            prev_balance = acc_info['prev_debit'] - acc_info['prev_credit']
            setOutCell(work_sheet, 3, acc_info['row'], prev_balance if prev_balance!=0 else "")
            setOutCell(work_sheet, 4, acc_info['row'], acc_info['move_debit'] if acc_info['move_debit']!=0 else "")
            setOutCell(work_sheet, 10, acc_info['row'], acc_info['move_credit'] if acc_info['move_credit']!=0 else "")
        for i in [3,4,5,6,8,10] :
            setOutCell(work_sheet, i, 12, range_sum(9,i,11,i))
        for i in [3,4,5,6,7,9,10] :
            setOutCell(work_sheet, i, 24, range_sum(13,i,23,i))
            setOutCell(work_sheet, i, 34, range_sum(25,i,33,i))
            setOutCell(work_sheet, i, 45, range_sum(35,i,44,i))
            setOutCell(work_sheet, i, 62, range_sum(54,i,61,i))
            setOutCell(work_sheet, i, 63, range_sum(46,i,61,i))
            setOutCell(work_sheet, i, 66, range_sum(64,i,65,i))
            setOutCell(work_sheet, i, 73, range_sum(67,i,72,i))
            setOutCell(work_sheet, i, 82, range_sum(74,i,81,i))
            setOutCell(work_sheet, i, 83, list_sum([[j,i,+1] for j in [12,24,34,45,63,66,73,82]]))
        for i in [3,4,8,10] :
            setOutCell(work_sheet, i, 93, range_sum(85,i,92,i))
            setOutCell(work_sheet, i, 95, range_sum(94,i,94,i))
            setOutCell(work_sheet, i, 103, range_sum(96,i,102,i))
            setOutCell(work_sheet, i, 112, range_sum(104,i,111,i))
            setOutCell(work_sheet, i, 113, list_sum([[j,i,+1] for j in [93,95,103,112]]))
            setOutCell(work_sheet, i, 124, range_sum(114,i,123,i))
            setOutCell(work_sheet, i, 126, range_sum(125,i,125,i))
            setOutCell(work_sheet, i, 136, range_sum(127,i,135,i))
            setOutCell(work_sheet, i, 147, range_sum(137,i,146,i))
            setOutCell(work_sheet, i, 149, range_sum(148,i,148,i))
            setOutCell(work_sheet, i, 151, range_sum(150,i,150,i))
            setOutCell(work_sheet, i, 153, range_sum(152,i,152,i))
            setOutCell(work_sheet, i, 154, list_sum([[j,i,+1] for j in [124,126,136,147,149,151,153]]))
            setOutCell(work_sheet, i, 155, list_sum([[j,i,+1] for j in [83,113,154]]))
        for i in range(9,12):
            setOutCell(work_sheet, 11, i, list_sum([[i,3,+1],[i,4,+1],[i,5,+1],[i,6,+1],[i,8,-1],[i,10,-1]]))
        for i in range(13,83):
            setOutCell(work_sheet, 11, i, list_sum([[i,3,+1],[i,4,+1],[i,5,+1],[i,6,+1],[i,7,-1],[i,10,-1]]))
        for i in range(85,155):
            setOutCell(work_sheet, 11, i, list_sum([[i,3,+1],[i,4,+1],[i,8,-1],[i,10,-1]]))

        # Classe 3
        template_sheet = template.sheet_by_index(3)
        work_sheet = report.get_sheet(3)
        setOutCell(work_sheet, 3, 4, prev_fy_code)
        setOutCell(work_sheet, 4, 4, fy_code)
        acc_infos = []
        rows = [7,8,9,11,12,13,15,16,17,18,19,20,22,23,24,25,27,28,30,31,
                33,34,36,37,38,39,42,44,45,46,47,48,49,50]
        acc_infos.extend(self._get_accounts_info(cr, uid, template_sheet, 1, rows, suffix='00000', context=context))
        rows = [40,41,51,52,53]
        codes = [] # ?
        acc_infos.extend(self._get_accounts_info(cr, uid, template_sheet, 1, rows, codes=codes, context=context))
        for i in range(0,len(acc_infos)) :
            acc_info = acc_infos[i]
            prev_balance = acc_info['prev_debit']-acc_info['prev_credit']
            setOutCell(work_sheet, 3, acc_info['row'], prev_balance if prev_balance != 0 else '')
            setOutCell(work_sheet, 4, acc_info['row'], acc_info['move_debit'] if acc_info['move_debit']!=0 else '')
            setOutCell(work_sheet, 5, acc_info['row'], acc_info['move_credit'] if acc_info['move_credit']!=0 else '')
        for i in [3,4,5]:
            setOutCell(work_sheet, i, 10, range_sum(7,i,9,i))
            setOutCell(work_sheet, i, 14, range_sum(11,i,13,i))
            setOutCell(work_sheet, i, 21, range_sum(15,i,20,i))
            setOutCell(work_sheet, i, 26, range_sum(22,i,25,i))
            setOutCell(work_sheet, i, 29, range_sum(27,i,28,i))
            setOutCell(work_sheet, i, 32, range_sum(30,i,31,i))
            setOutCell(work_sheet, i, 35, range_sum(33,i,34,i))
            setOutCell(work_sheet, i, 43, range_sum(36,i,42,i))
            setOutCell(work_sheet, i, 54, range_sum(44,i,53,i))
            rows = [10,14,21,26,29,32,35,43,54]
            setOutCell(work_sheet, i, 55, list_sum([[j,i,+1] for j in rows]))
        for i in range(7,56):
            setOutCell(work_sheet, 6, i, list_sum([[i,3,+1],[i,4,+1],[i,5,-1]]))

        # Classe 4
        template_sheet = template.sheet_by_index(4)
        work_sheet = report.get_sheet(4)
        setOutCell(work_sheet, 3, 4, prev_fy_code)
        setOutCell(work_sheet, 4, 4, fy_code)
        acc_infos = []
        rows = [7,8,9,10,12,13,14,15,16,17,18,20,21,22,23,24,25,26,32,33,
                34,41,42,43,46,47,48,54,55,56,58,59,60,61,62,63,69,70,71,
                72,73,74,75,77,78,79,80,81,82,83,85,86,87,88,89,90,91,92,
                93,94]
        acc_infos.extend(self._get_accounts_info(cr, uid, template_sheet, 1, rows, suffix='00000', context=context))
        rows = [27,28,29,35,36,37,38,44,45,49,50,52,65,66,67,94,95]
        acc_infos.extend(self._get_accounts_info(cr, uid, template_sheet, 1, rows, suffix='0000', context=context))
        rows = []
        codes = [] # ?
        acc_infos.extend(self._get_accounts_info(cr, uid, template_sheet, 1, rows, codes=codes, context=context))
        acc_info449 = self._get_accounts_info(cr, uid, template_sheet, 1, [51], codes=['44900000',], context=context)
        acc_info4499 = self._get_accounts_info(cr, uid, template_sheet, 1, [51], codes=['44990000',], context=context)
        if len(acc_info449)>0 and len(acc_info4499)>0:
            acc_info449 = acc_info449[0]
            acc_info4499 = acc_info4499[0]
            acc_info = acc_info449.copy()
            for key in ['prev_debit','prev_credit','move_debit','move_credit']:
                acc_info[key] = acc_info449[key]-acc_info4499[key]
            acc_infos.append(acc_info)
        for i in range(0,len(acc_infos)) :
            acc_info = acc_infos[i]
            prev_balance = acc_info['prev_debit'] - acc_info['prev_credit']
            if prev_balance > 0 :
                setOutCell(work_sheet, 3, acc_info['row'], prev_balance)
            elif prev_balance < 0 :
                setOutCell(work_sheet, 4, acc_info['row'], -prev_balance)
            setOutCell(work_sheet, 5, acc_info['row'], acc_info['move_debit'] if acc_info['move_debit']!=0 else "")
            setOutCell(work_sheet, 6, acc_info['row'], acc_info['move_credit'] if acc_info['move_credit']!=0 else "")
            bal = list_sum([[acc_info['row'],3,+1],[acc_info['row'],4,-1],[acc_info['row'],5,+1],[acc_info['row'],6,-1]],text=True)
            setOutCell(work_sheet, 7, acc_info['row'], Formula('IF(' + bal + '>0;' + bal + ';0)'))
            setOutCell(work_sheet, 8, acc_info['row'], Formula('IF(' + bal + '<0;-(' + bal + ');0)'))
        for i in [3,4,5,6,7,8]:
            setOutCell(work_sheet, i, 11, range_sum(7,i,10,i))
            setOutCell(work_sheet, i, 19, range_sum(12,i,18,i))
            setOutCell(work_sheet, i, 30, range_sum(27,i,29,i))
            setOutCell(work_sheet, i, 31, range_sum(20,i,29,i))
            setOutCell(work_sheet, i, 39, range_sum(35,i,38,i))
            setOutCell(work_sheet, i, 40, range_sum(32,i,38,i))
            setOutCell(work_sheet, i, 53, range_sum(41,i,52,i))
            setOutCell(work_sheet, i, 57, range_sum(54,i,56,i))
            setOutCell(work_sheet, i, 64, range_sum(58,i,63,i))
            setOutCell(work_sheet, i, 68, range_sum(65,i,67,i))
            setOutCell(work_sheet, i, 76, range_sum(68,i,75,i))
            setOutCell(work_sheet, i, 84, range_sum(77,i,83,i))
            setOutCell(work_sheet, i, 96, range_sum(85,i,95,i))
            rows = [11,19,31,40,53,57,64,76,84,96]
            setOutCell(work_sheet, i, 97, list_sum([[j,i,+1] for j in rows]))

        # Classe 5
        template_sheet = template.sheet_by_index(5)
        work_sheet = report.get_sheet(5)
        setOutCell(work_sheet, 3, 4, prev_fy_code)
        setOutCell(work_sheet, 5, 4, fy_code)
        acc_infos = []
        rows = [7,8,9,10,11,12,13,15,16,17,18,19,20,22,23,24,25,30,31,
                32,36,38,39,40,41,42,44,45,46,51,52,53,55,56,57,58,
                60,61,62,63,64,65]
        acc_infos.extend(self._get_accounts_info(cr, uid, template_sheet, 1, rows, suffix='00000', context=context))
        rows = [27,28,34,35,48,49]
        acc_infos.extend(self._get_accounts_info(cr, uid, template_sheet, 1, rows, suffix='0000', context=context))
        for i in range(0,len(acc_infos)) :
            acc_info = acc_infos[i]
            prev_balance = acc_info['prev_debit'] - acc_info['prev_debit']
            if prev_balance > 0 :
                setOutCell(work_sheet, 3, acc_info['row'], prev_balance)
            elif prev_balance < 0 :
                setOutCell(work_sheet, 4, acc_info['row'], -prev_balance)
            balance = prev_balance - (acc_info['move_credit']+acc_info['prev_credit'])
            if balance > 0 :
                setOutCell(work_sheet, 5, acc_info['row'], balance)
            elif balance < 0 :
                setOutCell(work_sheet, 6, acc_info['row'], -balance)
        for i in [3,4,5,6]:
            setOutCell(work_sheet, i, 14, range_sum(7,i,13,i))
            setOutCell(work_sheet, i, 21, range_sum(15,i,20,i))
            setOutCell(work_sheet, i, 26, range_sum(27,i,28,i))
            setOutCell(work_sheet, i, 29, range_sum(22,i,26,i))
            setOutCell(work_sheet, i, 33, range_sum(34,i,35,i))
            setOutCell(work_sheet, i, 37, list_sum([[j,i,+1] for j in [30,31,32,33,36]]))
            setOutCell(work_sheet, i, 43, range_sum(38,i,42,i))
            setOutCell(work_sheet, i, 47, range_sum(48,i,49,i))
            setOutCell(work_sheet, i, 50, range_sum(44,i,47,i))
            setOutCell(work_sheet, i, 54, range_sum(51,i,53,i))
            setOutCell(work_sheet, i, 59, range_sum(55,i,58,i))
            setOutCell(work_sheet, i, 66, range_sum(60,i,65,i))
            rows = [14,21,29,37,43,50,54,59,66]
            setOutCell(work_sheet, i, 67, list_sum([[j,i,+1] for j in rows]))

        # Classe 6
        template_sheet = template.sheet_by_index(6)
        work_sheet = report.get_sheet(6)
        setOutCell(work_sheet, 3, 4, prev_fy_code)
        setOutCell(work_sheet, 4, 4, fy_code)
        acc_infos = []
        rows = [47,48,49,50,51]
        acc_infos.extend(self._get_accounts_info(cr, uid, template_sheet, 1, rows, suffix='00000', context=context))
        rows = [8,9,10,11,12,14,15,16,17,18,20,21,22,24,25,26,27,28,29,30,
                32,33,34,35,36,37,38,39,40,42,43,44,45,52,53,54,57,59,60,
                61,62,63,64,66,67,68,70,71,72,73,75,76,77,78,79,80,81,82,
                84,85,86,88,89,90,91,92,93,94,95,97,98,99,100,103,104,105,
                106,107,108,110,111,112,113,114,115,117,119,120,121,123,124,126,
                128,129,131,132,133,134,137,138,139,140,141,142,144,146,147,148,
                149,150,152,153,154,155,156,158,161,162,164,165,167,169,171,
                172,173,175,176,177,178,181,182,183,184,185,186,187,188,190,
                191,192,193,194,195,196,197,199,200,201,202,204,205,207,208,
                210,211,213,214,215,216,219,220,221,223,224,225,227,229,230,
                231,232,233,234,236,238,240,242,243,244,246,247,248,251,252,
                253,255,256,259,260,261,262,264,265]
        acc_infos.extend(self._get_accounts_info(cr, uid, template_sheet, 1, rows, suffix='0000', context=context))
        for i in range(0,len(acc_infos)) :
            acc_info = acc_infos[i]
            prev_balance = acc_info['prev_debit']-acc_info['prev_credit']
            setOutCell(work_sheet, 3, acc_info['row'], prev_balance if prev_balance!=0 else "")
            balance = prev_balance + acc_info['move_debit'] - acc_info['move_credit']
            setOutCell(work_sheet, 4, acc_info['row'], balance if balance!=0 else "")
        rows =  [7,13,19,23,31,41]
        setOutCell(work_sheet, 3, rows[0]-1, list_sum([[j,3,+1] for j in rows]))
        for i in range(0,len(rows)-1):
            setOutCell(work_sheet, 3, rows[i], range_sum(rows[i]+1,3,rows[i+1]-1,3))
        setOutCell(work_sheet, 3, rows[-1], range_sum(rows[-1]+1,3,45,3))
        setOutCell(work_sheet, 3, 46, range_sum(47,3,54,3))
        rows = [56,58,65,69,74,83,87,96]
        setOutCell(work_sheet, 3, rows[0]-1, list_sum([[j,3,+1] for j in rows]))
        for i in range(0,len(rows)-1):
            setOutCell(work_sheet, 3, rows[i], range_sum(rows[i]+1,3,rows[i+1]-1,3))
        setOutCell(work_sheet, 3, rows[-1], range_sum(rows[-1]+1,3,100,3))
        rows = [102,109,116,118,122,125,127,130]
        setOutCell(work_sheet, 3, rows[0]-1, list_sum([[j,3,+1] for j in rows]))
        for i in range(0,len(rows)-1):
            setOutCell(work_sheet, 3, rows[i], range_sum(rows[i]+1,3,rows[i+1]-1,3))
        setOutCell(work_sheet, 3, rows[-1], range_sum(rows[-1]+1,3,134,3))
        rows = [136,143,145,151,157]
        setOutCell(work_sheet, 3, rows[0]-1, list_sum([[j,3,+1] for j in rows]))
        for i in range(0,len(rows)-1):
            setOutCell(work_sheet, 3, rows[i], range_sum(rows[i]+1,3,rows[i+1]-1,3))
        setOutCell(work_sheet, 3, rows[-1], range_sum(rows[-1]+1,3,158,3))
        rows = [160,163,166,168,170,174]
        setOutCell(work_sheet, 3, rows[0]-1, list_sum([[j,3,+1] for j in rows]))
        for i in range(0,len(rows)-1):
            setOutCell(work_sheet, 3, rows[i], range_sum(rows[i]+1,3,rows[i+1]-1,3))
        setOutCell(work_sheet, 3, rows[-1], range_sum(rows[-1]+1,3,178,3))
        rows = [180,189,198,203,206,209,212]
        setOutCell(work_sheet, 3, rows[0]-1, list_sum([[j,3,+1] for j in rows]))
        for i in range(0,len(rows)-1):
            setOutCell(work_sheet, 3, rows[i], range_sum(rows[i]+1,3,rows[i+1]-1,3))
        setOutCell(work_sheet, 3, rows[-1], range_sum(rows[-1]+1,3,216,3))
        rows = [218,222,226,228,235,237,239,241,245]
        setOutCell(work_sheet, 3, 217, list_sum([[j,3,+1] for j in rows]))
        for i in range(0,len(rows)-1):
            setOutCell(work_sheet, 3, rows[i], range_sum(rows[i]+1,3,rows[i+1]-1,3))
        setOutCell(work_sheet, 3, 245, range_sum(246,3,248,3))
        setOutCell(work_sheet, 3, 249, list_sum([[j,3,+1] for j in [250,254]]))
        setOutCell(work_sheet, 3, 250, range_sum(251,3,253,3))
        setOutCell(work_sheet, 3, 254, range_sum(255,3,256,3))
        setOutCell(work_sheet, 3, 257, list_sum([[j,3,+1] for j in [258,263]]))
        setOutCell(work_sheet, 3, 258, range_sum(259,3,262,3))
        setOutCell(work_sheet, 3, 263, range_sum(264,3,265,3))
        setOutCell(work_sheet, 3, 267, list_sum([[j,3,+1] for j in [6,46,55,101,135,159,179,217,249,257]]))
        rows =  [7,13,19,23,31,41]
        setOutCell(work_sheet, 5, rows[0]-1, list_sum([[j,5,+1] for j in rows]))
        for i in range(0,len(rows)-1):
            setOutCell(work_sheet, 5, rows[i], range_sum(rows[i]+1,4,rows[i+1]-1,4))
        setOutCell(work_sheet, 5, rows[-1], range_sum(rows[-1]+1,4,45,4))
        setOutCell(work_sheet, 5, 46, range_sum(47,4,54,4))
        rows = [56,58,65,69,74,83,87,96]
        setOutCell(work_sheet, 5, rows[0]-1, list_sum([[j,5,+1] for j in rows]))
        for i in range(0,len(rows)-1):
            setOutCell(work_sheet, 5, rows[i], range_sum(rows[i]+1,4,rows[i+1]-1,4))
        setOutCell(work_sheet, 5, rows[-1], range_sum(rows[-1]+1,4,100,4))
        rows = [102,109,116,118,123,125,127,130]
        setOutCell(work_sheet, 5, rows[0]-1, list_sum([[j,5,+1] for j in rows]))
        for i in range(0,len(rows)-1):
            setOutCell(work_sheet, 5, rows[i], range_sum(rows[i]+1,4,rows[i+1]-1,4))
        setOutCell(work_sheet, 5, rows[-1], range_sum(rows[-1]+1,4,134,4))
        rows = [136,143,145,151,157]
        setOutCell(work_sheet, 5, rows[0]-1, list_sum([[j,5,+1] for j in rows]))
        for i in range(0,len(rows)-1):
            setOutCell(work_sheet, 5, rows[i], range_sum(rows[i]+1,4,rows[i+1]-1,4))
        setOutCell(work_sheet, 5, rows[-1], range_sum(rows[-1]+1,4,158,4))
        rows = [160,163,166,168,170,174]
        setOutCell(work_sheet, 5, rows[0]-1, list_sum([[j,5,+1] for j in rows]))
        for i in range(0,len(rows)-1):
            setOutCell(work_sheet, 5, rows[i], range_sum(rows[i]+1,4,rows[i+1]-1,4))
        setOutCell(work_sheet, 5, rows[-1], range_sum(rows[-1]+1,4,178,4))
        rows = [180,189,198,203,206,209,212]
        setOutCell(work_sheet, 5, rows[0]-1, list_sum([[j,5,+1] for j in rows]))
        for i in range(0,len(rows)-1):
            setOutCell(work_sheet, 5, rows[i], range_sum(rows[i]+1,4,rows[i+1]-1,4))
        setOutCell(work_sheet, 5, rows[-1], range_sum(rows[-1]+1,4,216,4))
        rows = [218,222,226,228,235,237,239,241,245]
        setOutCell(work_sheet, 5, 217, list_sum([[j,5,+1] for j in rows]))
        for i in range(0,len(rows)-1):
            setOutCell(work_sheet, 5, rows[i], range_sum(rows[i]+1,4,rows[i+1]-1,4))
        setOutCell(work_sheet, 5, 245, range_sum(246,4,248,4))
        setOutCell(work_sheet, 5, 249, list_sum([[j,5,+1] for j in [250,254]]))
        setOutCell(work_sheet, 5, 250, range_sum(251,4,253,4))
        setOutCell(work_sheet, 5, 254, range_sum(255,4,256,4))
        setOutCell(work_sheet, 5, 257, list_sum([[j,5,+1] for j in [258,263]]))
        setOutCell(work_sheet, 5, 258, range_sum(259,4,262,4))
        setOutCell(work_sheet, 5, 263, range_sum(264,4,265,4))
        setOutCell(work_sheet, 5, 267, list_sum([[j,5,+1] for j in [6,46,55,101,135,159,179,217,249,257]]))

        # Classe 7
        template_sheet = template.sheet_by_index(7)
        work_sheet = report.get_sheet(7)
        setOutCell(work_sheet, 3, 4, prev_fy_code)
        setOutCell(work_sheet, 4, 4, fy_code)
        acc_infos = []
        rows = [47,48,49,55,56,57]
        acc_infos.extend(self._get_accounts_info(cr, uid, template_sheet, 1, rows, suffix='00000', context=context))
        rows = [8,9,10,11,13,14,15,16,18,19,20,21,23,24,25,26,28,29,30,31,
                33,34,35,36,38,39,40,41,42,43,44,45,47,48,49,51,52,53,55,
                56,57,60,61,63,64,66,68,69,72,73,75,77,79,80,82,83,84,85,
                88,90,92,94,96,98,100,101,102,104,105,106,109,111,114,
                115,116,117,119,120,122]
        acc_infos.extend(self._get_accounts_info(cr, uid, template_sheet, 1, rows, suffix='0000', context=context))
        for i in range(0,len(acc_infos)) :
            acc_info = acc_infos[i]
            prev_balance = acc_info['prev_debit']-acc_info['prev_credit']
            setOutCell(work_sheet, 3, acc_info['row'], prev_balance if prev_balance!=0 else "")
            balance = prev_balance + acc_info['move_debit'] - acc_info['move_credit']
            setOutCell(work_sheet, 4, acc_info['row'], balance if balance!=0 else "")
        setOutCell(work_sheet, 3, 6, list_sum([[j,3,+1] for j in [7,12,17,22,27,32,37]]))
        setOutCell(work_sheet, 3, 7, range_sum(8,3,11,3))
        setOutCell(work_sheet, 3, 12, range_sum(13,3,16,3))
        setOutCell(work_sheet, 3, 17, range_sum(18,3,21,3))
        setOutCell(work_sheet, 3, 22, range_sum(23,3,26,3))
        setOutCell(work_sheet, 3, 27, range_sum(28,3,31,3))
        setOutCell(work_sheet, 3, 32, range_sum(33,3,36,3))
        setOutCell(work_sheet, 3, 37, range_sum(38,3,45,3))
        setOutCell(work_sheet, 3, 46, range_sum(47,3,50,3))
        setOutCell(work_sheet, 3, 50, range_sum(51,3,53,3))
        setOutCell(work_sheet, 3, 54, range_sum(55,3,57,3))
        setOutCell(work_sheet, 3, 58, list_sum([[j,3,+1] for j in [59,62,65,67]]))
        setOutCell(work_sheet, 3, 59, range_sum(60,3,61,3))
        setOutCell(work_sheet, 3, 62, range_sum(63,3,64,3))
        setOutCell(work_sheet, 3, 65, range_sum(66,3,66,3))
        setOutCell(work_sheet, 3, 67, range_sum(68,3,69,3))
        setOutCell(work_sheet, 3, 70, list_sum([[j,3,+1] for j in [71,74,76,78,81]]))
        setOutCell(work_sheet, 3, 71, range_sum(72,3,73,3))
        setOutCell(work_sheet, 3, 74, range_sum(75,3,75,3))
        setOutCell(work_sheet, 3, 76, range_sum(77,3,77,3))
        setOutCell(work_sheet, 3, 78, range_sum(79,3,80,3))
        setOutCell(work_sheet, 3, 81, range_sum(82,3,85,3))
        setOutCell(work_sheet, 3, 86, list_sum([[j,3,+1] for j in [87,89,91,93,95,97,99,103]]))
        setOutCell(work_sheet, 3, 87, range_sum(88,3,88,3))
        setOutCell(work_sheet, 3, 89, range_sum(90,3,90,3))
        setOutCell(work_sheet, 3, 91, range_sum(92,3,92,3))
        setOutCell(work_sheet, 3, 93, range_sum(94,3,94,3))
        setOutCell(work_sheet, 3, 95, range_sum(96,3,96,3))
        setOutCell(work_sheet, 3, 97, range_sum(98,3,98,3))
        setOutCell(work_sheet, 3, 99, range_sum(100,3,102,3))
        setOutCell(work_sheet, 3, 103, range_sum(104,3,106,3))
        setOutCell(work_sheet, 3, 107, list_sum([[j,3,+1] for j in [108,110]]))
        setOutCell(work_sheet, 3, 108, range_sum(109,3,109,3))
        setOutCell(work_sheet, 3, 110, range_sum(111,3,111,3))
        setOutCell(work_sheet, 3, 112, list_sum([[j,3,+1] for j in [113,118,121]]))
        setOutCell(work_sheet, 3, 113, range_sum(114,3,117,3))
        setOutCell(work_sheet, 3, 118, range_sum(119,3,120,3))
        setOutCell(work_sheet, 3, 121, range_sum(122,3,122,3))
        setOutCell(work_sheet, 3, 124, list_sum([[j,3,+1] for j in [6,46,54,58,70,86,107,112]]))
        setOutCell(work_sheet, 5, 6, list_sum([[j,5,+1] for j in [7,12,17,22,27,32,37]]))
        setOutCell(work_sheet, 5, 7, range_sum(8,4,11,4))
        setOutCell(work_sheet, 5, 12, range_sum(13,4,16,4))
        setOutCell(work_sheet, 5, 17, range_sum(18,4,21,4))
        setOutCell(work_sheet, 5, 22, range_sum(23,4,26,4))
        setOutCell(work_sheet, 5, 27, range_sum(28,4,31,4))
        setOutCell(work_sheet, 5, 32, range_sum(33,4,36,4))
        setOutCell(work_sheet, 5, 37, range_sum(38,4,45,4))
        setOutCell(work_sheet, 5, 46, range_sum(47,3,50,3))
        setOutCell(work_sheet, 5, 50, range_sum(51,4,53,4))
        setOutCell(work_sheet, 5, 54, range_sum(555,4,57,4))
        setOutCell(work_sheet, 5, 58, list_sum([[j,5,+1] for j in [59,62,65,67]]))
        setOutCell(work_sheet, 5, 59, range_sum(60,4,61,4))
        setOutCell(work_sheet, 5, 62, range_sum(63,4,64,4))
        setOutCell(work_sheet, 5, 65, range_sum(66,4,66,4))
        setOutCell(work_sheet, 5, 67, range_sum(68,4,69,4))
        setOutCell(work_sheet, 5, 70, list_sum([[j,5,+1] for j in [71,74,76,78,81]]))
        setOutCell(work_sheet, 5, 71, range_sum(72,4,73,4))
        setOutCell(work_sheet, 5, 74, range_sum(75,4,75,4))
        setOutCell(work_sheet, 5, 76, range_sum(77,4,77,4))
        setOutCell(work_sheet, 5, 78, range_sum(79,4,80,4))
        setOutCell(work_sheet, 5, 81, range_sum(82,4,85,4))
        setOutCell(work_sheet, 5, 86, list_sum([[j,5,+1] for j in [87,89,91,93,95,97,99,103]]))
        setOutCell(work_sheet, 5, 87, range_sum(88,4,88,4))
        setOutCell(work_sheet, 5, 89, range_sum(90,4,90,4))
        setOutCell(work_sheet, 5, 91, range_sum(92,4,92,4))
        setOutCell(work_sheet, 5, 93, range_sum(94,4,94,4))
        setOutCell(work_sheet, 5, 95, range_sum(96,4,96,4))
        setOutCell(work_sheet, 5, 97, range_sum(98,4,98,4))
        setOutCell(work_sheet, 5, 99, range_sum(100,4,102,4))
        setOutCell(work_sheet, 5, 103, range_sum(104,4,106,4))
        setOutCell(work_sheet, 5, 107, list_sum([[j,5,+1] for j in [108,110]]))
        setOutCell(work_sheet, 5, 108, range_sum(109,4,109,4))
        setOutCell(work_sheet, 5, 110, range_sum(111,4,111,4))
        setOutCell(work_sheet, 5, 112, list_sum([[j,5,+1] for j in [113,118,121]]))
        setOutCell(work_sheet, 5, 113, range_sum(114,4,117,4))
        setOutCell(work_sheet, 5, 118, range_sum(119,4,120,4))
        setOutCell(work_sheet, 5, 121, range_sum(122,4,122,4))
        setOutCell(work_sheet, 5, 124, list_sum([[j,5,+1] for j in [6,46,54,58,70,86,107,112]]))

        # Classe 8
        template_sheet = template.sheet_by_index(8)
        work_sheet = report.get_sheet(8)
        setOutCell(work_sheet, 3, 4, prev_fy_code)
        setOutCell(work_sheet, 4, 4, fy_code)
        acc_infos = []
        rows = [7,8,9,11,12,13,15,16,17,18,25,26,27,28,35,36,37,38,39,41,
                42,43,44,45,46,47,48,49,50,52,53,54,55,57,58,59]
        acc_infos.extend(self._get_accounts_info(cr, uid, template_sheet, 1, rows, suffix='00000', context=context))
        rows = [20,21,22,23,30,31,32,33,61,62]
        acc_infos.extend(self._get_accounts_info(cr, uid, template_sheet, 1, rows, suffix='0000', context=context))
        for i in range(0,len(acc_infos)) :
            acc_info = acc_infos[i]
            prev_balance = acc_info['prev_debit']-acc_info['prev_credit']
            setOutCell(work_sheet, 3, acc_info['row'], prev_balance if prev_balance!=0 else "")
            balance = prev_balance + acc_info['move_debit'] - acc_info['move_credit']
            setOutCell(work_sheet, 4, acc_info['row'], balance if balance!=0 else "")
        setOutCell(work_sheet, 3, 6, range_sum(7,3,9,3))
        setOutCell(work_sheet, 3, 10, range_sum(11,3,13,3))
        setOutCell(work_sheet, 3, 14, range_sum(15,3,19,3))
        setOutCell(work_sheet, 3, 19, range_sum(20,3,23,3))
        setOutCell(work_sheet, 3, 24, range_sum(25,3,29,3))
        setOutCell(work_sheet, 3, 29, range_sum(30,3,33,3))
        setOutCell(work_sheet, 3, 34, range_sum(35,3,39,3))
        setOutCell(work_sheet, 3, 40, range_sum(41,3,46,3))
        setOutCell(work_sheet, 3, 47, range_sum(48,3,50,3))
        setOutCell(work_sheet, 3, 51, range_sum(52,3,55,3))
        setOutCell(work_sheet, 3, 56, range_sum(57,3,60,3))
        setOutCell(work_sheet, 3, 60, range_sum(61,3,62,3))
        setOutCell(work_sheet, 3, 64, list_sum([[j,3,+1] for j in [6,10,14,24,34,40,47,51,56]]))
        setOutCell(work_sheet, 5, 6, range_sum(7,4,9,4))
        setOutCell(work_sheet, 5, 10, range_sum(11,4,13,4))
        setOutCell(work_sheet, 5, 14, range_sum(15,4,19,4))
        setOutCell(work_sheet, 4, 19, range_sum(20,4,23,4))
        setOutCell(work_sheet, 5, 24, range_sum(25,4,29,4))
        setOutCell(work_sheet, 4, 29, range_sum(30,4,33,4))
        setOutCell(work_sheet, 5, 34, range_sum(35,4,39,4))
        setOutCell(work_sheet, 5, 40, range_sum(41,4,46,4))
        setOutCell(work_sheet, 5, 47, range_sum(48,4,50,4))
        setOutCell(work_sheet, 5, 51, range_sum(52,4,55,4))
        setOutCell(work_sheet, 5, 56, list_sum([[57,4,1],[58,4,+1],[59,4,+1],[60,5,+1]]))
        setOutCell(work_sheet, 5, 60, range_sum(61,4,62,4))
        setOutCell(work_sheet, 5, 64, list_sum([[j,5,+1] for j in [6,10,14,24,34,40,47,51,56]]))

    def print_report(self, cr, uid, ids, name, context=None):
        if context is None:
            context = {}
        fy_obj = self.pool.get('account.fiscalyear')
        fiscalyear = self.browse(cr, uid, ids, context=context)[0].fiscalyear_id
        context['fiscalyear']= fiscalyear and fiscalyear.id
        date = fy_obj.browse(cr, uid, context.get('fiscalyear'), context=context).date_start
        fys = fy_obj.browse(cr, uid, fy_obj.search(cr, uid, [('date_stop','<=',date)], context=context), context=context)
        if fys and len(fys)>0:
            prev_fy = fys[0]
            for fy in fys[1:] :
                if fy.date_stop > prev_fy.date_stop:
                    prev_fy = fy
            context['prev_fiscalyear'] = prev_fy.id
        context['date_from'] = '1000-01-01'
        context['date_to'] = self.browse(cr, uid, ids[0], context=context).date_of_report
        module_path = __file__.split('wizard')[0]
        xls_path = os.path.join(module_path, 'data', 'Donnees liasse fiscale.xls')
        template = open_workbook(xls_path, formatting_info=True)
        workbook = copy(template)
        self._write_calc(cr,uid,ids,template,workbook,context=context)
        data_xls_sIO = StringIO.StringIO()
        workbook.save(data_xls_sIO)
        zip_sIO = StringIO.StringIO()
        zip_file = zipfile.ZipFile(zip_sIO, 'w')
        zip_file.writestr('Liasse fiscale/Donnees liasse fiscale.xls',data_xls_sIO.getvalue())
        xls_path = os.path.join(module_path, 'data', 'Calculs liasse fiscale.xls')
        zip_file.write(xls_path, arcname='Liasse fiscale/Calculs liasse fiscale.xls')
        xls_path = os.path.join(module_path, 'data', 'Liasse fiscale.xls')
        zip_file.write(xls_path, arcname='Liasse fiscale/Liasse fiscale.xls')
        zip_file.close()
        zip_b64 = base64.b64encode(zip_sIO.getvalue())
        # data_xls_b64 = base64.b64encode(data_xls_sIO.getvalue())
        dlwizard = self.pool.get('lct_finance.file.download').create(cr, uid, {'file' : zip_b64, 'file_name' : 'Liasse fiscale.zip'}, context=dict(context, active_ids=ids))
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
