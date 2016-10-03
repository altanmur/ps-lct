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
        if "password" in vals:
            vals.update({
                "last_changed": fields.datetime.now(),
                "failed_conn": 0,
                })
        return super(res_users, self).write(cr, uid, ids, vals, context)

    def authenticate(self, db, login, password, user_agent_env):
        res = super(res_users, self).authenticate(db, login, password, user_agent_env)
        cr = openerp.pooler.get_db(db).cursor()
        cr.autocommit(True)
        cr.execute("SELECT failed_conn FROM res_users WHERE login = %s", [login])
        if cr.rowcount:
            failed_conn = cr.fetchone()[0]
            if not res:
                failed_conn = failed_conn + 1
            elif failed_conn <= 5:
                failed_conn = 0
            cr.execute("UPDATE res_users SET failed_conn = %s WHERE login = %s", [failed_conn, login])
        cr.close()
        return res

    def change_password(self, cr, uid, old_passwd, new_passwd, context=None):
        """Change current user password. Old password must be provided explicitly
        to prevent hijacking an existing user session, or for cases where the cleartext
        password is not used to authenticate requests.

        :return: True
        :raise: openerp.exceptions.AccessDenied when old password is wrong
        :raise: except_osv when new password is not set or empty
        """
        self.check(cr.dbname, uid, old_passwd)
        user = self.browse(cr, uid, uid, context)
        self.pool.get("change.password.user")._security_password(user.login, old_passwd, new_passwd, user.user_id.password_crypt)
        if new_passwd:
            return self.write(cr, 1, uid, {'password': new_passwd})
        raise osv.except_osv(_('Warning!'), _("Setting empty passwords is not allowed for security reasons!"))