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
from datetime import date
from dateutil.relativedelta import relativedelta


class payslip_report(TransientModel):
    _name = 'payslip_report'
    _description = "Payslip report"

    _columns = {
        'export_selected_only': fields.boolean('Export selected payslips only'),
        'dt_start': fields.date('Start date'),
        'dt_end': fields.date('End date'),
    }

    _defaults = {
        'export_selected_only': True,
        'dt_start': lambda self, *args, **kwargs: self._get_dt_start(*args, **kwargs),
        'dt_end': lambda self, *args, **kwargs: self._get_dt_end(*args, **kwargs),
    }

    def _get_dt_start(self, cr, uid, context=None):
        today = date.today().replace(day=1)
        return today.strftime("%Y-%m-%d")

    def _get_dt_end(self, cr, uid, context=None):
        end_of_month = (date.today() + relativedelta(months=1)).replace(day=1)
        return end_of_month.strftime("%Y-%m-%d")

    def print_report(self, cr, uid, ids, context=None):
        for report in self.browse(cr, uid, ids, context=context):
            payslip_ids = []
            if report.export_selected_only:
                payslip_ids = context.get('active_ids')
            else:
                payslip_ids = self.pool.get('hr.payslip').search(cr, uid,
                    [('date_from', '>=', report.dt_start),
                    ('date_to', '<=', report.dt_end)], context=context)
            context.update({'active_ids': payslip_ids})
            return {
                'type': 'ir.actions.report.xml',
                'report_name': 'webkit.payslip_report_pdf',
                'context': context,
            }
