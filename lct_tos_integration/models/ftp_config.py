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
from ftplib import FTP
from lxml import etree as ET
import os
from StringIO import StringIO
from datetime import datetime
import io
import traceback



class ftp_config(osv.osv):
    _name="ftp.config"

    _columns = {
        'name': fields.char('Name', required=True),
        'addr': fields.char('Server Address', required=True),
        'user': fields.char('Username', required=True),
        'psswd': fields.char('Password', required=True),
        'inbound_path': fields.char('Path of inbound folder', required=True),
        'outbound_path': fields.char('Path of outbound folder', required=True),
        'active': fields.boolean('Active'),
        'last_import': fields.date('Last Import', readonly=True)
    }

    def _check_active(self, cr, uid, ids, context=None):
        config_ids = self.search(cr, uid, [('active','=',True)], context=context)
        return len(config_ids) <= 1

    _constraints = [
        (_check_active, 'There can only be one active ftp configuration', ['active']),
    ]

    # Data Import

    def _import_ftp_data(self, cr, uid, config_ids, context=None):
        if not config_ids:
            return []

        imp_data_model = self.pool.get('lct.tos.import.data')
        imp_data_ids = []
        for config_obj in self.browse(cr, uid, config_ids, context=context):
            ftp = FTP(host=config_obj.addr, user=config_obj.user, passwd=config_obj.psswd)
            ftp.cwd(config_obj.outbound_path)
            archive_path = 'done'
            if archive_path not in ftp.nlst():
                ftp.mkd(archive_path)

            for filename in ftp.nlst():
                if filename in [archive_path, '.', '..']:
                    continue

                content = StringIO()
                try:
                    ftp.retrlines('RETR ' + filename, content.write)
                except:
                    imp_data_model.create(cr, uid, {
                            'name': filename,
                            'content': False,
                            'status': 'fail',
                            'error': traceback.format_exc(),
                        }, context=context)
                    continue

                imp_data_ids.append(imp_data_model.create(cr, uid, {
                        'name': filename,
                        'content': content.getvalue(),
                    }, context=context))

                toname = filename
                extension = ''
                if '.' in filename[1:-1]:
                    extension =  "".join(['.', filename.split('.')[-1]])
                toname_base = toname[:-(len(extension))]

                n = 1
                archive_files = [archive_file.replace('/done','') for archive_file in ftp.nlst(archive_path)]
                while toname in archive_files :
                    toname = "".join([toname_base, '-', str(n), extension])
                    n += 1
                try:
                    ftp.rename(filename, "".join([archive_path, "/", toname]))
                except:
                    imp_data_model.write(cr, uid, imp_data_ids.pop(), {
                        'status': 'fail',
                        'error': traceback.format_exc(),
                        }, context=context)
                    continue

        cr.commit()
        imp_data_model.process_data(cr, uid, imp_data_ids, context=context)

    def button_import_ftp_data(self, cr, uid, ids, context=None):
        return self._import_ftp_data(cr, uid, ids, context=context)

    def cron_import_ftp_data(self, cr, uid, context=None):
        self._import_ftp_data(cr, uid, self.search(cr, uid, [('active','=',True)]), context=context)
