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


class depreciation_table(osv.osv_memory):

    _inherit = "account.common.account.report"
    _name = "lct_finance.depreciation.table.report"

    def _write_report(self, cr, uid, ids, context=None):

        report = Workbook()
        sheet = report.add_sheet('Sheet 1')
        today_s = date.today().strftime("%d-%m-%Y")

        sheet.write_merge(1,1,1,10,'LCT SA')
        sheet.write_merge(2,2,2,27,'TABLEAU DES IMMOBILISATIONS AU' + today_s)
        sheet.write(5,1,"Designation de l'immobilisation")
        sheet.write(5,2,"Date d'aquisition")
        sheet.write_merge(5,5,3,7,'Valeur brute')
        sheet.write(5,10,"Taux d'amortissement")
        sheet.write_merge(5,5,9,15,'Amortissements')
        sheet.write(5,27,"Valeur comptable nette au " + today_s)



        return report


    def print_report(self, cr, uid, ids, name, context=None):
        if context is None:
            context = {}
        report = self._write_report(cr,uid,ids,context=context)

        f = StringIO.StringIO()
        report.save(f)
        xls_file = base64.b64encode(f.getvalue())
        dlwizard = self.pool.get('depreciation.table.download').create(cr, uid, {'xls_report' : xls_file}, context=dict(context, active_ids=ids))
        return {
            'view_mode': 'form',
            'view_id': False,
            'view_type': 'form',
            'res_model': 'depreciation.table.download',
            'res_id': dlwizard,
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'new',
            'domain': '[]',
            'context': dict(context, active_ids=ids)
        }

