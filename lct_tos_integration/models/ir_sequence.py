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

class ir_sequence(osv.osv):
    _inherit = "ir.sequence"

    def get_next_by_xml_id(self, cr, uid, module, xml_id, context=None):
        ir_model_data_model = self.pool.get('ir.model.data')
        mdid = ir_model_data_model._get_id(cr, uid, module, xml_id)
        sequence_id = ir_model_data_model.read(cr, uid, [mdid], ['res_id'])[0]['res_id']
        sequence_obj = self.browse(cr, uid, sequence_id, context=context)
        sequence = self.next_by_id(cr, uid, sequence_id, context=context)
        if int(sequence) >= 10**(sequence_obj.padding):
            self._alter_sequence(cr, sequence_id, 1, 1)
            sequence = self.next_by_id(cr, uid, sequence_id, context=context)
        return sequence