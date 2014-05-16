
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
import calendar
import copy


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
        return acc_id and acc_obj.browse(cr,uid,acc_id,context=context)

    def _write_account(self, cr, uid,ids, code, context=None):
        acc = self._get_account(cr, uid, ids, code, context=context)
        if acc :
            sheet = self.sheet
            i = self.current_line
            sheet.write(i,1,acc.name)
            sheet.write(i,3,acc.balance)
            sheet.write(i,4,'=+D' + str(i+1))
            sheet.write(i,7,"=+D"+ str(i+1) + "+F" + str(i+1) + "-G" + str(i+1))
            sheet.write(i,9,"=+D" + str(i+1) + "+F" + str(i+1) + "-G" + str(i+1))
            self.current_line += 1


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

    def _write_lines(self, cr, uid, ids, category_names, context=None) :
        i = self.current_line
        sheet = self.sheet
        today = self.today
        year = today.year
        month = today.month
        day = today.day
        assets = self._get_assets(cr, uid, ids, category_names=category_names, context=context)
        if not assets or len(assets)<=0:
            self.current_line += 1
            return
        for asset in assets :
            sheet.write(i,1,asset.name)
            purchase_date = datetime.strptime(asset.purchase_date_2,'%Y-%m-%d')
            sheet.write(i,2,purchase_date.strftime('%d/%m/%Y'))
            if year<=2014 and purchase_date <= datetime(2014,1,1):
                sheet.write(i,3,float(asset.x_purchase_value))
            elif purchase_date < datetime(year,1,1):
                sheet.write(i,3,float(asset.purchase_value))
            sheet.write(i,4,"=D" + str(i+1))
            sheet.write(i,7,"=D" + str(i+1) + "+F" + str(i+1) + "-G" + str(i+1))
            sheet.write(i,9,"=D" + str(i+1) + "+F" + str(i+1) + "-G" + str(i+1))
            sheet.write(i,10,str(int(100.0/(asset.category_id.method_number/12.0))) + "%")
            totpre = totcurr = 0.0
            m_deprec = [0.0 for j in range(0,12)]
            an_dot = None
            if len(asset.depreciation_line_ids)>0:
                an_dot = asset.depreciation_line_ids[0].amount *12.0
                for line in asset.depreciation_line_ids :
                    deprec_date = datetime.strptime(line.depreciation_date,'%Y-%m-%d')
                    if  deprec_date < datetime(year,1,1) :
                        totpre += line.amount
                    elif deprec_date < datetime(year,month,day) :
                        m_deprec[deprec_date.month-1] = line.amount
                        totcurr += line.amount
            sheet.write(i,11,totpre)
            sheet.write(i,12,an_dot)
            sheet.write(i,13,totcurr)
            for j in range(0,12) :
                sheet.write(i,14+j,m_deprec[j])

            sum_s1 = "="
            sum_s2 = "=+J" + str(i+1) + "-L" + str(i+1)
            for j in range(ord('O'),ord('Y')+1) :
                sum_s1 += "+" + chr(j) + str(i+1)
                sum_s2 += "-" + chr(j) + str(i+1)
            sheet.write(i,26,sum_s1)
            sheet.write(i,27,sum_s2)
            i += 1

        self.current_line = i


    def _format(self, f = ""):
        return {
            "bold" : 'font: bold 1;',
            "hor-center" : 'alignment: horizontal center;',
            "vert-center" : 'alignment: vertical center;',
            "italic" : 'font: italic 1;',
            "text-white" : 'font: color white;',
            "text-12" : 'font: height 240;',
            "text-14" : 'font: height 280;',
            "background-green" : 'pattern: pattern solid, fore_color green;',
            "background-black" : 'pattern: pattern solid, fore_color black;',
            "wrap" : 'alignment: wrap 1;',
            "border-l" : 'border : left medium;',
            "border-r" : 'border : right medium;',
            "border-b" : 'border : bottom medium;',
            "border-t" : 'border : top medium;',
            "background-blue" : 'pattern: pattern solid, fore_color blue;'
        }[f]


    def _cell_format(self, format_list = ()) :
        format_s = ""
        for f in format_list :
            format_s += self._format(f)
        return easyxf(format_s)

    def _write_total(self,title,i1,i2):
        f_total_left = self._cell_format((
            "bold",
            "italic",
            "hor-center",
            "vert-center",
            "border-t",
            "border-l",
            "border-b",
            "wrap",
        ))
        sheet = self.sheet
        sheet.row(self.current_line).height = 256*2
        sheet.write(self.current_line,1,title,f_total_left)
        if i1<=i2 :
            sheet.write(self.current_line,3,"=SUM(D" + str(i1) + ":D" + str(i2) + ")")
            sheet.write(self.current_line,4,"=SUM(E" + str(i1) + ":E" + str(i2) + ")")
        self.current_line += 1



    def _write_report(self, cr, uid, ids, context=None):

        sheet = self.sheet
        self.current_line = 0


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

        # Format
        f_title1 = self._cell_format((
            "hor-center",
            "vert-center",
            "background-black",
            "text-white",
            "text-12",
            ))
        f_title2 = self._cell_format((
            "bold",
            "vert-center",
            "background-green",
            "text-white",
            "text-14",
            ))
        f_label_left = self._cell_format((
            "bold",
            "italic",
            "vert-center",
            "hor-center",
            "border-l",
            "border-t",
            "border-b",
            "wrap",
            ))
        f_label_right = self._cell_format((
            "bold",
            "italic",
            "vert-center",
            "hor-center",
            "border-r",
            "border-t",
            "border-b",
            "wrap",
            ))
        f_label_center = self._cell_format((
            "bold",
            "italic",
            "vert-center",
            "hor-center",
            "border-t",
            "border-b",
            "wrap",
            ))
        f_label_month = self._cell_format((
            "bold",
            "italic",
            "vert-center",
            "hor-center",
            "border-t",
            "border-b",
            "wrap",
            "background-blue",
            "text-white",
            ))
        f_as_name = self._cell_format((
            "bold",
            "italic",
            "hor-center",
            "vert-center",
            "wrap",
        ))


        # Column width + row height
        sheet.row(0).height = 50
        sheet.col(0).width = 50
        sheet.col(1).width = 10000
        for j in range(2,28) :
            sheet.col(j).width = 3000

        # Titles
        sheet.write_merge(1,1,1,10,'LCT SA',f_title1)
        sheet.row(2).height = 256*5
        sheet.write_merge(2,2,2,27,'TABLEAU DES IMMOBILISATIONS AU ' + today_s,f_title2)

        # Column labels level 1

        sheet.row(5).height = 256*4
        sheet.write(5,1,u"Désignation de l'immobilisation",f_label_left)
        sheet.write(5,2,"Date d'aquisition",f_label_center)
        sheet.write_merge(5,5,3,7,'Valeur brute',f_label_center)
        sheet.write_merge(5,5,8,9,"",f_label_center)
        sheet.write(5,10,"Taux d'amortissement",f_label_center)
        sheet.write_merge(5,5,11,15,'Amortissements',f_label_center)
        sheet.write_merge(5,5,16,26,"",f_label_center)
        sheet.write(5,27,"Valeur comptable nette au " + today_s,f_label_right)

        # Column labels level 2
        sheet.row(6).height = 256*3
        sheet.write(6,3,"VALEURS AU " + jan1.strftime("%d/%m/%Y"),f_label_center)
        sheet.write(6,4,"VALEURS AU " + month1.strftime("%d/%m/%Y"),f_label_center)
        sheet.write(6,5,"AQUISITIONS",f_label_center)
        sheet.write(6,6,"SORTIES OU TRANSFERTS",f_label_center)
        sheet.write(6,7,"VALEURS AU " + tydec31.strftime("%d/%m/%Y"),f_label_center)
        sheet.write(6,9,"VALEURS AU " + monthlast.strftime("%d/%m/%Y"),f_label_center)
        sheet.write(6,11,u"Amortissements cumulés au " + lydec31.strftime("%d/%m/%Y"),f_label_center)
        sheet.write(6,12,"Dotations annuelles",f_label_center)
        sheet.write(6,13,"Dotations annuelles au prorata",f_label_center)
        sheet.write(6,14,"Janvier",f_label_month)
        sheet.write(6,15,u"Février",f_label_month)
        sheet.write(6,16,"Mars",f_label_month)
        sheet.write(6,17,"Avril",f_label_month)
        sheet.write(6,18,"Mai",f_label_month)
        sheet.write(6,19,"Juin",f_label_month)
        sheet.write(6,20,"Juillet",f_label_month)
        sheet.write(6,21,"Aout",f_label_month)
        sheet.write(6,22,"Septembre",f_label_month)
        sheet.write(6,23,"Octobre",f_label_month)
        sheet.write(6,24,"Novembre",f_label_month)
        sheet.write(6,25,u"Décembre",f_label_month)


        # Charges immobilisées
        sheet.write(8,1,u"Charges immobilisées",f_as_name)
        self.current_line = 9
        i = self.current_line
        self._write_account(cr, uid, ids, '20110000', context=context)
        self._write_account(cr, uid, ids, '20280000', context=context)
        self._write_account(cr, uid, ids, '20140000', context=context)
        self._write_total(u"Total Charges immobilisées",i+1,self.current_line)


        self.current_line = 13
        # Licences et Logiciels
        sheet.write(self.current_line,1,"Licences et Logiciels",f_as_name)
        self.current_line += 1
        i = self.current_line
        self._write_lines(cr, uid, ids, ("Licences", "Logiciels"), context=None)
        self._write_total(u"Total Logiciels",i+1,self.current_line)

        # Bâtiments, Installation techn. Agencements
        sheet.write(self.current_line,1,u"Bâtiments, Installation techn. Agencements",f_as_name)
        self.current_line += 1
        i = self.current_line
        acc = self._get_account(cr, uid, ids, '23940000', context=context)
        if acc :
            j = self.current_line
            sheet.write(j,1,"Terminal en cours de construction")
            sheet.write(j,3,acc.balance)
            sheet.write(j,4,'=+D' + str(j+1))
            sheet.write(j,7,"=+D"+ str(j+1) + "+F" + str(j+1) + "-G" + str(j+1))
            sheet.write(j,9,"=+D" + str(j+1) + "+F" + str(j+1) + "-G" + str(j+1))
            self.current_line += 1
        acc = self._get_account(cr, uid, ids, '23910000', context=context)
        if acc :
            j = self.current_line
            sheet.write(j,1,u"Bâtiments et installations en cours")
            sheet.write(j,3,acc.balance)
            sheet.write(j,4,'=+D' + str(j+1))
            sheet.write(j,7,"=+D"+ str(j+1) + "+F" + str(j+1) + "-G" + str(j+1))
            sheet.write(j,9,"=+D" + str(j+1) + "+F" + str(j+1) + "-G" + str(j+1))
            self.current_line += 1
        acc = self._get_account(cr, uid, ids, '23400000', context=context)
        if acc :
            j = self.current_line
            sheet.write(j,1,u"Installations Techniques (Groupes élèctrogènes)")
            sheet.write(j,3,acc.balance)
            sheet.write(j,4,'=+D' + str(j+1))
            sheet.write(j,7,"=+D"+ str(j+1) + "+F" + str(j+1) + "-G" + str(j+1))
            sheet.write(j,9,"=+D" + str(j+1) + "+F" + str(j+1) + "-G" + str(j+1))
            self.current_line += 1

        self._write_total(u"Total Bâtiments, Installation techn. Agencements",i+1,self.current_line)


        # Mobilier de bureau
        sheet.write(self.current_line,1,"Mobiler de bureau",f_as_name)
        self.current_line += 1
        i = self.current_line
        self._write_lines(cr, uid, ids, ("Mobilier de bureau",), context=None)
        self._write_total(u"Total mobilier de bureau",i+1,self.current_line)

        # Matériel de bureau
        sheet.write(self.current_line,1,u"Matériel de bureau",f_as_name)
        self.current_line += 1
        i = self.current_line
        self._write_lines(cr, uid, ids, ("Matériel de bureau",), context=None)
        self._write_total(u"Total matériel de bureau",i+1,self.current_line)


    def print_report(self, cr, uid, ids, name, context=None):
        if context is None:
            context = {}

        self.today = self.browse(cr,uid,ids,context=context)[0].report_date
        self.today = date.today().strftime('%Y-%m-%d')
        report = Workbook()
        self.sheet = report.add_sheet('Sheet 1')
        self._write_report(cr,uid,ids,context=context)


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
