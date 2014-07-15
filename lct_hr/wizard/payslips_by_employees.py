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

from openerp.osv import fields, osv


class hr_payslip_employees(osv.osv_memory):

    _inherit ='hr.payslip.employees'

    _columns = {
        'select_all_active_employees': fields.boolean('Generate for all active employees'),
    }

    _defaults = {
        'select_all_active_employees': True,
    }

    def compute_sheet(self, cr, uid, ids, context=None):
        data = self.read(cr, uid, ids, context=context)[0]
        if data['select_all_active_employees']:
            employee_ids = self.pool.get('hr.employee').search(cr, uid, [('active','=',True)])
            employee_ids_m2m = [(6, 0, employee_ids)]
            self.write(cr, uid, ids, {'employee_ids': employee_ids_m2m}, context=context)
        return super(hr_payslip_employees, self).compute_sheet(cr, uid, ids, context=context)
