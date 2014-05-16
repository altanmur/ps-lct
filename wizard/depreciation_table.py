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

    _inherit = "account.common.account.report"
    _name = "lct_finance.depreciation.table.report"

    def _get_account(self, cr, uid, ids, code, context=None):
        acc_obj = self.pool.get('account.account')
        acc_ids = acc_obj.search(cr, uid, [('code','ilike',code)],context=context)
        acc_id = acc_ids and acc_ids[0] or False
        return acc_id and acc_obj.browse(cr,uid,acc_id,context=context)

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


    def _write_report(self, cr, uid, ids, context=None):

        report = Workbook()
        sheet = report.add_sheet('Sheet 1')


        # Dates
        today = date.today()
        today_s = today.strftime("%d/%m/%Y")
        year = today.year
        month = today.month
        jan1 = date(year,1,1)
        month1 = date(year,month,1)
        tydec31 = date(year,12,31)
        lydec31 = date(year-1,12,31)
        monthlast = date(year,month,calendar.monthrange(year,month)[1])


        # Style
        bold = 'font: bold 1;'
        italic = 'font: italic 1;'
        text_white = 'font: color white;'
        background_green = 'pattern: pattern solid, fore_color green;'
        background_black = 'pattern: pattern solid, fore_color black;'
        hor_center = 'alignment: horizontal center;'
        vert_center = 'alignment: vertical center;'
        text_wrap = 'alignment: wrap 1;'
        border_l = 'border : left medium;'
        border_r = 'border : right medium;'
        border_b = 'border : bottom medium;'
        border_t = 'border : top medium;'


        title1_xf = easyxf(
            text_white +
            background_black +
            hor_center)
        title2_xf = easyxf(
            bold +
            text_white +
            background_green +
            vert_center)
        labelleft_xf = easyxf(
            bold +
            italic +
            text_wrap +
            border_l +
            border_t +
            border_b +
            hor_center +
            vert_center)
        labelcenter_xf = easyxf(
            bold +
            italic +
            text_wrap +
            border_t +
            border_b +
            hor_center +
            vert_center)
        labelright_xf = easyxf(
            bold +
            italic +
            text_wrap +
            border_r +
            border_t +
            border_b +
            hor_center +
            vert_center)

        # Column width
        sheet.col(1).width = 10000
        for i in range(2,28) :
            sheet.col(i).width = 5000

        # Titles
        sheet.write_merge(1,1,1,10,'LCT SA',title1_xf)
        sheet.row(2).height = 256*5
        sheet.write_merge(2,2,2,27,'TABLEAU DES IMMOBILISATIONS AU ' + today_s,title2_xf)

        # Column labels level 1
        sheet.row(5).height = 256*4
        sheet.write(5,1,u"Désignation de l'immobilisation",labelleft_xf)
        sheet.write(5,2,"Date d'aquisition",labelcenter_xf)
        sheet.write_merge(5,5,3,7,'Valeur brute',labelcenter_xf)
        sheet.write_merge(5,5,8,9,"",labelcenter_xf)
        sheet.write(5,10,"Taux d'amortissement",labelcenter_xf)
        sheet.write_merge(5,5,11,15,'Amortissements',labelcenter_xf)
        sheet.write_merge(5,5,16,26,"",labelcenter_xf)
        sheet.write(5,27,"Valeur comptable nette au " + today_s,labelright_xf)

        # Column labels level 2
        sheet.row(6).height = 256*3
        sheet.write(6,3,"VALEURS AU " + jan1.strftime("%d/%m/%Y"),labelcenter_xf)
        sheet.write(6,4,"VALEURS AU " + month1.strftime("%d/%m/%Y"),labelcenter_xf)
        sheet.write(6,5,"AQUISITIONS",labelcenter_xf)
        sheet.write(6,6,"SORTIES OU TRANSFERTS",labelcenter_xf)
        sheet.write(6,7,"VALEURS AU " + tydec31.strftime("%d/%m/%Y"),labelcenter_xf)
        sheet.write(6,9,"VALEURS AU " + monthlast.strftime("%d/%m/%Y"),labelcenter_xf)
        sheet.write(6,11,u"Amortissements cumulés au " + lydec31.strftime("%d/%m/%Y"),labelcenter_xf)
        sheet.write(6,12,"Dotations annuelles",labelcenter_xf)
        sheet.write(6,13,"Dotations annuelles au prorata",labelcenter_xf)
        sheet.write(6,14,"Janvier",labelcenter_xf)
        sheet.write(6,15,u"Février",labelcenter_xf)
        sheet.write(6,16,"Mars",labelcenter_xf)
        sheet.write(6,17,"Avril",labelcenter_xf)
        sheet.write(6,18,"Mai",labelcenter_xf)
        sheet.write(6,19,"Juin",labelcenter_xf)
        sheet.write(6,20,"Juillet",labelcenter_xf)
        sheet.write(6,21,"Aout",labelcenter_xf)
        sheet.write(6,22,"Septembre",labelcenter_xf)
        sheet.write(6,23,"Octobre",labelcenter_xf)
        sheet.write(6,24,"Novembre",labelcenter_xf)
        sheet.write(6,25,u"Décembre",labelcenter_xf)


        # Charges immobilisées
        sheet.write(8,1,u"Charges immobilisées",labelleft_xf)
        balance = 0.0

        ## Frais de constitution
        code = '20110000'
        acc = self._get_account(cr, uid, ids, code, context=context)
        if acc :
            sheet.write(9,1,acc.name)
            sheet.write(9,3,acc.balance)
            sheet.write(9,4,'=D10')

        ## Charges à étaler
        code = '20280000'
        acc = self._get_account(cr, uid, ids, code, context=context)
        if acc :
            sheet.write(10,1,acc.name)
            sheet.write(10,3,acc.balance)
            sheet.write(10,4,'=D11')

        ## Frais de fonctionnement antérieurs au démarrage
        code  = '20140000'
        acc = self._get_account(cr, uid, ids, code, context=context)
        if acc :
            sheet.write(11,1,acc.name)
            sheet.write(11,3,acc.balance)
            sheet.write(11,4,'=D12')


        sheet.write(13,1,u"Total Charges immobilisées",labelleft_xf)
        sheet.write(13,3,'=D10+D11+D12')
        sheet.write(13,4,'=E10+E11+E12')

        i = 14
        # Licences et Logiciels
        sheet.write(i,1,u"Licences et Logiciels",labelleft_xf)
        i += 1
        category_names = ("Licences","Logiciels")
        for asset in self._get_assets(cr, uid, ids, category_names=category_names, context=context):
            sheet.write(i,1,asset.name)
            purchase_date = datetime.strptime(asset.purchase_date,'%Y-%m-%d')
            sheet.write(i,2,purchase_date.strftime('%d/%m/%Y'))
            if purchase_date < datetime(2014,1,1) :
                sheet.write(i,3,float(asset.x_purchase_value))
            else :
                sheet.write(i,3,float(asset.purchase_value))
            sheet.write(i,4,'=D' + str(i+1))
            i += 1




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

