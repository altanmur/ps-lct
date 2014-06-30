
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
from datetime import datetime
from datetime import date, timedelta
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

    def _get_account(self, cr, uid, ids, code, context=None):
        acc_obj = self.pool.get('account.account')
        acc_ids = acc_obj.search(cr, uid, [('code','ilike',code)],context=context)
        acc_id = acc_ids and acc_ids[0] or False
        return acc_id and acc_obj.browse(cr,uid,acc_id,context=context) or False

    def _get_assets(self, cr, uid, ids, category_names = (), context=None):
        assets = []
        category_obj = self.pool.get('account.asset.category')
        asset_obj = self.pool.get('account.asset.asset')
        for category_name in category_names :
            category_ids = category_obj.search(cr, uid, [('name','ilike',category_name)],context=context)
            if category_ids :
                asset_ids = category_ids[0] and asset_obj.search(cr, uid, [('category_id','=',category_ids[0])],context=context) or False
                if asset_ids :
                    assets.extend(asset_obj.browse(cr,uid,asset_ids,context=context))
        return assets

    def _write_account(self, cr, uid,ids, code, context=None):
        acc = self._get_account(cr, uid, ids, code, context=context)
        ctx_jan1 = dict(context)
        ctx_jan1['date_to'] = str(self.today.year) + '-01-01'
        acc_jan1 = self._get_account(cr, uid, ids, code, context=ctx_jan1)
        if acc :
            sheet = self.sheet
            i = self.current_line
            sheet.write(i,1,acc.name,xl_module.line_left)
            sheet.write(i,2,acc.code)
            sheet.write(i,6,acc_jan1.balance)
            sheet.write(i,10,xl_module.list_sum([[i,6,+1],[i,7,+1],[i,8,-1]]),xl_module.line)
            for j in (13,14):
                sheet.write(i,j,"",xl_module.black_line)
            for j in range(15,28):
                sheet.write(i,j,"",xl_module.blue_line)
            sheet.write(i,28,acc.balance,xl_module.line_right)

            self.current_line += 1

    def _write_lines(self, cr, uid, ids, category_names, context=None) :
        i = self.current_line
        sheet = self.sheet
        today = self.today
        year = today.year
        month = today.month
        day = today.day
        sheet.row(i).height_mismatch = True
        sheet.row(i).height = 256/2*3
        for j in (13,14):
            sheet.write(i-1,j,"",xl_module.black_line)
        for j in range(15,28):
            sheet.write(i-1,j,"",xl_module.blue_line)
        assets = self._get_assets(cr, uid, ids, category_names=category_names, context=context)
        if not assets or len(assets)<=0:
            self.current_line += 1
            return
        for asset in assets :
            sheet.write(i,1,asset.name,xl_module.line_left)
            sheet.write(i,2,asset.code or "")
            sheet.write(i,3,asset.allocation or "")
            purchase_date = datetime.strptime(asset.purchase_date_2,'%Y-%m-%d')
            sheet.write(i,4,purchase_date.strftime('%d/%m/%Y'),xl_module.line)
            if purchase_date < datetime(2014,1,1):
                sheet.write(i,5,float(asset.x_purchase_value),xl_module.line)
            else:
                sheet.write(i,5,asset.purchase_value,xl_module.line)
            sheet.write(i,6,xl_module.list_sum([[i,5,+1],[i,12,-1]] if datetime.strptime(asset.purchase_date,'%Y-%m-%d') > datetime(year,1,1) else 0))
            sheet.write(i,10,xl_module.list_sum([[i,6,+1],[i,7,+1],[i,8,-1]]),xl_module.line)
            sheet.write(i,11,str(int(100.0/(asset.category_id.method_number/12.0))) + "%",xl_module.line)
            totcurr = an_dot = 0.0
            totpre = asset.dep_2013 or 0.0
            m_deprec = [0.0]*12
            if len(asset.depreciation_line_ids)>0:
                an_dot = asset.depreciation_line_ids[0].amount *12.0
                for line in asset.depreciation_line_ids :
                    deprec_date = datetime.strptime(line.depreciation_date,'%Y-%m-%d')
                    if deprec_date.year > 2013 and deprec_date.year < year:
                        totpre += line.amount
                    elif deprec_date.year == year :
                        m_deprec[deprec_date.month-1] = line.amount
                        if deprec_date < today:
                            totcurr += line.amount
            sheet.write(i,12,totpre,xl_module.line)
            sheet.write(i,13,an_dot,xl_module.black_line)
            sheet.write(i,14,totcurr,xl_module.black_red_line)
            for j in range(0,11) :
                sheet.write(i,15+j,m_deprec[j],xl_module.blue_line)
            sheet.write(i,26,m_deprec[11],xl_module.blue_red_line)
            sheet.write(i,27,xl_module.range_sum(i,15,i,26),xl_module.blue_red_line)
            sheet.write(i,28,asset.value_residual,xl_module.line_right)
            i += 1
        self.current_line = i


    def _write_total(self, title, i1, i2):
        self.current_line += 1
        i = self.current_line
        sheet = self.sheet
        sheet.write(self.current_line-1,1,"",xl_module.line_left)
        sheet.write(self.current_line-1,28,"",xl_module.line_right)
        for j in (13,14):
            sheet.write(i-1,j,"",xl_module.black_line)
        for j in range(15,28):
            sheet.write(i-1,j,"",xl_module.blue_line)
        self.total_lines.append(self.current_line)
        sheet.row(self.current_line).height_mismatch = True
        sheet.row(self.current_line).height = 256*3
        sheet.write(self.current_line,1,title,xl_module.total_left)
        for j in (2,3,4,9,11) :
            sheet.write(self.current_line,j,"",xl_module.total_center)
        if i1<=i2 :
            for j in (5,6,7,8,10,12) :
                sheet.write(self.current_line,j,xl_module.range_sum(i1,j,i2,j),xl_module.total_center)
            sheet.write(self.current_line,13,xl_module.range_sum(i1,13,i2,13),xl_module.total_black)
            sheet.write(self.current_line,14,xl_module.range_sum(i1,14,i2,14),xl_module.total_black_red)

            for j in range(15,26) :
                sheet.write(self.current_line,j,xl_module.range_sum(i1,j,i2,j),xl_module.total_blue)

            sheet.write(self.current_line,26,xl_module.range_sum(i1,26,i2,26),xl_module.total_blue_red)
            sheet.write(self.current_line,27,xl_module.range_sum(i1,27,i2,27),xl_module.total_blue_red)
            sheet.write(self.current_line,28,xl_module.range_sum(i1,28,i2,28),xl_module.total_right)
        self.current_line += 1

    def _write_total_total(self,title):
        self.current_line += 1
        sheet = self.sheet
        sheet.write(self.current_line-1,1,"",xl_module.line_left)
        sheet.write(self.current_line-1,28,"",xl_module.line_right)
        sheet.row(self.current_line).height_mismatch = True
        sheet.row(self.current_line).height = 256*3
        sheet.write(self.current_line,1,title,xl_module.total_left)
        i = self.current_line
        for j in (13,14):
            sheet.write(i-1,j,"",xl_module.black_line)
        for j in range(15,28):
            sheet.write(i-1,j,"",xl_module.blue_line)
        for j in (4,9,11) :
            sheet.write(self.current_line,j,"",xl_module.total_center)
        for j in (6,7,8,10,12) :
            cell_list = []
            for k in self.total_lines :
                cell_list.append([k,j,+1])
            sheet.write(self.current_line,j,xl_module.list_sum(cell_list),xl_module.total_center)
        cell_list = []
        for k in self.total_lines :
            cell_list.append([k,13,+1])
        sheet.write(self.current_line,13,xl_module.list_sum(cell_list),xl_module.total_black)
        cell_list = []
        for k in self.total_lines :
            cell_list.append([k,14,+1])
        sheet.write(self.current_line,14,xl_module.list_sum(cell_list),xl_module.total_black)
        for j in range(15,26) :
            cell_list = []
            for k in self.total_lines :
                cell_list.append([k,j,+1])
            sheet.write(self.current_line,j,xl_module.list_sum(cell_list),xl_module.total_blue)
        cell_list = []
        for k in self.total_lines :
            cell_list.append([k,26,+1])
        sheet.write(self.current_line,26,xl_module.list_sum(cell_list),xl_module.total_blue_red)
        cell_list = []
        for k in self.total_lines :
            cell_list.append([k,27,+1])
        sheet.write(self.current_line,27,xl_module.list_sum(cell_list),xl_module.total_blue_red)
        cell_list = []
        for k in self.total_lines :
            cell_list.append([k,28,+1])
        sheet.write(self.current_line,29,xl_module.list_sum(cell_list),xl_module.total_right)
        self.current_line += 1


    def _write_report(self, cr, uid, ids, context=None):

        sheet = self.sheet
        self.current_line = 0
        self.total_lines = []

        # Date
        today = self.today
        today_s = today.strftime("%d/%m/%Y")
        year = today.year
        month = today.month
        day = today.day
        jan1 = date(year,1,1)
        month1 = date(year,month,1)
        tydec31 = date(year,12,31)
        lydec31 = date(year-1,12,31)
        monthlast = date(year,month,calendar.monthrange(year,month)[1])


        # Column width + row height
        sheet.row(0).height_mismatch = True
        sheet.row(0).height = 50
        sheet.col(0).width = 50
        sheet.col(1).width = 10000
        sheet.col(2).width = 3000
        for j in range(3,8) :
            sheet.col(j).width = 6000

        # Titles
        sheet.write_merge(1,1,1,10,'LCT SA',xl_module.title1)
        sheet.row(2).height_mismatch = True
        sheet.row(2).height = 256*5
        sheet.write_merge(2,2,2,27,'TABLEAU DES IMMOBILISATIONS AU ' + today_s,xl_module.title2)


        # Column labels level 1
        sheet.row(5).height_mismatch = True
        sheet.row(5).height = 256*4
        sheet.write(5,1,u"Désignation de l'immobilisation",xl_module.label_left)
        sheet.write(5,2,"Code",xl_module.label_center)
        sheet.write(5,3,"Allocation",xl_module.label_center)
        sheet.write(5,4,"Date d'aquisition",xl_module.label_center)
        sheet.write(5,5,"Purchase Value",xl_module.label_center)
        sheet.write_merge(5,5,6,8,'Valeur brute',xl_module.label_center)
        sheet.write_merge(5,5,9,10,"",xl_module.label_center)
        sheet.write(5,11,"Taux d'amortissement",xl_module.label_center)
        sheet.write_merge(5,5,12,16,'Amortissements',xl_module.label_center)
        sheet.write_merge(5,5,17,27,"",xl_module.label_center)
        sheet.write(5,28,"Valeur comptable nette au " + today_s,xl_module.label_right)

        # Column labels level 2
        sheet.row(6).height_mismatch = True
        sheet.row(6).height = 256*3
        sheet.write(6,1,"",xl_module.line_left)
        sheet.write(6,6,"VALEURS AU " + jan1.strftime("%d/%m/%Y"),xl_module.label_center)
        sheet.write(6,7,"AQUISITIONS",xl_module.label_center)
        sheet.write(6,8,"SORTIES OU TRANSFERTS",xl_module.label_center)
        sheet.write(6,9,"",xl_module.label_center)
        sheet.write(6,10,"VALEURS AU " + monthlast.strftime("%d/%m/%Y"),xl_module.label_center)
        sheet.write(6,12,u"Amortissements cumulés au " + jan1.strftime("%d/%m/%Y"),xl_module.label_center)
        sheet.write(6,13,"Dotations annuelles",xl_module.label_black)
        sheet.write(6,14,"Dotations annuelles au prorata",xl_module.label_black_red)
        sheet.write(6,15,"Janvier",xl_module.label_month)
        sheet.write(6,16,u"Février",xl_module.label_month)
        sheet.write(6,17,"Mars",xl_module.label_month)
        sheet.write(6,18,"Avril",xl_module.label_month)
        sheet.write(6,19,"Mai",xl_module.label_month)
        sheet.write(6,20,"Juin",xl_module.label_month)
        sheet.write(6,21,"Juillet",xl_module.label_month)
        sheet.write(6,22,"Aout",xl_module.label_month)
        sheet.write(6,23,"Septembre",xl_module.label_month)
        sheet.write(6,24,"Octobre",xl_module.label_month)
        sheet.write(6,25,"Novembre",xl_module.label_month)
        sheet.write(6,26,u"Décembre",xl_module.label_blue_red)
        sheet.write(6,27,"",xl_module.blue_red_line)
        sheet.write(6,28,"",xl_module.line_right)

        # Charges immobilisées
        sheet.write(7,1,"",xl_module.line_left)
        sheet.write(7,28,"",xl_module.line_right)
        i = 8
        for j in (13,14):
            sheet.write(i-1,j,"",xl_module.black_line)
        for j in range(15,28):
            sheet.write(i-1,j,"",xl_module.blue_line)
        sheet.row(self.current_line).height_mismatch = True
        sheet.row(self.current_line).height = 256/2*3
        sheet.write(8,1,u"Charges immobilisées",xl_module.as_name)
        sheet.write(8,28,"",xl_module.line_right)
        self.current_line = 9
        i = self.current_line
        for j in (13,14):
            sheet.write(i-1,j,"",xl_module.black_line)
        for j in range(15,28):
            sheet.write(i-1,j,"",xl_module.blue_line)
        self._write_account(cr, uid, ids, '20110000', context=context)
        self._write_account(cr, uid, ids, '20140000', context=context)
        self._write_account(cr, uid, ids, '20280000', context=context)
        self._write_total(u"Total Charges immobilisées",i,self.current_line-1)


        self.current_line = 14
        # Licences et Logiciels
        sheet.row(self.current_line).height_mismatch = True
        sheet.row(self.current_line).height = 256/2*3
        sheet.write(self.current_line,1,"Licences et Logiciels",xl_module.as_name)
        sheet.write(self.current_line,28,"",xl_module.line_right)
        self.current_line += 1
        self._write_lines(cr, uid, ids, ("Licences", "Logiciels"), context=None)
        self._write_total(u"Total logiciels",i,self.current_line-1)

        # Bâtiments, Installation techn. Agencements
        sheet.row(self.current_line).height_mismatch = True
        sheet.row(self.current_line).height = 256/2*3
        sheet.write(self.current_line,1,u"Bâtiments, Installation techn. Agencements",xl_module.as_name)
        sheet.write(self.current_line,28,"",xl_module.line_right)
        self.current_line += 1
        i = self.current_line
        for j in (13,14):
            sheet.write(i-1,j,"",xl_module.black_line)
        for j in range(15,28):
            sheet.write(i-1,j,"",xl_module.blue_line)
        acc = self._get_account(cr, uid, ids, '23940000', context=context)
        if acc :
            j = self.current_line
            sheet.write(j,1,"Terminal en cours de construction",xl_module.line_left)
            sheet.write(j,6,acc.balance)
            sheet.write(j,10,xl_module.list_sum([[j,6,+1],[j,7,+1],[j,8,-1]]))
            self.current_line += 1
            for k in (13,14):
                sheet.write(j,k,"",xl_module.black_line)
            for k in range(15,28):
                sheet.write(j,k,"",xl_module.blue_line)
            sheet.write(j,28,acc.balance,xl_module.line_right)
        acc = self._get_account(cr, uid, ids, '23910000', context=context)
        if acc :
            j = self.current_line
            sheet.write(j,1,u"Bâtiments et installations en cours",xl_module.line_left)
            sheet.write(j,6,acc.balance)
            sheet.write(j,10,xl_module.list_sum([[j,3,+1],[j,5,+1],[j,6,-1]]))
            self.current_line += 1
            for k in (13,14):
                sheet.write(j,k,"",xl_module.black_line)
            for k in range(15,28):
                sheet.write(j,k,"",xl_module.blue_line)
            sheet.write(j,28,acc.balance,xl_module.line_right)
        acc = self._get_account(cr, uid, ids, '23400000', context=context)
        if acc :
            j = self.current_line
            sheet.write(j,1,u"Installations Techniques (Groupes élèctrogènes)",xl_module.line_left)
            sheet.write(j,6,acc.balance)
            sheet.write(j,10,xl_module.list_sum([[j,3,+1],[j,5,+1],[j,6,-1]]))
            self.current_line += 1
            for k in (13,14):
                sheet.write(j,k,"",xl_module.black_line)
            for k in range(15,28):
                sheet.write(j,k,"",xl_module.blue_line)
            sheet.write(j,28,acc.balance,xl_module.line_right)
        self._write_total(u"Bâtiments, Installation techn. Agencements",i,self.current_line-1)


        # Mobilier de bureau
        sheet.row(self.current_line).height_mismatch = True
        sheet.row(self.current_line).height = 256/2*3
        sheet.write(self.current_line,1,"Mobiler de bureau",xl_module.as_name)
        sheet.write(self.current_line,28,"",xl_module.line_right)
        self.current_line += 1
        i = self.current_line
        self._write_lines(cr, uid, ids, ("Mobilier de bureau",), context=None)
        self._write_total(u"Total mobilier de bureau",i,self.current_line-1)

        # Matériel de bureau
        sheet.row(self.current_line).height_mismatch = True
        sheet.row(self.current_line).height = 256/2*3
        sheet.write(self.current_line,1,u"Matériel de bureau",xl_module.as_name)
        sheet.write(self.current_line,28,"",xl_module.line_right)
        self.current_line += 1
        i = self.current_line
        self._write_lines(cr, uid, ids, ("Matériel de bureau",), context=None)
        self._write_total(u"Total matériel de bureau",i,self.current_line-1)

        # Matériel de transport
        sheet.row(self.current_line).height_mismatch = True
        sheet.row(self.current_line).height = 256/2*3
        sheet.write(self.current_line,1,u"Matériel de transport",xl_module.as_name)
        sheet.write(self.current_line,28,"",xl_module.line_right)
        self.current_line += 1
        i = self.current_line
        self._write_lines(cr, uid, ids, ("Matériel de transport (25%)","Matériel de transport (33%)",), context=None)
        self._write_total(u"Total matériel de transport",i,self.current_line-1)

        # Matériel informatique
        sheet.row(self.current_line).height_mismatch = True
        sheet.row(self.current_line).height = 256/2*3
        sheet.write(self.current_line,1,u"Matériel informatique",xl_module.as_name)
        sheet.write(self.current_line,28,"",xl_module.line_right)
        self.current_line += 1
        i = self.current_line
        self._write_lines(cr, uid, ids, ("Matériel informatique",), context=None)
        self._write_total(u"Total matériel informatique",i,self.current_line-1)

        # Matériel et mobilier des logements du personnel
        sheet.row(self.current_line).height_mismatch = True
        sheet.row(self.current_line).height = 256/2*3
        sheet.write(self.current_line,1,u"Matériel et mobilier des logements du personnel",xl_module.as_name)
        sheet.write(self.current_line,28,"",xl_module.line_right)
        self.current_line += 1
        i = self.current_line
        self._write_lines(cr, uid, ids, ("Matériel et mobilier des logements du personnel",), context=None)
        self._write_total(u"Total matériel et mobilier des logements du personnel",i,self.current_line-1)

        # Matériel en cours
        sheet.row(self.current_line).height_mismatch = True
        sheet.row(self.current_line).height = 256/2*3
        sheet.write(self.current_line,1,u"Matériels en cours",xl_module.as_name)
        for i in range(self.current_line+1,self.current_line+15):
            sheet.write(i,1,"",xl_module.line_left)
        for i in range(self.current_line,self.current_line+15):
            sheet.write(i,28,"",xl_module.line_right)
            for k in (13,14):
                sheet.write(i,k,"",xl_module.black_line)
            for k in range(15,28):
                sheet.write(i,k,"",xl_module.blue_line)
        self.current_line += 15
        self._write_total(u"Total matériels en cours",self.current_line-14,self.current_line-1)

        # Total
        self._write_total_total(u"Total immobilisations")


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


