
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

class vessel_revenue(osv.osv_memory):

    _name = "lct_finance.vessel.revenue.report"
    _columns = {
        "date_from" : fields.date(string='From',required=True),
        "date_to" : fields.date(string='To',required=True),
    }
    _defaults = {
        "date_to" : date.today().strftime('%Y-%m-%d'),
    }

    def _write_report(self, cr, uid, ids, context=None):

        inv_mod = self.pool.get('account.invoice')
        part_mod = self.pool.get('res.partner')
        prod_mod = self.pool.get('product.product')

        sheet_vessel = self.sheet_vessel
        sheet_appointment = self.sheet_appointment
        self.current_line = 0
        self.total_lines = []

        # Date
        date_to = self.date_to
        date_from = self.date_from
        date_to_s = date_to.strftime("%d/%m/%Y")
        date_from_s = date_from.strftime("%d/%m/%Y")

        # Column width + row height
        sheet_vessel.col(0).width = 10000
        sheet_vessel.col(1).width = 3000
        sheet_vessel.col(2).width = 3000
        sheet_vessel.col(3).width = 3000
        sheet_appointment.col(0).width = 10000
        sheet_appointment.col(1).width = 3000
        sheet_appointment.col(2).width = 3000
        sheet_appointment.col(3).width = 3000

        # Titles
        sheet_vessel.write_merge(0,0,0,3,'VESSEL REVENUE REPORT',xl_module.title3)
        sheet_vessel.write(2,0,"FROM",xl_module.normal)
        sheet_vessel.write(2,1,date_from_s,xl_module.normal)
        sheet_vessel.write(2,2,"TO",xl_module.normal)
        sheet_vessel.write(2,3,date_to_s,xl_module.normal)
        sheet_appointment.write_merge(0,0,0,3,'APPOINTMENT REVENUE REPORT',xl_module.title3)
        sheet_appointment.write(2,0,"FROM",xl_module.normal)
        sheet_appointment.write(2,1,date_from_s,xl_module.normal)
        sheet_appointment.write(2,2,"TO",xl_module.normal)
        sheet_appointment.write(2,3,date_to_s,xl_module.normal)

        # vessel revenue report
        invoice_ids = inv_mod.search(cr, uid, [('date_invoice','>=',date_from),('date_invoice','<=',date_to),('type2','=','vessel')], context=context)
        invoices = inv_mod.browse(cr, uid, invoice_ids, context=context)
        vessels = {}
        for invoice in invoices:
            for line in invoice.invoice_line:
                if line.product_id:
                    if vessels.get(invoice.partner_id.id):
                        if vessels[invoice.partner_id.id].get(line.product_id.id):
                            vessels[invoice.partner_id.id][line.product_id.id]['qty'] += line.quantity
                            vessels[invoice.partner_id.id][line.product_id.id]['revenue'] += line.price_subtotal
                            vessels[invoice.partner_id.id][line.product_id.id]['price'] = vessels[invoice.partner_id.id][line.product_id.id]['revenue']/vessels[invoice.partner_id.id][line.product_id.id]['qty']
                        else: 
                            vessels[invoice.partner_id.id][line.product_id.id] = {
                                'qty':line.quantity,
                                'revenue': line.price_subtotal,
                                'price': line.price_subtotal/line.quantity, 
                            }
                    else:
                        vessels[invoice.partner_id.id] = {
                            line.product_id.id: {
                                'qty':line.quantity,
                                'revenue': line.price_subtotal,
                                'price': line.price_subtotal/line.quantity, 
                            }
                        }
                else:
                    if vessels.get(invoice.partner_id.id):
                        if vessels[invoice.partner_id.id].get(False) and vessels[invoice.partner_id.id][False].get(line.name):
                            vessels[invoice.partner_id.id][False][line.name]['qty'] += line.quantity
                            vessels[invoice.partner_id.id][False][line.name]['revenue'] += line.price_subtotal
                            vessels[invoice.partner_id.id][False][line.name]['price'] = vessels[invoice.partner_id.id][False][line.name]['revenue']/vessels[invoice.partner_id.id][False][line.name]['qty']
                        elif vessels[invoice.partner_id.id].get(False) and not vessels[invoice.partner_id.id][False].get(line.name): 
                            vessels[invoice.partner_id.id][False].update({
                                line.name: {
                                    'qty':line.quantity,
                                    'revenue': line.price_subtotal,
                                    'price': line.price_subtotal/line.quantity, 
                                },
                            })
                        else :
                            vessels[invoice.partner_id.id][False] = {
                                line.name: {
                                    'qty':line.quantity,
                                    'revenue': line.price_subtotal,
                                    'price': line.price_subtotal/line.quantity, 
                                },
                            }
                    else:
                        vessels[invoice.partner_id.id] = {
                            False: {
                                line.name: {
                                    'qty':line.quantity,
                                    'revenue': line.price_subtotal,
                                    'price': line.price_subtotal/line.quantity, 
                                },
                            }
                        }

        vessels_total = {}
        self.current_line = 4
        for partner_id, products_dict in vessels.iteritems():
            sheet_vessel.write_merge(self.current_line,self.current_line,0,2,part_mod.browse(cr, uid, partner_id, context=context).name,xl_module.bold)
            sheet_vessel.write(self.current_line+1,0,"Product Name",xl_module.line_name)
            sheet_vessel.write(self.current_line+1,1,"Quantity",xl_module.line_name)
            sheet_vessel.write(self.current_line+1,2,"Price",xl_module.line_name)
            sheet_vessel.write(self.current_line+1,3,"Revenue",xl_module.line_name)
            self.current_line += 2
            for product_id, prod_dict in products_dict.iteritems():
                if product_id:
                    sheet_vessel.write(self.current_line,0,prod_mod.browse(cr, uid, product_id, context=context).name,xl_module.line_name)
                    sheet_vessel.write(self.current_line,1,prod_dict['qty'],xl_module.number)
                    sheet_vessel.write(self.current_line,2,round(prod_dict['price']),xl_module.number)
                    sheet_vessel.write(self.current_line,3,round(prod_dict['revenue']),xl_module.number)
                    self.current_line += 1
                    if vessels_total.get(product_id):
                        vessels_total[product_id]['qty'] += prod_dict['qty']
                        vessels_total[product_id]['revenue'] += prod_dict['revenue']
                        vessels_total[product_id]['price'] += prod_dict['revenue']
                    else:
                        vessels_total[product_id] = {
                                'qty': prod_dict['qty'],
                                'revenue': prod_dict['revenue'],
                                'price': prod_dict['price'], 
                            }
                else: 
                    for description, noprod_dict in prod_dict.iteritems():
                        sheet_vessel.write(self.current_line,0,description,xl_module.line_name)
                        sheet_vessel.write(self.current_line,1,noprod_dict['qty'],xl_module.number)
                        sheet_vessel.write(self.current_line,2,round(noprod_dict['price']),xl_module.number)
                        sheet_vessel.write(self.current_line,3,round(noprod_dict['revenue']),xl_module.number)
                        self.current_line += 1

                        if vessels_total.get(product_id):
                            if vessels_total[product_id].get(description):
                                vessels_total[product_id][description]['qty'] += noprod_dict['qty']
                                vessels_total[product_id][description]['revenue'] += noprod_dict['revenue']
                                vessels_total[product_id][description]['price'] += noprod_dict['price']
                            else:
                                vessels_total[product_id].update({
                                    description : {
                                        'qty': noprod_dict['qty'],
                                        'revenue': noprod_dict['revenue'],
                                        'price': noprod_dict['price'], 
                                        },
                                    })
                        else:
                            vessels_total[product_id] = {
                                description : {
                                    'qty': noprod_dict['qty'],
                                    'revenue': noprod_dict['revenue'],
                                    'price': noprod_dict['price'], 
                                    },
                                }
            self.current_line += 1

        sheet_vessel.write_merge(self.current_line,self.current_line,0,2,'TOTAL',xl_module.bold)
        sheet_vessel.write(self.current_line+1,0,"Product Name",xl_module.line_name)
        sheet_vessel.write(self.current_line+1,1,"Quantity",xl_module.line_name)
        sheet_vessel.write(self.current_line+1,2,"Price",xl_module.line_name)
        sheet_vessel.write(self.current_line+1,3,"Revenue",xl_module.line_name)
        self.current_line += 2


        for product_id, prod_dict in vessels_total.iteritems():
            if product_id:
                sheet_vessel.write(self.current_line,0,prod_mod.browse(cr, uid, product_id, context=context).name,xl_module.line_name)
                sheet_vessel.write(self.current_line,1,prod_dict['qty'],xl_module.number)
                sheet_vessel.write(self.current_line,2,round(prod_dict['price']),xl_module.number)
                sheet_vessel.write(self.current_line,3,round(prod_dict['revenue']),xl_module.number)
                self.current_line += 1
            else: 
                for description, noprod_dict in prod_dict.iteritems():
                    sheet_vessel.write(self.current_line,0,description,xl_module.line_name)
                    sheet_vessel.write(self.current_line,1,noprod_dict['qty'],xl_module.number)
                    sheet_vessel.write(self.current_line,2,round(noprod_dict['price']),xl_module.number)
                    sheet_vessel.write(self.current_line,3,round(noprod_dict['revenue']),xl_module.number)
                    self.current_line += 1

        self.current_line += 1

        # appointment revenue report
        invoice_ids = inv_mod.search(cr, uid, [('date_invoice','>=',date_from),('date_invoice','<=',date_to),('type2','=','appointment')], context=context)
        invoices = inv_mod.browse(cr, uid, invoice_ids, context=context)
        appointments = {}
        for invoice in invoices:
            for line in invoice.invoice_line:
                if line.product_id:
                    if appointments.get(line.product_id.id):
                        appointments[line.product_id.id]['qty'] += line.quantity
                        appointments[line.product_id.id]['revenue'] += line.price_subtotal
                        appointments[line.product_id.id]['price'] = appointments[line.product_id.id]['revenue']/appointments[line.product_id.id]['qty']
                    else: 
                        appointments[line.product_id.id] = {
                            'qty':line.quantity,
                            'revenue': line.price_subtotal,
                            'price': line.price_subtotal/line.quantity, 
                        }
                else:
                    if appointments.get(False) and appointments[False].get(line.name):
                        appointments[False][line.name]['qty'] += line.quantity
                        appointments[False][line.name]['revenue'] += line.price_subtotal
                        appointments[False][line.name]['price'] = appointments[False][line.name]['revenue']/appointments[False][line.name]['qty']
                    elif appointments.get(False) and not appointments[False].get(line.name): 
                        appointments[False].update({
                            line.name: {
                                'qty':line.quantity,
                                'revenue': line.price_subtotal,
                                'price': line.price_subtotal/line.quantity, 
                            },
                        })
                    else :
                        appointments[False] = {
                            line.name: {
                                'qty':line.quantity,
                                'revenue': line.price_subtotal,
                                'price': line.price_subtotal/line.quantity, 
                            },
                        }
        self.current_line = 4
        sheet_appointment.write(self.current_line+1,0,"Product Name",xl_module.line_name)
        sheet_appointment.write(self.current_line+1,1,"Quantity",xl_module.line_name)
        sheet_appointment.write(self.current_line+1,2,"Price",xl_module.line_name)
        sheet_appointment.write(self.current_line+1,3,"Revenue",xl_module.line_name)
        self.current_line += 2
        for product_id, prod_dict in appointments.iteritems():
            if product_id:
                sheet_appointment.write(self.current_line,0,prod_mod.browse(cr, uid, product_id, context=context).name,xl_module.line_name)
                sheet_appointment.write(self.current_line,1,prod_dict['qty'],xl_module.number)
                sheet_appointment.write(self.current_line,2,round(prod_dict['price']),xl_module.number)
                sheet_appointment.write(self.current_line,3,round(prod_dict['revenue']),xl_module.number)
                self.current_line += 1
            else:
                for description, noprod_dict in prod_dict.iteritems():
                    sheet_appointment.write(self.current_line,0,description,xl_module.line_name)
                    sheet_appointment.write(self.current_line,1,noprod_dict['qty'],xl_module.number)
                    sheet_appointment.write(self.current_line,2,round(noprod_dict['price']),xl_module.number)
                    sheet_appointment.write(self.current_line,3,round(noprod_dict['revenue']),xl_module.number)
                    self.current_line += 1
        self.current_line += 1


    def print_report(self, cr, uid, ids, name, context=None):
        if context is None:
            context = {}
        context['date_to'] = self.browse(cr,uid,ids,context=context)[0].date_to
        context['date_from'] = self.browse(cr,uid,ids,context=context)[0].date_from
        self.date_to = datetime.strptime(context['date_to'],'%Y-%m-%d')
        self.date_from = datetime.strptime(context['date_from'],'%Y-%m-%d')
        report = Workbook()
        self.sheet_vessel = report.add_sheet('VESSEL')
        self.sheet_appointment = report.add_sheet('APPOINTMENT')
        self._write_report(cr,uid,ids,context=context)


        f = StringIO.StringIO()
        report.save(f)
        xls_file = base64.b64encode(f.getvalue())
        dlwizard = self.pool.get('lct_finance.file.download').create(cr, uid, {'file' : xls_file, 'file_name' : 'Vessel Revenue Report.xls'}, context=dict(context, active_ids=ids))
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


