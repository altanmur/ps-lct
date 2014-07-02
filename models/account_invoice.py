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

from openerp.osv import fields, orm


class account_invoice(orm.Model):
    _inherit = 'account.invoice'

    _columns = {
        'bank': fields.char('Bank', size=64),
        'bank_bic': fields.char('Swift', size=64),
        'iban': fields.char('IBAN', size=64),
        'bank_code': fields.char('Bank Code', size=64),
        'counter_code': fields.char('Counter Code', size=64),
        'acc_number': fields.char('Account Number', size=64),
        'rib': fields.char('RIB', size=64),
        'customer_nbr': fields.char('Customer Number', size=64),
        'reference' : fields.text('Reference'),
        # For the invoice report (fiche d'imputation)
        'create_date': fields.datetime('Creation Date' , readonly=True),
    }
