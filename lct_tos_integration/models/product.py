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

    _columns = {
        'service_id': fields.many2one('lct.product.service', 'Service'),
        'category_id': fields.many2one('lct.product.category', 'Category'),
        'sub_category_id': fields.many2one('lct.product.sub.category', 'Sub-category'),
        'size_id': fields.many2one('lct.product.size', 'Size'),
        'status_id': fields.many2one('lct.product.status', 'Status'),
        'type_id': fields.many2one('lct.product.type', 'Type'),
    }

    def _product_by_properties(self, cr, uid, properties, ids=None, context=None):
        domain = []
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

    def get_products_by_properties(self, cr, uid, properties, context=None):
        service_ids = properties.pop('service_ids', False)
        if not service_ids:
            service_ids = [False]

        product_ids = []
        for service_id in service_ids:
            properties['service_id'] = service_id
            product_id = self.search(cr, uid, [(prop, '=', prop_id) for prop, prop_id in properties.iteritems()])
            if product_id:
                if len(product_id) == 1:
                    product_id = product_id[0]
                else:
                    product_id = False
            else:
                product_id = self._product_by_properties(cr, uid, properties, context=context)
            product_ids.append(product_id)

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
