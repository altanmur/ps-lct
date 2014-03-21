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
        'benefits_in_kind': fields.float('Benefits in kind', digits=(16,2)),  # Avantages en nature; maybe calculated from catégorie/classe/échelon?
        'transport_allowance': fields.float('Transport allowance', digits=(16,2)),  # Indemnité de déplacement
        'representation_allowance': fields.float('Representation allowance', digits=(16,2)),  # Indemnité de représentation
        'individual_allowance': fields.float('Individual allowance', digits=(16,2)),  # Indemnité de sujetion particulière
        'performance_allowance': fields.float('Performance allowance', digits=(16,2)),  # Indemnité de rendement == bonus???
        'other_allowances': fields.float('Other allowances', digits=(16,2)),  # Autres indemnités
        'bonus': fields.float('Bonus', digits=(16,2)),  # Sursalaires
        'pension_annuities': fields.float('Pension or annuities', digits=(16,2)),
        'life_insurance': fields.float('Life insurance', digits=(16,2)),
        # 'category': fields.selection([
        #     ('1','1'),
        #     ('2','2'),
        #     ('3','3'),
        #     ], 'Category', select=True),
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
        'wage': fields.function(lambda self, *args, **kwargs: self._calculate_wage(*args, **kwargs),
                                 method=True,
                                 type='float',
                                 string='Wage',
                                 store=True),
    }

    _defaults = {
        # 'category': '1',
        'hr_class': 'EA',
        'echelon': '1',
        }

    def _calculate_wage(self, cr, uid, ids, field_name, args, context=None):
        res = dict.fromkeys(ids, 0.0)
        config = self.pool.get('hr.payroll.base_wage')
        conf_ids = config.search(cr, uid, [('base_wage','>',0)], context=context)
        base_wage = config.browse(cr, uid, conf_ids[0], context=context).base_wage
        for contract_id in ids:
            contract_data = self.read(cr, uid, contract_id, ['hr_class', 'echelon'], context)
            hr_class, hr_echelon = contract_data['hr_class'] or 'EA', contract_data['echelon'] or '1'
            wage = base_wage * class_mult[hr_class][0] * class_mult[hr_class][1] ** (int(hr_echelon) - 1)
            res.update({contract_id: wage})
        return res

    def get_cat(self, hr_class):
        return class_cat[hr_class].decode('utf-8') or '-'
