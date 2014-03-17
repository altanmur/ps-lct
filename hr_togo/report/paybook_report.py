# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-TODAY OpenERP S.A. <http://www.openerp.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
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

from osv.orm import TransientModel
from osv import fields
from xlwt import Workbook, Font, XFStyle
import base64
import StringIO


# Some constants
header = ["No Mlle", "NOM & PRENOM", "SALAIRE DE BASE", "PRIME D'ANCIENNETE", "SURSALAIRES",
            "HEURES SUPPLEMENTAIRES", "INDEMNITES DE DEPLACEMENT", "INDEMNITES DE REPRESENTATION",
            "INDEMNITE DE SUJETION PARTICULIERE", "INDEMNITE DE RENDEMENT", "AUTRES INDEMNITES",
            "TOTAL SALAIRE BRUT", "CNSS 4%", "IRPP", "TCS", "CNSS 17.5%", "TS 3%", "AVANCE SUR SALAIRES",
            "REMBOURSEMENT DE PRETS", "AUTRES", "SALAIRES NETS"]
mapping = ['basic', 'seniority', 'benefits', 'overtime', 'transportation allowance',
            'representation allowance', 'individual allowance', 'performance allowance',
            'other allowances', 'gross', 'cnss', 'irpp', 'tcs', '', '', 'advance on salary',
            'loan repayments', 'other deductions', 'to pay']


class paybook_report(TransientModel):
    _name = 'paybook_report'
    _description = "Paybook report"

    _columns = {
        'dt_start': fields.date('Start date'),
        'dt_end': fields.date('End date'),
        'xls_file': fields.binary('Report',readonly=True),
        'datas_fname': fields.char('File name', 64),
        'state' : fields.selection([('draft', 'Draft'),('done', 'Done')], string="Status"),
    }

    _defaults = {
        'datas_fname' : 'Livre de Paie.xls',
        'state' : 'draft',
        # 'dt_start': _get_dt_start,
        # 'dt_end': _get_dt_end,
    }

    def export_xls(self, cr, uid, ids, context=None):
        for report in self.browse(cr, uid, ids, context=context):
            dt_start = report.dt_start
            dt_end = report.dt_end + ' 23:59:59'
            args = (dt_start, dt_end)
            query = """
                SELECT employee.reg_nbr, employee.name_related, payslip.id AS payslip_id, line.total, line.name
                FROM hr_payslip AS payslip
                LEFT OUTER JOIN hr_employee AS employee ON payslip.employee_id = employee.id
                LEFT OUTER JOIN hr_payslip_line  AS line ON line.slip_id = payslip.id
                WHERE payslip.date_from >= '%s' AND payslip.date_to <= '%s' AND line.active = 't'
                GROUP BY employee.name_related, employee.reg_nbr, payslip.id, line.total, line.name
                ORDER BY employee.name_related, payslip.date_from
            """ % args
            cr.execute(query)
            row_data = {}
            ordered_ids = []
            for rec in cr.dictfetchall():
                payslip_id = rec['payslip_id']
                if payslip_id not in ordered_ids:
                    ordered_ids.append(payslip_id)
                if payslip_id not in row_data:
                    row_data[payslip_id] = {
                        'reg_nbr': rec['reg_nbr'],
                        'name_related': rec['name_related']
                    }
                row_data[payslip_id].update({rec['name'].lower(): rec['total']})

            xls = Workbook()
            font_bold = Font()
            font_bold.bold = True
            style_bold = XFStyle()
            style_bold.font = font_bold
            sheet1 = xls.add_sheet('Pay book')
            # add header
            sheet1.write(1, 0, 'From %s' % dt_start, style_bold)
            sheet1.write(1, 1, 'To %s' % dt_end.split()[0], style_bold)
            for title in header:
                sheet1.write(2, header.index(title), title)
            row = 3
            for slip_id in ordered_ids:
                raw_data = row_data[slip_id]
                sheet1.write(row, 0, raw_data['reg_nbr'])
                sheet1.write(row, 1, raw_data['name_related'])
                for field in mapping:
                    if 'togo - ' + field in raw_data:
                        sheet1.write(row, mapping.index(field) + 2, raw_data['togo - ' + field])
                sheet1.write(row, 15, raw_data['togo - gross'] * 0.175)
                sheet1.write(row, 16, raw_data['togo - gross'] * 0.03)
                row += 1
            output = StringIO.StringIO()
            xls.save(output)
            encode_text = base64.encodestring(output.getvalue())
            self.write(cr,uid,ids,{'state':'done'},context=context)
            self.write(cr,uid,ids,{'xls_file' : encode_text},context=context)
            return {'type' : 'ir.actions.client', 'tag' : 'reload_dialog',}
