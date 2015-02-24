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

class product_product(osv.osv):
    _inherit = 'product.product'

    def _calc_cont_nr_editable(self, cr, uid, ids, fields, arg, context=None):
        res = {}
        for product_id in ids:
            res[product_id] = self._is_cont_nr_editable(cr, uid, product_id, context=context)
        return res

    _columns = {
        'service_id': fields.many2one('lct.product.service', 'Service'),
        'category_id': fields.many2one('lct.product.category', 'Category'),
        'sub_category_id': fields.many2one('lct.product.sub.category', 'Sub-category'),
        'size_id': fields.many2one('lct.product.size', 'Size'),
        'status_id': fields.many2one('lct.product.status', 'Status'),
        'type_id': fields.many2one('lct.product.type', 'Type'),
        'cont_nr_editable': fields.function(_calc_cont_nr_editable, type='boolean', string="Container number editable"),
    }

    def _is_cont_nr_editable(self, cr, uid, product_id, context=None):
        nonvalid_product_ids = self.search(cr, uid, ['|', ('name', 'like', 'Gearbox count'), ('name', 'like', 'Hatchcover moves')])
        return product_id and product_id not in nonvalid_product_ids or False

    def _product_by_properties(self, cr, uid, properties, ids=None, context=None):
        domain = []
        if 'category_id' in properties:
            domain.append(('category_id', '=', properties['category_id']))
            del properties['category_id']

        if ids is not None:
            if not ids:
                return False
            elif len(ids) == 1:
                return ids[0]
            else:
                domain.append(('id','in',ids))

        new_properties = dict(properties)
        for prop, value in properties.iteritems():
            new_ids = self.search(cr, uid, domain + [(prop, '=', value)], context=context)
            del new_properties[prop]
            product_id = self._product_by_properties(cr, uid, new_properties, new_ids, context=context)
            if product_id:
                return product_id
        return False

    def _get_property_string(self, cr, uid, properties, context=None):
        property_names = {}

        for prop, prop_id in properties.iteritems():
            if not prop_id:
                property_names[prop] = "None"
                continue
            relation = self.fields_get(cr, uid, context=context)[prop]['relation']
            property_names[prop] = self.pool.get(relation).name_get(cr, uid, prop_id, context=context)[0][1]
        return ";  ".join([("%s: %s" % (prop, name)) for prop, name in property_names.iteritems()])

    def _get_too_many_products_found_error_message(self, cr, uid, properties, line, context=None):
        message = "Too many products found for this combination at line %d in xml:  " % (line,)
        message += self._get_property_string(cr, uid, properties, context=context)
        return message

    def _get_product_not_found_error_message(self, cr, uid, properties, line, context=None):
        message = "No product found for this combination at line %d in xml:  " % (line,)
        message += self._get_property_string(cr, uid, properties, context=context)
        return message

    def get_products_by_properties(self, cr, uid, properties, line, context=None):
        properties = dict(properties)
        service_ids = properties.pop('service_ids', False)
        if not service_ids:
            service_ids = [False]

        product_ids = []
        for service_id in service_ids:
            properties['service_id'] = service_id
            product_id = self.search(cr, uid, [(prop, '=', prop_id) for prop, prop_id in properties.iteritems()])
            if not product_id:
                product_id = self._product_by_properties(cr, uid, properties, context=context)
                product_id = product_id and [product_id] or False
            if not product_id:
                error_message = self._get_product_not_found_error_message(cr, uid, properties, line, context=context)
                raise osv.except_osv(('Error'), (error_message))

            if len(product_id) > 1:
                error_message = self._get_too_many_products_found_error_message(cr, uid, properties, line, context=context)
                raise osv.except_osv(('Error'), (error_message))

            product_ids.append(product_id[0])

        return product_ids

class lct_product_service(osv.osv):
    _name = 'lct.product.service'

    _columns = {
        'name' : fields.char('Name'),
    }

class lct_product_category(osv.osv):
    _name = 'lct.product.category'

    _columns = {
        'name' : fields.char('Name'),
    }

class lct_product_sub_category(osv.osv):
    _name = 'lct.product.sub.category'

    _columns = {
        'name' : fields.char('Name'),
    }

class lct_product_size(osv.osv):
    _name = 'lct.product.size'
    _rec_name='size'

    _columns = {
        'size': fields.integer('Size'),
    }

class lct_product_status(osv.osv):
    _name = 'lct.product.status'

    _columns = {
        'name': fields.char('Name'),
    }

class lct_product_type(osv.osv):
    _name = 'lct.product.type'

    _columns = {
        'name': fields.char('Name'),
    }
