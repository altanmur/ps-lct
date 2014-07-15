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
from xlwt import Workbook, easyxf
import base64
import StringIO
from datetime import date
from dateutil.relativedelta import relativedelta


# Some constants
# Yes, hardcoding this one in French; sorry.
header = ["No Mlle", "NOM & PRENOM", "SALAIRE DE BASE", "PRIME D'ANCIENNETE", "SURSALAIRES",
            "HEURES SUPPLEMENTAIRES", "INDEMNITES DE DEPLACEMENT", "INDEMNITES DE REPRESENTATION",
            "INDEMNITE DE SUJETION PARTICULIERE", "INDEMNITE DE RENDEMENT", "AUTRES INDEMNITES",
            "TOTAL SALAIRE BRUT", "CNSS 4%", "IRPP", "TCS", "CNSS 17.5%", "TS 3%", "AVANCE SUR SALAIRES",
            "REMBOURSEMENT DE PRETS", "AUTRES", "SALAIRES NETS"]
mapping = ['basic', 'seniority premium', 'benefits in kind', 'overtime', 'transportation allowance',
            'representation allowance', 'individual allowance', 'performance allowance',
            'other allowances', 'gross', 'employee cnss', 'irpp', 'tcs', 'employer cnss', 'tax on salary', 'advance on salary',
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
        'dt_start': lambda self, *args, **kwargs: self._get_dt_start(*args, **kwargs),
        'dt_end': lambda self, *args, **kwargs: self._get_dt_end(*args, **kwargs),
    }

    def _get_dt_start(self, cr, uid, context=None):
        today = date.today().replace(day=1)
        return today.strftime("%Y-%m-%d")

    def _get_dt_end(self, cr, uid, context=None):
        end_of_month = (date.today() + relativedelta(months=1)).replace(day=1)
        return end_of_month.strftime("%Y-%m-%d")

    def export_xls(self, cr, uid, ids, context=None):
        for report in self.browse(cr, uid, ids, context=context):
            data_start_row = 5
            dt_start = report.dt_start
            dt_end = report.dt_end
            args = (dt_start, dt_end)
            query = """
                SELECT employee.reg_nbr, employee.name_related, payslip.id AS payslip_id, line.total, rule.name
                FROM hr_payslip AS payslip
                LEFT OUTER JOIN hr_employee AS employee ON payslip.employee_id = employee.id
                LEFT OUTER JOIN hr_payslip_line  AS line ON line.slip_id = payslip.id
                LEFT OUTER JOIN hr_salary_rule AS rule ON line.salary_rule_id = rule.id
                WHERE payslip.date_from >= '%s' AND payslip.date_to <= '%s' AND line.active = 't'
                GROUP BY employee.name_related, employee.reg_nbr, payslip.id, line.total, rule.name
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
            style_default = easyxf('border: left thin, right thin', num_format_str='#,##0')
            style_gray = easyxf('pattern: pattern solid, fore_color grey25;'
                ' border: top thin, bottom thin, left thin, right thin', num_format_str='#,##0')
            style_bold_center = easyxf('font: bold on; align: horiz center')
            style_bold_center_gray = easyxf('font: bold on; align: horiz center, vert top;'
                ' pattern: pattern solid, fore_color grey25; border: top thin, bottom thin, left thin, right thin')
            style_center_wrap = easyxf('align: wrap on, horiz center')
            style_center_gray = easyxf('align: wrap on, horiz center; pattern: pattern solid, fore_color grey25;'
                ' border: top thin, bottom thin, left thin, right thin')
            sheet1 = xls.add_sheet('Livre de paie')
            for i in range(21):
                sheet1.col(i).width = 256*20
            sheet1.row(4).height = 720
            # add header
            sheet1.write_merge(0, 0, 0, 19, u'ETAT COLLECTIF DES SALAIRES', style_bold_center)
            sheet1.write_merge(1, 1, 0, 19, u'LIVRE DE PAIE, DU %s AU %s' % (dt_start, dt_end), style_center_wrap)
            sheet1.write_merge(2, 2, 12, 16, u'RETENUES SUR SALAIRES', style_bold_center_gray)
            sheet1.write_merge(2, 3, 17, 19, u'AUTRES RETENUES', style_bold_center_gray)
            sheet1.write_merge(3, 3, 12, 14, u'PART SALARIALE', style_bold_center_gray)
            sheet1.write_merge(3, 3, 15, 16, u'PART PATRONALE', style_bold_center_gray)
            for title in header:
                sheet1.write(4, header.index(title), title, style_center_gray)
            row = data_start_row
            totals = [0] * len(mapping)
            for slip_id in ordered_ids:
                raw_data = row_data[slip_id]
                # TODO: these need to become rules on the payslip and just taken from there.
                sheet1.write(row, 0, raw_data['reg_nbr'])
                sheet1.write(row, 1, raw_data['name_related'])
                for field in mapping:
                    if field in raw_data:
                        sheet1.write(row, mapping.index(field) + 2, raw_data[field], style_default)
                        totals[mapping.index(field)] += raw_data[field]
                row += 1
            sheet1.write_merge(row, row, 0, 1, u'Total:', style_center_gray)
            for idx, val in enumerate(totals):
                sheet1.write(row, idx + 2, val, style_gray)
            output = StringIO.StringIO()
            xls.save(output)
            encode_text = base64.encodestring(output.getvalue())
            self.write(cr,uid,ids,{'state':'done'},context=context)
            self.write(cr,uid,ids,{'xls_file' : encode_text},context=context)
            return {'type' : 'ir.actions.client', 'tag' : 'reload_dialog',}
