
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
from xlwt import Workbook
import StringIO
import base64
from datetime import date, datetime
from openerp.addons.lct_finance.wizard import xl_module

class vessel_revenue(osv.osv_memory):
    _name = "lct_finance.vessel.revenue.report"

    _columns = {
        "date_from" : fields.date(string='From', required=True),
        "date_to" : fields.date(string='To', required=True),
    }

    _defaults = {
        "date_to" : date.today().strftime('%Y-%m-%d'),
        "date_from": date.today().strftime('%Y-01-01'),
    }

    def _get_vessel_data(self, cr, uid, date_from, date_to, context=None):
        vessels = {}
        vessels_total = {}
        invoice_ids = self.pool.get('account.invoice').search(cr, uid, [('date_invoice', '>=', date_from), ('date_invoice', '<=', date_to), ('type2', '=', 'vessel')], context=context)
        invoices = self.pool.get('account.invoice').browse(cr, uid, invoice_ids, context=context)
        for invoice in invoices:
            partner_id = invoice.partner_id.id
            vessels.setdefault(partner_id, {})
            for line in invoice.invoice_line:
                product_id = line.product_id and line.product_id.id or line.description
                vessels[partner_id].setdefault(product_id, {'qty': 0.0, 'revenue': 0.0})
                vessels[partner_id][product_id]['qty'] += line.quantity
                vessels[partner_id][product_id]['revenue'] += line.price_subtotal
                vessels_total.setdefault(product_id, {'qty': 0.0, 'revenue': 0.0})
                vessels_total[product_id]['qty'] += line.quantity
                vessels_total[product_id]['revenue'] += line.price_subtotal

        for product_dict in vessels_total.itervalues():
            product_dict['price'] = product_dict['revenue'] / product_dict['qty']

        for partner_dict in vessels.itervalues():
            for product_dict in partner_dict.itervalues():
                product_dict['price'] = product_dict['revenue'] / product_dict['qty']

        return vessels, vessels_total

    def _get_appointment_data(self, cr, uid, date_from, date_to, context=None):
        appointments = {}
        invoice_ids = self.pool.get('account.invoice').search(cr, uid, [('date_invoice', '>=', date_from), ('date_invoice', '<=', date_to), ('type2', '=', 'appointment')], context=context)
        invoices = self.pool.get('account.invoice').browse(cr, uid, invoice_ids, context=context)
        for invoice in invoices:
            for line in invoice.invoice_line:
                product_id = line.product_id and line.product_id.id or line.description
                appointments.setdefault(product_id, {'qty': 0.0, 'revenue': 0.0})
                appointments[product_id]['qty'] += line.quantity
                appointments[product_id]['revenue'] += line.price_subtotal

        for product_dict in appointments.itervalues():
            product_dict['price'] = product_dict['revenue'] / product_dict['qty']

        return appointments

    def _write_products_dict(self, cr, uid, products_dict, sheet, line_start, context=None):
        current_line = line_start
        product_model = self.pool.get('product.product')

        sheet.write(current_line + 1, 0, "Product Name", xl_module.line_name)
        sheet.write(current_line + 1, 1, "Quantity", xl_module.line_name)
        sheet.write(current_line + 1, 2, "Price", xl_module.line_name)
        sheet.write(current_line + 1, 3, "Revenue", xl_module.line_name)
        current_line += 2
        for product_id, prod_dict in products_dict.iteritems():
            if isinstance(product_id, int):
                product_name = product_model.browse(cr, uid, product_id, context=context).name
            else:
                product_name = product_id
            sheet.write(current_line, 0, product_name, xl_module.line_name)
            sheet.write(current_line, 1, prod_dict['qty'], xl_module.number)
            sheet.write(current_line, 2, round(prod_dict['price']), xl_module.number)
            sheet.write(current_line, 3, round(prod_dict['revenue']), xl_module.number)
            current_line += 1
        return current_line + 1

    def _write_vessel_sheet(self, cr, uid, ids, wb, context=None):
        partner_model = self.pool.get('res.partner')
        product_model = self.pool.get('product.product')

        sheet = wb.add_sheet('VESSEL')
        current_line = 0

        # Date
        wizard = self.browse(cr, uid, ids, context=context)[0]
        date_from = wizard.date_from
        date_to = wizard.date_to
        format_date_from = datetime.strptime(date_from, '%Y-%m-%d').strftime("%d/%m/%Y")
        format_date_to = datetime.strptime(date_to, '%Y-%m-%d').strftime("%d/%m/%Y")

        # Column width + row height
        sheet.col(0).width = 10000
        sheet.col(1).width = 3000
        sheet.col(2).width = 3000
        sheet.col(3).width = 3000

        # Titles
        sheet.write_merge(0, 0, 0, 3, 'VESSEL REVENUE REPORT', xl_module.title3)
        sheet.write(2, 0, "FROM", xl_module.normal)
        sheet.write(2, 1, format_date_from, xl_module.normal)
        sheet.write(2, 2, "TO", xl_module.normal)
        sheet.write(2, 3, format_date_to, xl_module.normal)
        current_line = 4

        vessels, vessels_total = self._get_vessel_data(cr, uid, date_from, date_to, context=context)
        for partner_id, products_dict in vessels.iteritems():
            partner_name = partner_model.browse(cr, uid, partner_id, context=context).name
            sheet.write_merge(current_line, current_line, 0, 2, partner_name, xl_module.bold)
            current_line = self._write_products_dict(cr, uid, products_dict, sheet, current_line, context=context)

        sheet.write_merge(current_line, current_line, 0, 2, 'TOTAL', xl_module.bold)
        self._write_products_dict(cr, uid, vessels_total, sheet, current_line + 1, context=context)

    def _write_appointment_sheet(self, cr, uid, ids, wb, context=None):
        sheet = wb.add_sheet('APPOINTMENT')
        current_line = 0

        # Date
        wizard = self.browse(cr, uid, ids, context=context)[0]
        date_from = wizard.date_from
        date_to = wizard.date_to
        format_date_from = datetime.strptime(date_from, '%Y-%m-%d').strftime("%d/%m/%Y")
        format_date_to = datetime.strptime(date_to, '%Y-%m-%d').strftime("%d/%m/%Y")

        # Column width + row height
        sheet.col(0).width = 10000
        sheet.col(1).width = 3000
        sheet.col(2).width = 3000
        sheet.col(3).width = 3000

        # Titles
        sheet.write_merge(0, 0, 0, 3, 'APPOINTMENT REVENUE REPORT', xl_module.title3)
        sheet.write(2, 0, "FROM", xl_module.normal)
        sheet.write(2, 1, format_date_from, xl_module.normal)
        sheet.write(2, 2, "TO", xl_module.normal)
        sheet.write(2, 3, format_date_to, xl_module.normal)
        current_line = 4

        appointments = self._get_appointment_data(cr, uid, date_from, date_to, context=context)
        self._write_products_dict(cr, uid, appointments, sheet, current_line, context=context)

    def _write_report(self, cr, uid, ids, wb, context=None):
        wizard = self.browse(cr, uid, ids, context=context)[0]
        self._write_vessel_sheet(cr, uid, ids, wb, context=context)
        self._write_appointment_sheet(cr, uid, ids, wb, context=context)

    def print_report(self, cr, uid, ids, name, context=None):
        if context is None:
            context = {}
        wizard = self.browse(cr, uid, ids[0], context=context)

        report = Workbook()
        self._write_report(cr, uid, ids, report, context=context)

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
