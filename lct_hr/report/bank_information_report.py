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


class bank_information_report_pdf(report_sxw.rml_parse):
    _name = 'bank_information_report_pdf'
    _description = "Staff Bank Information report"

    def __init__(self, cr, uid, name, context):
        super(bank_information_report_pdf, self).__init__(cr, uid, name, context=context)
        payslips, total_net = self.get_payslip_data(cr, uid, context=context)
        self.localcontext.update({
            'payslips': payslips,
            'total_net': total_net,
            })

    def get_payslip_data(self, cr, uid, context=None):
        retval = {}
        payslip_ids = []
        slip_run_ids = context.get('active_ids')
        slip_runs = self.pool.get('hr.payslip.run').browse(cr, uid, slip_run_ids, context=context)
        payslip_obj = self.pool.get('hr.payslip')
        for run in slip_runs:
            payslip_ids.extend([x.id for x in run.slip_ids])
        payslips = payslip_obj.browse(cr, uid, payslip_ids, context=context)
        net_total = 0
        for payslip in payslips:
            lines = payslip_obj.get_visible_lines(cr, uid, payslip.id, context=context)
            net_salary = sum(x.total for x in lines if x.sequence in [5000])
            net_total += net_salary
            retval[payslip] = {
                'net_salary': net_salary,
            }

        return (retval, net_total)

report_sxw.report_sxw('report.webkit.bank_information_report_pdf',
                      'hr.payslip',
                      'lct_hr/report/payslip_report.html.mako',
                      parser=bank_information_report_pdf)
