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
import StringIO
import base64
from datetime import datetime
from datetime import date, timedelta


class balance_sheet(osv.osv_memory):
    
    _inherit = "accounting.report"
    _name = "balance.sheet"
    
    
    def _get_root_parents(self, cr, uid, ids, parents, children, context=None):
       
        if children == []:
            return parents
        parent = children[0].parent_id
        if not parent:
            if children[0] not in parents:
                parents.append(children[0])
            del children[0]
        else :
            children[0] = parent
        return self._get_root_parents(cr, uid, ids, parents, children, context=context)
        
    def _format_sheet(self, cr, uid, ids, sheet, context=None):
        for i in range(1,4):
            col=sheet.col(i)
            col.width = 7000
            
        row = sheet.row(3)
        row.height_mismatch = True
        row.height = 20*30
        sheet.write_merge(3,3,1,3,"Balance Sheet",easyxf(
            'font: name Calibri, height 320,bold on;'
            'borders: left thick,right thick,top thick;'
            'align: horizontal center, vertical center;'
            ))
        row = sheet.row(4)
        row.height_mismatch = True
        row.height = 20*30
        
        sheet.write_merge(4,4,1,3,"Lome Container Terminal",easyxf(
            'font: name Calibri, height 320,bold on;'
            'borders: left thick,right thick,bottom thick;'
            'align: horizontal center, vertical center;'
            ))
            
        sheet.write(6,1,"",easyxf(
            'border: left thin,top thin;'
            ))
        sheet.write(6,2,"",easyxf(
            'border: top thin;'
            ))
        sheet.write(6,3,"",easyxf(
            'border: right thin,top thin;'
            ))
        sheet.write(7,1,"Date of report : ",easyxf(
            'border: left thin;'
            'font: name Calibri,bold on;'
            ))
        sheet.write(7,2,date.today().strftime("%d-%m-%Y"),easyxf(
            'font: name Calibri,bold on;'
            ))
        sheet.write(7,3,"",easyxf(
            'border: right thin;'
            ))
        sheet.write(8,1,"",easyxf(
            'border: left thin,bottom thin;'
            ))
        sheet.write(8,2,"",easyxf(
            'border: bottom thin;'
            ))
        sheet.write(8,3,"",easyxf(
            'border: right thin,bottom thin;'
            ))
            
    def _get_accounts(self, cr, uid,  ids, accounts, context=None):
        result_accounts = []
        while True :
            if accounts == []:
                break
            if accounts[0].child_parent_ids != []:
                for child in accounts[0].child_parent_ids:
                    accounts.insert(1,child)
            result_accounts.append(accounts[0])
            accounts.pop(0)
        return result_accounts
        
        
    def _fill_data(self, cr, uid,  ids, sheet, context=None):

        i = 10
        accounts = []
        for journal in self.browse(cr,uid,ids,context=context)[0].journal_ids :
            account = journal.default_debit_account_id
            if account:
                if account not in accounts:
                    accounts.append(account)
        
        parent_accounts = self._get_root_parents(cr, uid, ids, [], accounts, context=context)
        accounts = self._get_accounts(cr, uid,  ids, parent_accounts, context=context)
        accounts.reverse()
      
        for i in range(0,len(accounts)):
            row = sheet.row(i+10)
            if accounts[i].child_parent_ids == [] :
                row.write(1,accounts[i].code,easyxf(
                    'align: horizontal center, vertical center;'
                    ))
                row.write(2,accounts[i].name,easyxf(
                    'align: horizontal center, vertical center;'
                    ))
                row.write(3,accounts[i].debit - accounts[i].debit,easyxf(
                    'align: horizontal center, vertical center;'
                    ))
            else :
                row.write(1,accounts[i].code,easyxf(
                    'font: bold on;'
                    'borders: left thin,right thin,bottom thin, top thin;'
                    'align: horizontal center, vertical center;'
                    ))
                row.write(2,accounts[i].name,easyxf(
                    'font: bold on;'
                    'borders: left thin,right thin,bottom thin, top thin;'
                    'align: horizontal center, vertical center;'
                    ))
                row.write(3,accounts[i].debit - accounts[i].debit,easyxf(
                    'font:bold on;'
                    'borders: left thin,right thin,bottom thin, top thin;'
                    'align: horizontal center, vertical center;'
                    ))
          
    def _write_report(self, cr, uid, ids, context=None):
        report = Workbook()
        sheet = report.add_sheet('Balance Sheet',cell_overwrite_ok=True) 
        self._format_sheet(cr, uid, ids, sheet=sheet,context=context)
        
        self._fill_data( cr, uid, ids, sheet=sheet, context=context)
        return report
        
    
    def print_report(self, cr, uid, ids, name, context=None):
        if context is None:
            context = {}
        print name

        report = self._write_report(cr,uid,ids,context=context)
        
        
        f = StringIO.StringIO()
        report.save(f)
        xls_file = base64.b64encode(f.getvalue())
        dlwizard = self.pool.get('balance.sheet.download').create(cr, uid, {'xls_report' : xls_file}, context=dict(context, active_ids=ids))
        return {
            'view_mode': 'form',
            'view_id': False,
            'view_type': 'form',
            'res_model': 'balance.sheet.download',
            'res_id': dlwizard,
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'new',
            'domain': '[]',
            'context': dict(context, active_ids=ids)
        }
        
