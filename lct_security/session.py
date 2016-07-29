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

from openerp.addons import web
from datetime import datetime

def session_authenticate(self, db, login, password, env=None):
    uid = self.proxy('common').authenticate(db, login, password, env)
    self.bind(db, uid, login, password)

    if not uid:
        return {}

    user_obj = self.model("res.users")
    user_infos = user_obj.search_read([("login", "=", login)], ["last_changed", "failed_conn"])
    failed_conn = 0
    last_changed_days = 0
    if user_infos and user_infos[0].get("id"):
        last_changed = user_infos[0].get("last_changed")
        if last_changed:
            dt_last_changed = datetime.strptime(last_changed, "%Y-%m-%d %H:%M:%S")
            last_changed_days = (datetime.now() - dt_last_changed).days
        failed_conn = user_infos[0].get("failed_conn")

    if last_changed_days > 30 or failed_conn > 5:
        uid = None
    else:
        self.get_context()
    return {
        "last_changed": last_changed_days,
        "failed_conn": failed_conn,
    }

@web.http.jsonrequest
def ctrl_authenticate(self, req, db, login, password, base_location=None):
    wsgienv = req.httprequest.environ
    env = dict(
        base_location=base_location,
        HTTP_HOST=wsgienv['HTTP_HOST'],
        REMOTE_ADDR=wsgienv['REMOTE_ADDR'],
    )
    tmp = req.session.authenticate(db, login, password, env)
    res = self.session_info(req)
    res.update({
        "last_changed": tmp.get("last_changed"),
        "failed_conn": tmp.get("failed_conn"),
    })
    return res

web.session.OpenERPSession.authenticate = session_authenticate
web.controllers.main.Session.authenticate = ctrl_authenticate