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
from datetime import datetime, timedelta
import traceback
import xml.etree.ElementTree as ET
import re

class yardActivity(osv.Model):
    _name = "lct.tos.yardactivity"
    _rec_name  = 'container_number'

    _columns = {
        'container_number': fields.char('container number', required=True),
        'date_activity': fields.date('date'),
        'container_operator_id': fields.char('Operator'),
        'arrival_timestamp': fields.datetime('Arrival'),
        'departure_timestamp': fields.datetime('Departure'),
        'transaction_direction': fields.char('transaction direction'),
        'yard_activity': fields.char('yard activity'),
        'quantity': fields.integer('quantity'),
        'from_location': fields.char('from location'),
        'to_location': fields.char('to location'),
        'status': fields.char('status'),
        'category': fields.char('category'),
        'container_size': fields.char('container size'),
        'container_type_id': fields.char('container type'),
        'container_height': fields.char('container height'),
        'container_hazardous_class_id': fields.char('container hazardous class'),
        'active_reefer': fields.char('active reefer'),
        'oog': fields.char('oog'),
        'bb': fields.char('bb'),
        'bundles': fields.char('bundles'),
        'plugged_time': fields.char('plugged time'),
        'departure_mode_id': fields.char('departure mode id'),
        'special_handling_code_id': fields.char('special handling code id'),
        'service_code_id': fields.char('service code id'),
        'state': fields.selection([('draft','Draft'),('done','Done')],'State',required=True,readonly=True),
    }



    _defaults = {
        'state' : 'draft',
    }

    def xml_to_yac(self, cr, uid, imp_data_id, context=None):
        imp_data = self.pool.get('lct.tos.import.data').browse(cr, uid, imp_data_id, context=context)
        content = re.sub('<\?xml.*\?>','',imp_data.content).replace(u"\ufeff","")
        yardacts = ET.fromstring(content)
        yardactivity_ids = []
        yardacti_model = self.pool.get("lct.tos.yardactivity")
        for yardact in yardacts.findall('yactivity'):
            for lines in yardact.findall('lines'):
                for line in lines.findall('line'):
                    new_yardact = {
                        'container_number': line.find('container_number').text,
                        'date_activity': yardact.find('date').text,
                        'container_operator_id': line.find('container_operator_id').text,
                        'arrival_timestamp': line.find('arrival_timestamp').text,
                        'departure_timestamp': line.find('departure_timestamp').text,
                        'transaction_direction': line.find('transaction_direction').text,
                        'yard_activity': line.find('yard_activity').text,
                        'quantity': line.find('quantity').text,
                        'from_location': line.find('from_location').text,
                        'to_location': line.find('to_location').text,
                        'status': line.find('status').text,
                        'category': line.find('category').text,
                        'container_size': line.find('container_size').text,
                        'container_type_id': line.find('container_type_id').text,
                        'container_height': line.find('container_height').text,
                        'container_hazardous_class_id': line.find('container_hazardous_class_id').text,
                        'active_reefer': line.find('active_reefer').text,
                        'oog': line.find('oog').text,
                        'bb': line.find('bb').text,
                        'bundles': line.find('bundles').text,
                        'plugged_time': line.find('plugged_time').text,
                        'departure_mode_id': line.find('departure_mode_id').text,
                        'special_handling_code_id': line.find('special_handling_code_id').text,
                        'service_code_id': line.find('service_code_id').text,
                    }
                    yardactivity_ids.append(yardacti_model.create(cr, uid, new_yardact, context=context))
        return yardactivity_ids

    def button_create_invoice(self, cr, uid, yard_ids, context=None):
        yards = self.browse(cr, uid, yard_ids, context=context)
        invoicee_ids = []
        for yard in yards:
            invoicee_ids.append(yard.container_operator_id)
        invoicee_ids = set(invoicee_ids)
        #Create an invoice by container_operator_id

        return True
