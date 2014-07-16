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

class ftp_config(osv.osv):

    _name="ftp.config"

    _columns = {
        'name': fields.char('Name', required=True),
        'addr': fields.char('Server Address', required=True),
        'user': fields.char('Username', required=True),
        'psswd': fields.char('Password', required=True),
        'inbound_path': fields.char('Path of inbound folder', required=True),
        'outbound_path': fields.char('Path of outbound folder', required=True),
        'is_active': fields.boolean('Active'),
    }

    _order = 'is_active desc'

    def create(self, cr, uid, vals, context=None):
        if vals and vals.get('is_active', False):
            config_ids = self.search(cr, uid, [], context=context)
            self.write(cr, uid, config_ids, {'is_active': False}, context=context)
        return super(ftp_config, self).create(cr, uid, vals, context=context)

    def write(self, cr, uid, ids, vals, context=None):
        if vals and vals.get('is_active', False):
            config_ids = self.search(cr, uid, [('id','not in',ids)], context=context)
            self.write(cr, uid, config_ids, {'is_active': False}, context=context)
        return super(ftp_config, self).write(cr, uid, ids, vals, context=context)