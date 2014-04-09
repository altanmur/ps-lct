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

from report import report_sxw
from openerp.modules import get_module_path


base_bath = get_module_path('lct_hr')


class payslip_report_pdf(report_sxw.rml_parse):
    _name = 'payslip_report_pdf'
    _description = "Payslip PDF report"

    def __init__(self, cr, uid, name, context):
        super(payslip_report_pdf, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'payslips': self.get_payslip_data(cr, uid, context=context),
            })

    # Returns only the lines that actually appear on the payslip
    def get_payslip_lines(self, cr, uid, obj, context=None):
        payslip_line = self.pool.get('hr.payslip.line')
        res = []
        ids = []
        for id in range(len(obj)):
            if obj[id].appears_on_payslip == True:
                ids.append(obj[id].id)
        if ids:
            res = payslip_line.browse(cr, uid, ids, context=context)
        return res

    def get_payslip_data(self, cr, uid, context=None):
        retval = {}
        payslip_ids = context.get('active_ids')
        payslips = self.pool.get('hr.payslip').browse(cr, uid, payslip_ids, context=context)
        for payslip in payslips:
            lines = self.get_payslip_lines(cr, uid, payslip.line_ids, context=context)
            sen_yr, sen_mon, sen_day = self.pool.get('hr.employee').get_seniority_ymd(cr, uid, payslip.employee_id.id, context=context)
            seniority = '%dA, %dM, %dJ' % (sen_yr, sen_mon, sen_day)

            gross = sum(x.total for x in lines if x.sequence in [1999])
            salarial_costs = sum(x.total for x in lines if x.sequence in [2040])
            patronal_costs = sum(x.total for x in lines if x.sequence in [2041])
            net_salary = sum(x.total for x in lines if x.sequence in [5000])
            benefits_in_kind = sum(x.total for x in lines if x.sequence in [1009])
            worked_hours = sum([x.number_of_hours for x in payslip.worked_days_line_ids])
            worked_days = sum([x.number_of_days for x in payslip.worked_days_line_ids])

            retval[payslip] = {
                'lines': lines,
                'seniority': seniority,
                'gross': gross,
                'salarial_costs': salarial_costs,
                'patronal_costs': patronal_costs,
                'net_salary': net_salary,
                'benefits_in_kind': benefits_in_kind,
                'worked_hours': worked_hours,
                'worked_days': worked_days,
            }

        return retval

report_sxw.report_sxw('report.webkit.payslip_report_pdf',
                      'hr.payslip',
                      'lct_hr/report/payslip_report.html.mako',
                      parser=payslip_report_pdf)
