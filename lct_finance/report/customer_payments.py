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

import time
from openerp.report import report_sxw
from openerp.tools.amount_to_text import french_number
import re

# Lifted from openerp/tools/amount_to_text to get rid of the cents, which aren't
# used in CFA.

def amount_to_text_fr(number, currency):
    number = '%.2f' % number
    units_name = currency
    list = str(number).split('.')
    start_word = french_number(abs(int(list[0])))
    final_result = start_word +' '+units_name
    final_result = re.sub('un Mil', 'Mil', final_result)
    final_result = re.sub('un Cent', 'Cent', final_result)
    final_result = re.sub(',', '', final_result)
    return final_result


class customer_payment(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(customer_payment, self).__init__(cr, uid, name, context)
        self.number_lines = 0
        self.number_add = 0
        self.localcontext.update({
            'time': time,
            'amount_to_text_fr': amount_to_text_fr,
            'fac_nbr': self.get_fac_nbr,
        })

    def get_fac_nbr(self, voucher):
        for line in voucher.line_cr_ids:
            if line.reconcile:
                return line.name
        return '---'



report_sxw.report_sxw(
    'report.lct_finance.customer_payments',
    'account.voucher',
    'addons/lct_finance/report/customer_payments.rml',
    parser=customer_payment,header=False
)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
