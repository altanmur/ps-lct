

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
from lxml import etree as ET
import traceback
import re
from datetime import datetime


class lct_tos_import_data(osv.Model):
    _name = 'lct.tos.import.data'

    _columns = {
        'name': fields.char('File name', readonly=True),
        'content': fields.text('File content', readonly=True),
        'type': fields.selection([('xml','xml')], string='File type'),
        'status': fields.selection([('fail','Failed to process'),('success','Processed'),('pending','Pending')], string='Status', readonly=True, required=True),
        'create_date': fields.date(string='Import date', readonly=True),
        'error': fields.text('Errors'),
    }

    _defaults = {
        'status': 'pending',
    }

    def button_reset(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'status': 'pending', 'error': False}, context=context)

    def process_data(self, cr, uid, ids, context=None):
        if not ids:
            return []

        imp_datas = self.browse(cr, uid, ids, context=context)
        if any([(imp_data.status != 'pending') for imp_data in  imp_datas]):
            raise osv.except_osv(('Error'),('You can only process pending data'))

        inv_model = self.pool.get('account.invoice')
        for imp_data in imp_datas:
            cr.execute('SAVEPOINT SP')
            filename = imp_data.name
            if re.match('^VBL_\d{6}_\d{6}\.xml$', filename):
                try:
                    inv_model.xml_to_vbl(cr, uid, imp_data.id, context=context)
                except:
                    cr.execute('ROLLBACK TO SP')
                    self.write(cr, uid, imp_data.id, {
                        'status': 'fail',
                        'error': traceback.format_exc(),
                        }, context=context)
                    continue
            elif re.match('^APP_\d{6}_\d{6}\.xml$', filename):
                try:
                    inv_model.xml_to_app(cr, uid, imp_data.id, context=context)
                except:
                    cr.execute('ROLLBACK TO SP')
                    self.write(cr, uid, imp_data.id, {
                        'status': 'fail',
                        'error': traceback.format_exc(),
                        }, context=context)
                    continue
            else:
                cr.execute('ROLLBACK TO SP')
                error = 'Filename format not known.\nKnown formats are :\n    APP_YYMMDD_SEQ000.xml\n    VBL_YYMMDD_SEQ000.xml'
                self.write(cr, uid, imp_data.id, {
                    'status': 'fail',
                    'error': error,
                    }, context=context)
                continue
            self.write(cr, uid, imp_data.id, {'status': 'success'}, context=context)
            cr.execute('RELEASE SAVEPOINT SP')
