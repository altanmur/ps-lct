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


class hr_contract(osv.osv):
    _inherit = 'hr.contract'

    _columns = {
        'benefits_in_kind': fields.float('Benefits in kind', digits=(16,2)),  # Avantages en nature; maybe calculated from catégorie/classe/échelon?
        'transport_allowance': fields.float('Transport allowance', digits=(16,2)),  # Indemnité de déplacement
        'representation_allowance': fields.float('Representation allowance', digits=(16,2)),  # Indemnité de représentation
        'individual_allowance': fields.float('Individual allowance', digits=(16,2)),  # Indemnité de sujetion particulière
        'performance_allowance': fields.float('Performance allowance', digits=(16,2)),  # Indemnité de rendement == bonus???
        'other_allowances': fields.float('Other allowances', digits=(16,2)),  # Autres indemnités
        'benefits': fields.float('Benefits', digits=(16,2)),  # Sursalaires
        'loan_repayments': fields.float('Loan repayments', digits=(16,2)),  # Remboursement de prêts - doesn't belong here, but placeholding it because I need to figure out how it's calculated
        'other_deductions': fields.float('Other deductions', digits=(16,2)),  # Autres retenues - think this probably goes on the contract, need to verify
    }
