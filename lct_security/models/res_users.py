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
from openerp.osv import osv, fields
from openerp.tools.translate import _


class res_users(osv.osv):
    _inherit = "res.users"

    _columns = {
        "failed_conn": fields.integer(),
        "last_changed": fields.datetime(),
    }

    def write(self, cr, uid, ids, vals, context=None):
        def _get_max_ss_len(s1, s2):
            m = [[0] * (1 + len(s2)) for i in xrange(1 + len(s1))]
            for x in xrange(len(s1)):
                for y in xrange(len(s2)):
                    if s1[x] == s2[y]:
                        m[x+1][y+1] = m[x][y] + 1
            return max(max(r) for r in m)

        def _security_password(rec, vals, min_len=8, max_ss_len=4):
            login = vals.get("login", rec.login)
            name = vals.get("name", rec.name)
            old_pw = rec.password
            new_pw = vals.get("password")
            error_title = "Unsecure Password"
            if login == new_pw:
                raise osv.except_osv(_(error_title), _("Password and Login must not be the same"))
            if name == new_pw:
                raise osv.except_osv(_(error_title), _("Password and User Name must not be the same"))
            if len(new_pw) < min_len:
                raise osv.except_osv(_(error_title), _("Password must be at least %s characters long" %min_len))
            ss_len = _get_max_ss_len(old_pw, new_pw)
            if ss_len >= max_ss_len:
                raise osv.except_osv(_(error_title), _("Old and New Password must have less than %s character substring" %max_ss_len))

        if "password" in vals:
            rec = self.browse(cr, uid, ids, context=context)
            _security_password(rec, vals)
        return super(res_users, self).write(cr, uid, ids, vals, context=context)

