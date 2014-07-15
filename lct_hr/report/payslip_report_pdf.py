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
from datetime import datetime


class payslip_report_pdf(report_sxw.rml_parse):
    _name = 'payslip_report_pdf'
    _description = "Employee Payslips"

    def __init__(self, cr, uid, name, context):
        super(payslip_report_pdf, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'payslips': self.get_payslip_data(cr, uid, context=context),
            })

    # Not sure how well this will perform on big data sets. The yearly stuff is
    # duplicating a ton of lookups. If it turns out this performs badly, rewrite
    # to use queries instead of ORM.
    def get_payslip_data(self, cr, uid, context=None):
        retval = {}
        payslip_obj = self.pool.get('hr.payslip')
        payslip_ids = context.get('active_ids')
        payslips = payslip_obj.browse(cr, uid, payslip_ids, context=context)
        for payslip in payslips:
            sen_yr, sen_mon, sen_day = self.pool.get('hr.employee')\
                .get_seniority_ymd(cr, uid, payslip.employee_id.id, context=context)
            seniority = '%dA, %dM, %dJ' % (sen_yr, sen_mon, sen_day)

            # Leaves
            leave_obj = self.pool.get('hr.holidays')
            leave_ids = leave_obj.search(cr, uid,
                [('employee_id', '=', payslip.employee_id.id)], context=context)
            leaves = leave_obj.browse(cr, uid, leave_ids, context=context)
            leaves_acquired = sum([x.number_of_days for x in leaves \
                if x.state == 'validate' \
                and x.type == 'add'\
                and x.holiday_status_id.limit == False]) or 0.0
            holidays = [x for x in leaves \
                if x.state == 'validate' \
                and x.type == 'remove' \
                and x.date_from.split()[0] >= payslip.date_from.split()[0] \
                and x.date_to.split()[0] <= payslip.date_to.split()[0]]
            # leaves_taken = sum([x.number_of_days for x in leaves \
            #     if x.state == 'validate' \
            #     and x.type == 'remove'\
            #     and x.holiday_status_id.limit == False])
            leaves_remaining = sum([x.number_of_days for x in leaves\
                if x.state == 'validate' \
                and x.holiday_status_id.limit == False]) or 0.0


            retval[payslip] = {
                # 'lines': lines,
                'seniority': seniority,
                'leaves_acquired': leaves_acquired,
                # 'leaves_taken': leaves_taken,
                'leaves_remaining': leaves_remaining,
                'holidays': holidays,
            }
            retval[payslip].update(self.get_salarial_data(cr, uid, payslip,
                yearly=False, context=context))
            # Yearly stuff
            jan_1 = payslip.date_from.split('-')[0] + '-01-01'
            slip_end = payslip.date_to.split()[0]
            yr_slip_ids = payslip_obj.search(cr, uid,
                [('employee_id', '=', payslip.employee_id.id),
                ('date_from', '>=', jan_1),
                ('date_to', '<=', slip_end)], context=context)
            yearly_data = dict.fromkeys(['gross_year',
                'salarial_costs_year',
                'patronal_costs_year',
                'net_salary_year',
                'benefits_in_kind_year',
                'worked_hours_year',
                'worked_days_year'], 0)
            for yr_slip in payslip_obj.browse(cr, uid, yr_slip_ids, context=context):
                data = self.get_salarial_data(cr, uid, yr_slip, yearly=True,
                    context=context)
                for key in data.keys():
                    yearly_data[key] += data.get(key, 0)
            retval[payslip].update(yearly_data)

        return retval

    def get_salarial_data(self, cr, uid, payslip, yearly=False, context=None):
        retval = {}
        keys = ['gross', 'salarial_costs', 'patronal_costs',
                'net_salary', 'benefits_in_kind', 'worked_hours', 'worked_days']
        lines = payslip.get_visible_lines(context=context)
        gross = sum(x.total for x in lines if x.sequence in [1999])
        salarial_costs = sum(x.total for x in lines if x.sequence in [2040])
        patronal_costs = sum(x.total for x in lines if x.sequence in [2041])
        net_salary = sum(x.total for x in lines if x.sequence in [5000])
        benefits_in_kind = sum(x.total for x in lines if x.sequence in [1009])
        # For now, it's 160, except the 1st month, when it's prorata.
        days_in_service = (datetime.strptime(payslip.date_to, '%Y-%m-%d') \
            - datetime.strptime(payslip.employee_id.start_date, '%Y-%m-%d')).days
        days_in_month = (datetime.strptime(payslip.date_to, '%Y-%m-%d') \
            - datetime.strptime(payslip.date_from, '%Y-%m-%d')).days
        worked_hours = int(160 * min(1, float(days_in_service) / days_in_month))
        # worked_hours = sum([x.number_of_hours for x in payslip.worked_days_line_ids])
        worked_days = sum([x.number_of_days for x in payslip.worked_days_line_ids])
        if not yearly:
            retval['lines'] = lines
            for key in keys:
                retval[key] = locals().get(key)
        else:
            for key in keys:
                retval[key + '_year'] = locals().get(key)
        return retval


report_sxw.report_sxw('report.webkit.payslip_report_pdf',
                      'hr.payslip',
                      'lct_hr/report/payslip_report.html.mako',
                      parser=payslip_report_pdf)
