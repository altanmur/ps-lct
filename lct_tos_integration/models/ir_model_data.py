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

from openerp.osv import osv

class ir_model_data(osv.osv):
    _inherit = 'ir.model.data'

    def __init__(self, pool, cr):
        super(ir_model_data, self).__init__(pool, cr)
        cr.execute("SELECT id FROM res_groups WHERE name = 'Cashier (for all access inherit)'")
        groups = cr.fetchall()
        cr.execute("SELECT id FROM ir_model_data WHERE name = 'cashier_group' AND module = 'lct_tos_integration'")
        ir_model_datas = cr.fetchall()
        if groups and not ir_model_datas:
            group_id = groups[0][0]
            cr.execute("""
                INSERT INTO ir_model_data (
                    create_uid,
                    create_date,
                    write_uid,
                    write_date,
                    noupdate,
                    name,
                    module,
                    model,
                    res_id)
                VALUES (
                    1,
                    now(),
                    1,
                    now(),
                    true,
                    'cashier_group',
                    'lct_tos_integration',
                    'res.groups',
                    %s
                    )
                """ %group_id)


    def get_record_id(self, cr, uid, module, xml_id, context=None):
        model_data_id = self._get_id(cr, uid, module, xml_id)
        model_data = self.browse(cr, uid, model_data_id, context=context)
        model = self.pool.get(model_data.model)
        if self.pool.get(model_data.model).browse(cr, uid, model_data.res_id, context=context).exists():
            return model_data.res_id
        return False
