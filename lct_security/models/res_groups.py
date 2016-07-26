# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#    Copyright (C) 2010-2013 OpenERP s.a. (<http://openerp.com>).
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

import openerp
from openerp.osv import fields, osv


class tmp_res_group_user_rel(osv.osv):
    _name = "tmp_res_group_user_rel"

    _columns = {
        "group_id": fields.many2one("res.groups", required=True, string="Group"),
        "user_id": fields.many2one("res.users", required=True, string="User"),
        "from_dt": fields.datetime("Autorized From", required=True),
        "to_dt": fields.datetime("Authorized Until"),
    }


class res_groups(osv.osv):
    _inherit = "res.groups"

    _columns = {
        "tmp_group_user_ids": fields.one2many("tmp_res_group_user_rel", "group_id", "Temporary Users", translate=True)
    }

    def update_tmp_acl(self, cr, uid):
        now = fields.datetime.now()
        tmp_group_user_obj = self.pool.get("tmp_res_group_user_rel")
        group_user_obj = self.pool.get("res_groups_users_rel")
        tmp_group_user_ids = tmp_group_user_obj.search(cr, uid, [])
        tmp_group_users = tmp_group_user_obj.browse(cr, uid, tmp_group_user_ids)
        for tmp_group_user in tmp_group_users:
            user = tmp_group_user.user_id
            group = tmp_group_user.group_id
            user_line_ids = [rec for rec in group.users if rec == user]
            if tmp_group_user.from_dt < now < tmp_group_user.to_dt:
                if not user_line_ids:
                    group.write({"users": [(4, user.id)]})
            else:
                if user_line_ids:
                    group.write({"users": [(3, user.id)]})
