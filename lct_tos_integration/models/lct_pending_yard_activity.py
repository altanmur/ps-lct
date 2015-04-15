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

from datetime import datetime


class lct_pending_yard_activity(osv.osv):
    _name = 'lct.pending.yard.activity'

    _columns = {
        'name': fields.char('Container number', required=True),
        'vessel_id': fields.char('Vessel ID', required=True),
        'plugged_time': fields.integer('Plugged time'),
        'dep_timestamp': fields.datetime('Departure timestamp'),
        'arr_timestamp': fields.datetime('Arrival timestamp'),
        'type': fields.selection([
                ('expst', 'Storage'),
                ('reefe', 'Reefer Electricity'),
            ], string='Type', required=True),
        'status': fields.selection([
                ('pending', 'Pending'),
                ('processed', 'Processed'),
            ], string='Status', required=True)
    }

    _defaults = {
        'status': 'pending',
    }

    def _get_elmnt_text(self, line, tag, raise_on_failure=False):
        elmnt = line.find(tag)
        if elmnt is None:
            if raise_on_failure:
                raise osv.except_osv(('Error'), ('Could not find tag %s on a yard activity line' % tag))
            else:
                return False
        return elmnt.text

    def _get_elmnt_digit(self, line, tag):
        text = self._get_elmnt_text(line, tag)
        if not text or not text.isdigit():
            return False
        return int(text)

    def create_activity(self, cr, uid, line, context=None):
        vals = {
            'name': self._get_elmnt_text(line, 'container_number'),
            'status': 'pending',
            'vessel_id': self._get_elmnt_text(line, 'vessel_id'),
        }

        yac_type = self._get_elmnt_text(line, 'yard_activity', raise_on_failure=True)
        if yac_type == 'EXPST':
            vals['type'] = 'expst'
        elif yac_type == 'REEFE':
            vals['type'] = 'reefe'
        dep_timestamp = self._get_elmnt_text(line, 'departure_timestamp')
        if not dep_timestamp:
            raise osv.except_osv(('Error'), ('departure_timestamp in not defined at line %d' % (line.sourceline)))
        arr_timestamp = self._get_elmnt_text(line, 'arrival_timestamp')
        if not dep_timestamp:
            raise osv.except_osv(('Error'), ('arrival_timestamp in not defined at line %d' % (line.sourceline)))
        dep_time = datetime.strptime(dep_timestamp, "%Y-%m-%d %H:%M:%S")
        arr_time = datetime.strptime(arr_timestamp, "%Y-%m-%d %H:%M:%S")
        if dep_time < arr_time:
            raise osv.except_osv(('Error'), ('Departure timestamp should be greater than the arrival timestamp'))
        vals['dep_timestamp'] = dep_timestamp
        vals['arr_timestamp'] = arr_timestamp
        vals['plugged_time'] = self._get_elmnt_digit(line, 'plugged_time')

        self.create(cr, uid, vals, context=context)
