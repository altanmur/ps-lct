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

class account_voucher(osv.osv):
    _inherit = 'account.voucher'

    _columns = {
        'origin_bank_id': fields.many2one('res.partner.bank', 'Origin bank account'),
        'internal_transfer': fields.boolean('Internal transfer'),
        'destination_bank_id': fields.many2one('res.partner.bank', 'Destination bank account'),
        'pos1_id': fields.many2one('auth_signature_position', 'Position 1'),
        'pos2_id': fields.many2one('auth_signature_position', 'Position 2'),
        'signee1_id': fields.many2one('res.partner', 'Signee 1'),
        'signee2_id': fields.many2one('res.partner', 'Signee 2'),
    }

    # account.voucher => account.voucher.line => account.move.line => invoice
    def get_invoice(self, cr, uid, ids, context=None):
        retval = None
        if isinstance(ids, list):
            ids = ids[0]
        voucher = self.browse(cr, uid, ids, context=context)
        if voucher and voucher.line_dr_ids:
            retval = voucher.line_dr_ids[0].move_line_id.invoice
        return retval
