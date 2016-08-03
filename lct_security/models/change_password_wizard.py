# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2011 OpenERP S.A (<http://www.openerp.com>).
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
from openerp.tools.translate import _

import hashlib
import hmac
import logging
import random
from string import ascii_letters, digits

import openerp

_logger = logging.getLogger(__name__)

magic_md5 = '$1$'
magic_sha256 = '$5$'

from openerp.addons.base.res import res_users
res_users.USER_PRIVATE_FIELDS.append('password_crypt')

def gen_salt(length=8, symbols=None):
    if symbols is None:
        symbols = ascii_letters + digits
    return ''.join(random.SystemRandom().sample(symbols, length))

def md5crypt( raw_pw, salt, magic=magic_md5 ):
    """ md5crypt FreeBSD crypt(3) based on but different from md5

    The md5crypt is based on Mark Johnson's md5crypt.py, which in turn is
    based on  FreeBSD src/lib/libcrypt/crypt.c (1.2)  by  Poul-Henning Kamp.
    Mark's port can be found in  ActiveState ASPN Python Cookbook.  Kudos to
    Poul and Mark. -agi

    Original license:

    * "THE BEER-WARE LICENSE" (Revision 42):
    *
    * <phk@login.dknet.dk>  wrote  this file.  As  long as  you retain  this
    * notice  you can do  whatever you want with this stuff. If we meet some
    * day,  and you think this stuff is worth it,  you can buy me  a beer in
    * return.
    *
    * Poul-Henning Kamp
    """
    raw_pw = raw_pw.encode('utf-8')
    salt = salt.encode('utf-8')
    hash = hashlib.md5()
    hash.update( raw_pw + magic + salt )
    st = hashlib.md5()
    st.update( raw_pw + salt + raw_pw)
    stretch = st.digest()

    for i in range( 0, len( raw_pw ) ):
        hash.update( stretch[i % 16] )

    i = len( raw_pw )

    while i:
        if i & 1:
            hash.update('\x00')
        else:
            hash.update( raw_pw[0] )
        i >>= 1

    saltedmd5 = hash.digest()

    for i in range( 1000 ):
        hash = hashlib.md5()

        if i & 1:
            hash.update( raw_pw )
        else:
            hash.update( saltedmd5 )

        if i % 3:
            hash.update( salt )
        if i % 7:
            hash.update( raw_pw )
        if i & 1:
            hash.update( saltedmd5 )
        else:
            hash.update( raw_pw )

        saltedmd5 = hash.digest()

    itoa64 = './0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'

    rearranged = ''
    for a, b, c in ((0, 6, 12), (1, 7, 13), (2, 8, 14), (3, 9, 15), (4, 10, 5)):
        v = ord( saltedmd5[a] ) << 16 | ord( saltedmd5[b] ) << 8 | ord( saltedmd5[c] )

        for i in range(4):
            rearranged += itoa64[v & 0x3f]
            v >>= 6

    v = ord( saltedmd5[11] )

    for i in range( 2 ):
        rearranged += itoa64[v & 0x3f]
        v >>= 6

    return magic + salt + '$' + rearranged


class change_password_wizard(osv.TransientModel):
    _inherit = "change.password.wizard"

    def default_get(self, cr, uid, fields, context=None):
        res = super(change_password_wizard, self).default_get(cr, uid, fields, context)
        [r[2].update({"uid": uid}) for r in res["user_ids"]]
        return res


class change_password_user(osv.TransientModel):
    _inherit = "change.password.user"

    _columns = {
        "old_passwd": fields.char("Old Password"),
        "uid": fields.integer("uid"),
    }

    def _security_password(self, login, old_passwd, new_passwd, stored_passwd, min_len=8, max_ss_len=4):
            error_title = ""
            if not self.confirm_password(old_passwd, stored_passwd):
                raise osv.except_osv(_(error_title), _("Old password did not match"))
            if login == new_passwd:
                raise osv.except_osv(_(error_title), _("Password and Login must be different"))
            if len(new_passwd) < min_len:
                raise osv.except_osv(_(error_title), _("Password must be at least %s characters long" %min_len))
            if old_passwd:
                ss_len = self._get_max_ss_len(old_passwd, new_passwd)
                if ss_len >= max_ss_len:
                    raise osv.except_osv(_(error_title), _("Old and New Passwords must have less than %s subsequent characters in common" %max_ss_len))

    def confirm_password(self, old, store):
            if not old or not store:
                return True
            if store[:len(magic_md5)] == magic_md5:
                salt = store[len(magic_md5):11]
                if store == md5crypt(old, salt):
                    return True

    def _get_max_ss_len(self, s1, s2):
        m = [[0] * (1 + len(s2)) for i in xrange(1 + len(s1))]
        for x in xrange(len(s1)):
            for y in xrange(len(s2)):
                if s1[x] == s2[y]:
                    m[x+1][y+1] = m[x][y] + 1
        return max(max(r) for r in m)

    def change_password_button(self, cr, uid, ids, context=None):

        for user in self.browse(cr, uid, ids, context=context):
            self._security_password(user.user_login, user.old_passwd, user.new_passwd, user.user_id.password_crypt)

        super(change_password_user, self).change_password_button(cr, uid, ids, context)
