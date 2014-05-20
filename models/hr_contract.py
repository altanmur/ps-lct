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
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

# Constants for LCT
class_mult = {
    'EA': [1, 1.05],
    'EB': [1.28, 1.05],
    'EC': [1.28**2, 1.05],
    'ED': [1.28**3, 1.05],
    'ME': [1.28**3*1.3, 1.055],
    'MF': [1.28**3*1.3**2, 1.055],
    'MG': [1.28**3*1.3**3, 1.055],
    'CH': [1.28**3*1.3**4, 1.055],
    'CI': [1.28**3*1.3**5, 1.055],
    'HC': [1.28**3*1.3**5*1.8, 1.055],
}

class_cat = {
            'EA': '1',
            'EB': '1',
            'EC': '1',
            'ED': '1',
            'ME': '2',
            'MF': '2',
            'MG': '2',
            'CH': '3',
            'CI': '3',
            'HC': 'Hors Cat.',
            }


class hr_contract(osv.osv):
    _inherit = 'hr.contract'

    _columns = {
        'benefits_in_kind': fields.float('Benefits in kind', digits=(16,2)),
        'transport_allowance': fields.float('Transport allowance', digits=(16,2)),
        'representation_allowance': fields.float('Representation allowance', digits=(16,2)),
        'individual_allowance': fields.float('Individual allowance', digits=(16,2)),
        'performance_allowance': fields.float('Performance allowance', digits=(16,2)),
        'other_allowances': fields.float('Other allowances', digits=(16,2)),
        'bonus': fields.float('Bonus', digits=(16,2)),
        'pension_annuities': fields.float('Pension or annuities', digits=(16,2)),
        'life_insurance': fields.float('Life insurance', digits=(16,2)),
        'category': fields.function(lambda self, *args, **kwargs: self._get_category(*args, **kwargs),
                                 method=True,
                                 type='char',
                                 string='Category',
                                 store=True),
        'hr_class': fields.selection([
            ('EA','EA'),
            ('EB','EB'),
            ('EC','EC'),
            ('ED','ED'),
            ('ME','ME'),
            ('MF','MF'),
            ('MG','MG'),
            ('CH','CH'),
            ('CI','CI'),
            ('HC','HC'),
            ], 'Class', select=True),
        'echelon': fields.selection([
            ('1','1'),
            ('2','2'),
            ('3','3'),
            ('4','4'),
            ('5','5'),
            ('6','6'),
            ('7','7'),
            ('8','8'),
            ('9','9'),
            ('10','10'),
            ('11','11'),
            ('12','12'),
            ('13','13'),
            ('14','14'),
            ('15','15'),
            ], 'Echelon', select=True),
        # Override; this one's calculated based on class and echelon
        'wage': fields.function(lambda self, *args, **kwargs: \
            self._calculate_wage(*args, **kwargs),
                                 method=True,
                                 type='float',
                                 string='Wage',
                                 store=True),
        'date_next_promotion': fields.date('Next promotion'),
    }

    _defaults = {
        # 'category': '1',
        'hr_class': 'EA',
        'echelon': '1',
        'date_next_promotion': lambda *a: \
            (date.today() + relativedelta(years=2)).strftime('%Y-%m-%d'),
    }

    _sql_constraints = [
        ('employee_id_uniq', 'unique(employee_id)',
            'You can only have one contract per employee.'),
    ]

    def _calculate_wage(self, cr, uid, ids, field_name, args, context=None):
        res = dict.fromkeys(ids, 0.0)
        base_wage = float(self.pool.get('ir.config_parameter').get_param(cr, uid, 'lct_hr.base_wage', default='69250', context=context))
        for contract_id in ids:
            contract_data = self.read(cr, uid, contract_id, ['hr_class', 'echelon'], context)
            hr_class, hr_echelon = contract_data['hr_class'] or 'EA', contract_data['echelon'] or '1'
            wage = base_wage * class_mult[hr_class][0] * class_mult[hr_class][1] ** (int(hr_echelon) - 1)
            res.update({contract_id: wage})
        return res

    def _get_category(self, cr, uid, ids, field_name, args, context=None):
        res = dict.fromkeys(ids, False)
        for contract_id in ids:
            hr_class = self.read(cr, uid, contract_id, ['hr_class'], context)['hr_class'] or 'EA'
            res.update({contract_id: class_cat[hr_class]})
        return res

    def auto_promote(self, cr, uid, force_run=False):
        active_contract_ids = self.search(cr, uid, [
            '|',
            ('date_end', '>', date.today().strftime('%Y-%m-%d')),
            ('date_end', '=', False)])
        active_contracts = self.browse(cr, uid, active_contract_ids)
        write_vals = {}
        for contract in active_contracts:
            employee = contract.employee_id
            # First, promote echelon if necessary
            echelon = contract.echelon
            date_next_promotion = datetime.strptime(contract.date_next_promotion, '%Y-%m-%d').date()
            if date.today() >= date_next_promotion:
                # Sigh, why did I store this as a string intead of int?
                echelon = str(min(int(echelon) + 1, 15))
                self.write(cr, uid, contract.id, {
                    'echelon': echelon,
                    'date_next_promotion': (date.today() + relativedelta(years=2)).strftime('%Y-%m-%d')})
            # Then update seniority, if applicable
            employee_start = datetime.strptime(employee.start_date, '%Y-%m-%d').date()
            seniority_pay = employee.seniority_pay
            if relativedelta(date.today(), employee_start).years > employee.active_years:
                active_years = employee.active_years + 1
                if active_years == 2:
                    wage = self._calculate_wage(cr, uid, [contract.id], field_name=None, args=None)[contract.id]
                    seniority_pay = wage * 0.02
                elif active_years > 2:
                    wage = self._calculate_wage(cr, uid, [contract.id], field_name=None, args=None)[contract.id]
                    seniority_pay = employee.seniority_pay + wage * 0.01
                write_vals.update({
                    'active_years': active_years,
                    'seniority_pay': seniority_pay,
                })
                self.pool.get('hr.employee').write(cr, uid, contract.employee_id.id, write_vals)
