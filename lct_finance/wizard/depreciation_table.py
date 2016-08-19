
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
from xlwt import Workbook,easyxf,Formula
from xlrd import open_workbook,XL_CELL_BLANK
from xlutils.copy import copy
import StringIO
import base64
from datetime import date, timedelta, datetime
from tempfile import TemporaryFile
import calendar
import copy
import xl_module

class depreciation_table(osv.osv_memory):

    _name = "lct_finance.depreciation.table.report"
    _columns = {
        "report_date" : fields.date(string='Date of Report',required=True),
    }
    _defaults = {
        "report_date" : date.today().strftime('%Y-%m-%d'),
    }

    def _write_report(self, cr, uid, ids, context=None):
        D_FORMAT = "%d/%m/%Y"
        HEIGHT = 256
        WIDTH = 1000
        report_date = self.browse(cr, uid, ids[0], context).report_date
        REPORT_DATE = datetime.strptime(report_date, "%Y-%m-%d")
        REPORT_DATE_S = REPORT_DATE.strftime(D_FORMAT)
        JAN1_DATE_S = REPORT_DATE.strftime("01/01/%Y")
        JAN1_DATE = datetime.strptime(JAN1_DATE_S, D_FORMAT)

        def _next_line(crd, spacing=1):
            crd["row"] += spacing
            crd["col"] = 0

        def _write(sheet, crd, label, format_=None, height=0, width=0):
            if height:
                sheet.row(crd["row"]).height = height
            if width:
                sheet.col(crd["col"]).width = width
            if format_:
                sheet.write(crd["row"], crd["col"], label, format_)
            else:
                sheet.write(crd["row"], crd["col"], label)
            crd["col"] += 1

        def _write_merge(sheet, crd, size, label, format_=None, spacing=0, height=0):
            if height:
                sheet.row(crd["row"]).height = height
            if format_:
                sheet.write_merge(crd["row"], crd["row"], crd["col"], crd["col"] + size - 1, label, format_)
            else:
                sheet.write_merge(crd["row"], crd["row"], crd["col"], crd["col"] + size - 1, label)
            if spacing:
                _next_line(crd, spacing=spacing)
            else:
                crd["col"] += size

        def _write_header(sheet, crd):
            _write_merge(sheet, crd, 10, "LCT SA", xl_module.title1, spacing=1, height=HEIGHT)
            _write_merge(sheet, crd, 10, "TABLEAU DES IMMOBILISATIONS AU %s" %REPORT_DATE_S, xl_module.title2, spacing=3, height=5*HEIGHT)

            _write(sheet, crd, u"Désignation de l'immobilisation", xl_module.label_center, width=10*WIDTH, height=4*HEIGHT)
            _write(sheet, crd, u"N° compte", xl_module.label_center, width=3*WIDTH)
            _write(sheet, crd, u"Date d'aquistion", xl_module.label_center, width=6*WIDTH)
            _write_merge(sheet, crd, 4, u"Valeur brute", xl_module.label_center)
            _write(sheet, crd, u"Taux d'amort.", xl_module.label_center, width=3*WIDTH)
            _write(sheet, crd, u"", xl_module.label_center, width=6*WIDTH)
            _write_merge(sheet, crd, REPORT_DATE.month, u"Amortissements", xl_module.label_center)
            _write(sheet, crd, u"Valeur comptable nette au %s" %REPORT_DATE_S, xl_module.label_center, width=6*WIDTH)

            _next_line(crd)
            _write_merge(sheet, crd, 3, u"", height=3*HEIGHT)
            _write(sheet, crd, u"VALEURS AU %s" %JAN1_DATE_S, xl_module.label_center, width=6*WIDTH)
            _write(sheet, crd, u"ACQUISITIONS", xl_module.label_center, width=6*WIDTH)
            _write(sheet, crd, u"SORTIES OU TRANSFERS", xl_module.label_center, width=6*WIDTH)
            _write(sheet, crd, u"VALEURS AU %s" %REPORT_DATE_S, xl_module.label_center, width=6*WIDTH)
            _write(sheet, crd, u"")
            _write(sheet, crd, u"Amortisements cumulés au 31/12/%s" %(REPORT_DATE.year - 1), xl_module.label_center, width=6*WIDTH)
            for m in xrange(REPORT_DATE.month):
                _write(sheet, crd, date(1900, m+1, 1).strftime("%B"), xl_module.label_month, width=3*WIDTH)

        def _write_categ_line(sheet, crd, categ):
            _next_line(crd)
            _write(sheet, crd, categ.name, xl_module.as_name)

        def _write_asset_line(sheet, crd, categ, asset, asset_data):
            _next_line(crd)
            _write(sheet, crd, asset.name)
            _write(sheet, crd, categ.account_asset_id.code if categ.account_asset_id else "")
            _write(sheet, crd, asset.purchase_date_2)
            for i in xrange(4):
                _write(sheet, crd, asset_data[i])
            _write(sheet, crd, "%.2f%%" %(1200./asset.method_number) if asset.method_number else "")
            for i in xrange(REPORT_DATE.month + 1):
                _write(sheet, crd, asset_data[~0][i])
            _write(sheet, crd, asset_data[3])

        def _write_total(sheet, crd, name, lines, height=HEIGHT):
            _next_line(crd)
            _write(sheet, crd, "Total %s" %name, xl_module.total_center, height=height)
            _write(sheet, crd, "", xl_module.total_center)
            _write(sheet, crd, "", xl_module.total_center)
            for i in xrange(4):
                _write(sheet, crd, sum([l[i] for l in lines]), xl_module.total_center)
            _write(sheet, crd, "", xl_module.total_center)
            for i in xrange(REPORT_DATE.month + 1):
                _write(sheet, crd, sum(l[~0][i] for l in lines), xl_module.total_center)
            _write(sheet, crd, sum([l[3] for l in lines]), xl_module.total_center)
            _next_line(crd)

        def _get_data():
            # {category: {asset: [value_1JAN, aquititions, transfers, value_REPORT_DATE, [depJAN, depFEB, ...]]}}
            res = {}
            move_line_obj = self.pool.get("account.move.line")
            asset_obj = self.pool.get("account.asset.asset")
            # for asset_id in asset_obj.search(cr, uid, [("state", "=", "open")], context=context):
            print "Precessing data..."
            for asset_id in asset_obj.search(cr, uid, [], context=context):
                asset = asset_obj.browse(cr, uid, asset_id, context=context)
                print "Asset [%s]: %s" %(asset_id, asset.name)
                category = asset.category_id
                if not res.get(category):
                    res.update({category: {}})
                deps = {k: 0 for k in xrange(13)}
                dep_report_date, dep_jan1 = 0, 0
                for dep in asset.depreciation_line_ids:
                    if not dep.move_check:
                        continue
                    dep_dt = datetime.strptime(dep.depreciation_date, "%Y-%m-%d")
                    if dep_dt <= self.today and dep_dt >= REPORT_DATE:
                        dep_report_date += dep.amount
                    if dep_dt < REPORT_DATE and dep_dt >= JAN1_DATE:
                        dep_jan1 += dep.amount
                    if dep_dt.year < REPORT_DATE.year:
                        deps[0] += dep.amount
                        continue
                    if dep_dt.year > REPORT_DATE.year:
                        continue
                    deps[dep_dt.month] += dep.amount

                move_report_date_ids = move_line_obj.search(cr, uid, [("to_update_asset_id", "=", asset_id), ("date", "<=", self.today), ("date", ">=", REPORT_DATE)], context=context)
                move_report_date = move_line_obj.browse(cr, uid, move_report_date_ids, context=context)
                aquitition_report_date = sum([mv.debit - mv.credit for mv in move_report_date if mv.get_asset_move_type() == "aquisition"])
                transfer_report_date = sum([mv.debit - mv.credit for mv in move_report_date if mv.get_asset_move_type() in ("transfer", "scrap")])

                move_jan1_ids = move_line_obj.search(cr, uid, [("to_update_asset_id", "=", asset_id), ("date", "<", REPORT_DATE), ("date", ">=", JAN1_DATE)], context=context)
                move_jan1 = move_line_obj.browse(cr, uid, move_jan1_ids, context=context)
                aquitition_jan1 = sum([mv.debit - mv.credit for mv in move_jan1 if mv.get_asset_move_type() == "aquisition"])
                transfer_jan1 = sum([mv.debit - mv.credit for mv in move_jan1 if mv.get_asset_move_type() in ("transfer", "scrap")])

                value_report_date = asset.value_residual + dep_report_date + aquitition_report_date + transfer_report_date
                value_jan1 = value_report_date + dep_jan1 + aquitition_jan1 + transfer_jan1

                res[category].update({asset: [value_jan1, aquitition_jan1, transfer_jan1, value_report_date, deps]})
            return res

        sheet = self.sheet
        crd = {'row': 0, 'col': 0}
        _write_header(sheet, crd)
        data = _get_data()
        for categ, categ_data in data.items():
            _write_categ_line(sheet, crd, categ)
            for asset, asset_data in categ_data.items():
                _write_asset_line(sheet, crd, categ, asset, asset_data)
            _write_total(sheet, crd, categ.name, categ_data.values(), height=3*HEIGHT)
        _write_total(sheet, crd, "Immobilisations", [asset_data for categ_data in data.values() for asset_data in categ_data.values()], height=4*HEIGHT)

    def print_report(self, cr, uid, ids, name, context=None):
        if context is None:
            context = {}
        context['date_to'] = self.browse(cr,uid,ids,context=context)[0].report_date
        context['date_from'] = '1000-01-01'
        self.today = datetime.strptime(context['date_to'],'%Y-%m-%d')
        report = Workbook()
        self.sheet = report.add_sheet('Sheet 1')
        self._write_report(cr,uid,ids,context=context)


        f = StringIO.StringIO()
        report.save(f)
        xls_file = base64.b64encode(f.getvalue())
        dlwizard = self.pool.get('lct_finance.file.download').create(cr, uid, {'file' : xls_file, 'file_name' : 'Depreciation table.xls'}, context=dict(context, active_ids=ids))
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


