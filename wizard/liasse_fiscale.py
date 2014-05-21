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

class liasse_fiscale(osv.osv_memory):

    _name = "lct_finance.liasse.fiscale"

    _columns = {
        "fiscalyear_id" : fields.many2one('account.fiscalyear',  required=True, string="Fiscal Year"),
    }

    _defaults = {
        "fiscalyear_id" : lambda self, cr, uid, context: self._get_curr_fy(cr, uid, context=None)
    }

    def _get_curr_fy(self, cr, uid, context=None):
        fy_obj = self.pool.get('account.fiscalyear')
        domain = [('date_start','<=',fields.date.today()),('date_stop','>=',fields.date.today())]
        fy_ids = fy_obj.search(cr, uid, domain, context=context)
        return None
        return fy_ids and fy_ids[0] or None


    def _read_accounts(self, cr, uid, sheet, rows, col, acc_rows, accounts, context=None):
        acc_obj = self.pool.get('account.account')
        acc_ids = []
        for i in range(0,len(rows)):
            if sheet.cell(rows[i],1).ctype != XL_CELL_BLANK :
                shortcode = str(int(sheet.cell(rows[i],1).value))
                code =  shortcode+ (8-len(shortcode))*'0'
                domain = [('code','ilike',code)]
                id_list = acc_obj.search(cr, uid, domain, context=context)
                if not id_list :
                    continue
                acc_id = id_list[0]
                if acc_id :
                    acc_ids.append(acc_id)
                    acc_rows.append(rows[i])
        accounts.extend(acc_obj.browse(cr, uid, acc_ids, context=context))


    def _write_calc(self, cr, uid, ids, context=None):
        module_path = __file__.split('wizard')[0]
        template = open_workbook(module_path + 'data/calc_liasse.xls',formatting_info=True)
        self.report = copy(template)
        report = self.report

        fy_obj = self.pool.get('account.fiscalyear')

        # Classe 1
        ts = template.sheet_by_index(2)
        rs = report.get_sheet(2)

        ## Debit
        rows = [15,21]
        accounts = []
        acc_rows = []
        self._read_accounts(cr, uid, ts, rows, 1, acc_rows, accounts, context=context)
        for i in range(0,len(acc_rows)) :
            setOutCell(rs,3,acc_rows[i],accounts[i].prev_debit)
        ctx = dict(context)
        ctx['date_start'] = context['fiscalyear']

        ## Credit
        rows = []
        rows.extend(range(9,15))
        rows.extend(range(16,21))
        rows.extend(range(22,35))
        rows.extend(range(36,44))
        rows.extend(range(45,49))
        rows.append(50)
        rows.append(52)
        rows.append(54)
        rows.append(56)
        rows.extend(range(58,65))
        rows.append(66)
        rows.append(68)
        rows.extend(range(71,75))
        rows.append(68)
        rows.append(76)
        rows.append(78)
        rows.append(80)
        rows.append(82)
        rows.append(84)
        rows.append(86)
        rows.append(88)
        rows.append(90)
        rows.extend(range(92,100))
        accounts = []
        acc_rows = []
        self._read_accounts(cr, uid, ts, rows, 1, acc_rows, accounts, context=context)
        for i in range(0,len(acc_rows)) :
            setOutCell(rs,4,acc_rows[i],accounts[i].prev_credit)

        #






    def print_report(self, cr, uid, ids, name, context=None):
        if context is None:
            context = {}
        context['fiscalyear'] = self.browse(cr, uid, ids, context=context)[0].fiscalyear_id
        if not context['fiscalyear'] :
            raise osv.except_osv('UserError','Please select a fiscal year')
        self._write_calc(cr,uid,ids,context=context)

        f = StringIO.StringIO()
        self.report.save(f)
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

