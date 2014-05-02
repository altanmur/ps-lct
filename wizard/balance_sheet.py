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
    
    
    
    #~ def _get_root_parents(self, cr, uid, ids, parents, children, context=None):
       #~ 
        #~ if children == []:
            #~ return parents
        #~ parent = children[0].parent_id
        #~ if not parent:
            #~ if children[0] not in parents:
                #~ parents.append(children[0])
            #~ del children[0]
        #~ else :
            #~ children[0] = parent
        #~ return self._get_root_parents(cr, uid, ids, parents, children, context=context)
        
    def _format_sheet(self, cr, uid, ids, sheet, context=None):
        
        col=sheet.col(1)
        sheet.col(1).width = 5000
        sheet.col(2).width = 12000
        sheet.col(3).width = 5000
            
        row = sheet.row(3)
        row.height_mismatch = True
        row.height = 20*30
        sheet.write_merge(3,3,1,3,"Balance Sheet",easyxf(
            'font: name Calibri, height 320,bold on;'
            'borders: left thick, right thick, top thick;'
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
            

        
        
    def _fill_data(self, cr, uid,  ids, sheet, context=None):
        
        
        if self.browse(cr,uid,ids,context=context)[0].date_from : context['date_from'] = self.browse(cr,uid,ids,context=context)[0].date_from
        if self.browse(cr,uid,ids,context=context)[0].date_to : context['date_to'] = self.browse(cr,uid,ids,context=context)[0].date_to
        if self.browse(cr,uid,ids,context=context)[0].period_from : context['date_from'] = self.browse(cr,uid,ids,context=context)[0].period_from.date_start
        if self.browse(cr,uid,ids,context=context)[0].period_to : context['date_to'] = self.browse(cr,uid,ids,context=context)[0].period_to.date_stop
        #self.write(cr, uid, ids,{ 'chart_account_id': self.pool.get('account.account').search(cr,uid,[('name','ilike','IFRS')],context=context)[0]})
        
        
        domain = [('note','ilike','IFRS'),'|',('code','ilike','2%'),('code','ilike','3%')]
        acc_ids = self.pool.get('account.account').search(cr, uid,domain,order="code")
        import pdb; pdb.set_trace()
        accounts = self.pool.get('account.account').browse(cr,uid,acc_ids,context=context)
        
        
        
        if accounts == []:
            return 
        
        row = sheet.row(10)
        if accounts[0].code[1] == "X":
            row.write(1,accounts[0].code,easyxf(
                'font: bold on, height 240, colour white;'
                'pattern: pattern solid, fore_colour black;'
                'borders: left thin,right thin,bottom thin, top thin;'
                'align: horizontal center, vertical center;'
                ))
            row.write(2,accounts[0].name,easyxf(
                'font: bold on, height 240, colour white;'
                'pattern: pattern solid, fore_colour black;'
                'borders: left thin,right thin,bottom thin, top thin;'
                'align: horizontal center, vertical center;'
                ))
            row.write(3,accounts[0].debit - accounts[0].debit,easyxf(
                'font:bold on, height 240, colour white;'
                'pattern: pattern solid, fore_colour black;'
                'borders: left thin,right thin,bottom thin, top thin;'
                'align: horizontal center, vertical center;'
                ))
        elif accounts[0].child_parent_ids:
            row.write(1,accounts[0].code,easyxf(
                'font: bold on, height 240;'
                'borders: left thin,right thin,bottom thin, top thin;'
                'align: horizontal center, vertical center;'
                ))
            row.write(2,accounts[0].name,easyxf(
                'font: bold on, height 240;'
                'borders: left thin,right thin,bottom thin, top thin;'
                'align: horizontal center, vertical center;'
                ))
            row.write(3,accounts[0].debit - accounts[0].debit,easyxf(
                'font:bold on, height 240, colour white;'
                'pattern: pattern solid, fore_colour grey25;'
                'borders: left thin,right thin,bottom thin, top thin;'
                'align: horizontal center, vertical center;'
                ))
        elif accounts[0].code[-1] != "X":
            row.write(1,accounts[0].code,easyxf(
                'align: horizontal center, vertical center;'
                'border: left thin'
                ))
            row.write(2,accounts[0].name,easyxf(
                'align: horizontal center, vertical center;'
                'border: left thin, right thin'
                ))
            row.write(3,accounts[0].debit - accounts[0].debit,easyxf(
                'align: horizontal center, vertical center;'
                'border: right thin'
                ))
        j = 0
        for i in range(1,len(accounts)):
            j = j+1
            row = sheet.row(j+10)
            if accounts[i].code[1] == "X":
                row.write(1,accounts[i].code,easyxf(
                    'font: bold on, height 240, colour white;'
                    'pattern: pattern solid, fore_colour black;'
                    'borders: left thin,right thin,bottom thin, top thin;'
                    'align: horizontal center, vertical center;'
                    ))
                row.write(2,accounts[i].name,easyxf(
                    'font: bold on, height 240, colour white;'
                    'pattern: pattern solid, fore_colour black;'
                    'borders: left thin,right thin,bottom thin, top thin;'
                    'align: horizontal center, vertical center;'
                    ))
                row.set_cell_number(3,accounts[i].balance,easyxf(
                    'font:bold on, height 240, colour white;'
                    'pattern: pattern solid, fore_colour black;'
                    'borders: left thin,right thin,bottom thin, top thin;'
                    'align: horizontal center, vertical center;',
                    num_format_str='#,##0'
                    ))
            elif accounts[i].child_parent_ids != []:
                row.write(1,accounts[i].code,easyxf(
                    'font: bold on, height 240;'
                    'borders: left thin,right thin,bottom thin, top thin;'
                    'align: horizontal center, vertical center;'
                    ))
                row.write(2,accounts[i].name,easyxf(
                    'font: bold on, height 240;'
                    'borders: left thin,right thin,bottom thin, top thin;'
                    'align: horizontal center, vertical center;'
                    ))
                row.set_cell_number(3,accounts[i].balance,easyxf(
                    'font:bold on, height 240, colour white;'
                    'pattern: pattern solid, fore_colour grey25;'
                    'borders: left thin,right thin,bottom thin, top thin;'
                    'align: horizontal center, vertical center;',
                    num_format_str='#,##0'
                    ))
            elif accounts[i].code[-1] != "X":
                row.write(1,accounts[i].code,easyxf(
                    'align: horizontal center, vertical center;'
                    'border: left thin'
                    ))
                row.write(2,accounts[i].name,easyxf(
                    'align: horizontal center, vertical center;'
                    'border: left thin, right thin'
                    ))
                row.set_cell_number(3,accounts[i].balance,easyxf(
                    'align: horizontal center, vertical center;'
                    'border: right thin',
                    num_format_str='#,##0'
                    ))
            else : j = j-1
            
                    
        
        
          
    def _write_report(self, cr, uid, ids, context=None):
        report = Workbook(style_compression=2)
        sheet = report.add_sheet('Balance Sheet',cell_overwrite_ok=True) 
        self._format_sheet(cr, uid, ids, sheet=sheet,context=context)
        self._fill_data( cr, uid, ids, sheet=sheet, context=context)
        return report
        
    
    def print_report(self, cr, uid, ids, name, context=None):
        if context is None:
            context = {}
        
        
        #if self.browse(cr,uid,ids,context=context)[0].filter == "filter_no" :
        report = self._write_report(cr,uid,ids,context=context)
        #rt.add_sheet('Balance Sheet',cell_overwrite_ok=True)
        
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
        
