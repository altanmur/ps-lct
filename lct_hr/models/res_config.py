# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (C) 2004-2012 OpenERP S.A. (<http://openerp.com>).
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
from openerp import tools

class human_resources_configuration(osv.osv_memory):
    _inherit = 'hr.config.settings'

    _columns = {
        'base_wage': fields.float('Base wage', digits=(16, 2),
            help='Salary for Category 1, class EA, echelon 1'),
        'payslip_signature': fields.binary('Employer signature',
            help="Employer signature used in payroll reports")
    }

    _defaults = {
        'base_wage': lambda self, *args, **kwargs: self.get_base_wage(*args, **kwargs),
        'payslip_signature': lambda self, *args, **kwargs: self.get_payslip_signature(*args, **kwargs),
    }

    def get_base_wage(self, cr, uid, ids, context=None):
        wage = self.pool.get('ir.config_parameter')\
            .get_param(cr, uid, 'lct_hr.base_wage', default='69250', context=context)
        return float(wage)

    def set_base_wage(self, cr, uid, ids, context=None):
        wage = self.browse(cr, uid, ids[0], context=context).base_wage
        self.pool.get('ir.config_parameter').set_param(cr, uid, 'lct_hr.base_wage', str(wage))

    def get_payslip_signature(self, cr, uid, ids, context=None):
        """ returns lower resolution image for widget to limit place usage """
        signature = self.get_payslip_signature_big(cr, uid, ids, context=context)
        signature = tools.image_resize_image_medium(signature, avoid_if_small=True)
        return signature

    def get_payslip_signature_big(self, cr, uid, ids, context=None):
        """ returns high resolution image for printing """
        signature = self.pool.get('ir.config_parameter')\
            .get_param(cr, uid, 'lct_hr.payslip_signature', default=None, context=context)
        if not signature:
            signature = self.pool.get('res.company').read(cr, uid, 1, ['logo'], context=context).get('logo')
        return signature

    def set_payslip_signature(self, cr, uid, ids, context=None):
        signature = self.browse(cr, uid, ids[0], context=context).payslip_signature
        self.pool.get('ir.config_parameter').set_param(cr, uid,
                                    'lct_hr.payslip_signature', signature)
