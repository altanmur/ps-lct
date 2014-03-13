from openerp.osv import fields, orm


class hr_payroll_basewage(orm.Model):
    _name = 'hr.payroll.base_wage'
    _description = 'Base wage'

    _columns = {
        'base_wage': fields.float('Base wage', digits=(16, 2), help='Salary for Category 1, class EA, echelon 1'),
    }

    _defaults = {
        'base_wage': 69250,
        }
