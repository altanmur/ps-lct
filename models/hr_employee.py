# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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
# import time

from openerp.osv import fields, osv
from datetime import datetime
from dateutil.relativedelta import relativedelta


class hr_employee(osv.osv):
    _inherit = 'hr.employee'

    _columns = {
        'nbr_dependents': fields.integer('Number of dependents'),
        'start_date': fields.date('Start date', required=True),
        'mortgage_interests': fields.float('Interests on mortgage(s)', digits=(16,2)),
        'advance_on_salary': fields.float('Advance on salary', digits=(16,2)),
        'loan_repayments': fields.float('Loan repayments', digits=(16,2)),
        'overtime': fields.float('Overtime', digits=(16,2), help="Expressed in monetary terms, not hours"),
        'other_deductions': fields.float('Other deductions', digits=(16,2)),
        'pension_allowance': fields.float('Pension allowance', digits=(16,2)),
        'reg_nbr': fields.char('Registration number', size=64),
        'cnss_nbr': fields.char('CNSS Number', size=64),
        'active_years': fields.integer('Active years', readonly=True),
        'seniority_pay': fields.float('Seniority pay', digits=(16,2), readonly=True),
        # For functional reasons, specific to LCT.
        'bank_name': fields.char('Bank name', required=True),
        'acc_number': fields.char('Account number', required=True),
    }

    _defaults = {
        'start_date': datetime.today().strftime('%Y-%m-%d')
    }

    _sql_constraints = [
        ('unique_reg_nbr', 'unique(reg_nbr)', 'An employee with the same registration number already exists.'),
        ('unique_cnss_nbr', 'unique(cnss_nbr)', 'An employee with the same CNSS number already exists.'),
    ]

    def get_seniority_ymd(self, cr, uid, ids, context=None):
        if isinstance(ids, list):
            ids = ids[0]
        emp = self.browse(cr, uid, ids, context=context)
        if emp:
            start_date = datetime.strptime(emp.start_date, '%Y-%m-%d')
            delta = relativedelta(datetime.today(), start_date)
            return(delta.years, delta.months, delta.days)
        return (0, 0, 0)
