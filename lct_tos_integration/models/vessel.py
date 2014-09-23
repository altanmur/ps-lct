# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-TODAY OpenERP S.A. <http://www.odoo.com>
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
import re
import xml.etree.ElementTree as ET

class lct_tos_vessel(osv.Model):
    _name = 'lct.tos.vessel'

    _columns = {
        'vessel_id': fields.char('ID'),
        'name': fields.char('Name'),
        'call_sign': fields.char('Call sign'),
        'lloyds_number': fields.char('lloyds number'),
        'vessel_in_voyage_number': fields.char('vessel in voyage number'),
        'vessel_out_voyage_number': fields.char('vessel out voyage number'),
        'vessel_eta': fields.datetime('ETA'),
    }

    def xml_to_vessel(self, cr, uid, imp_data_id, context=None):
        imp_data = self.pool.get('lct.tos.import.data').browse(cr, uid, imp_data_id, context=context)
        content = re.sub('<\?xml.*\?>','',imp_data.content).replace(u"\ufeff","")
        vessels = ET.fromstring(content)
        vsl_ids = []
        for vessel in vessels.findall('vessel'):
            new_vessel = {
                'vessel_id': vessel.find('vessel_id').text,
                'name': vessel.find('name').text,
                'call_sign': vessel.find('call_sign').text,
                'lloyds_number': vessel.find('lloyds_number').text,
                'vessel_in_voyage_number': vessel.find('vessel_in_voyage_number').text,
                'vessel_out_voyage_number': vessel.find('vessel_out_voyage_number').text,
                'vessel_eta': vessel.find('vessel_eta').text,
            }
            vsl_ids.append(self.create(cr, uid, new_vessel, context=context))
        return vsl_ids
