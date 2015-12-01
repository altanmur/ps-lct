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
import openerp.addons.decimal_precision as dp
import time
from openerp.tools.translate import _

class product_pricelist_item(osv.Model):
    _inherit = 'product.pricelist.item'

    _columns = {
        'description': fields.char('Description'),
        'slab_rate': fields.boolean('Slab Rate'),
        'free_period': fields.integer('Free Period'),
        'first_slab_last_day': fields.integer('Last Day of 1st Slab'),
        'second_slab_last_day': fields.integer('Last Day of 2nd Slab'),
        'price_surcharge_rate1': fields.float('Price Surcharge',
            digits_compute= dp.get_precision('Product Price'), help='Specify the fixed amount to add or substract(if negative) to the amount calculated with the discount.'),
        'price_discount_rate1': fields.float('Price Discount', digits=(16,4)),
        'price_surcharge_rate2': fields.float('Price Surcharge',
            digits_compute= dp.get_precision('Product Price'), help='Specify the fixed amount to add or substract(if negative) to the amount calculated with the discount.'),
        'price_discount_rate2': fields.float('Price Discount', digits=(16,4)),
        'price_surcharge_rate3': fields.float('Price Surcharge',
            digits_compute= dp.get_precision('Product Price'), help='Specify the fixed amount to add or substract(if negative) to the amount calculated with the discount.'),
        'price_discount_rate3': fields.float('Price Discount', digits=(16,4)),
    }

    _defaults = {
        'price_surcharge_rate1': lambda *a: 0,
        'price_discount_rate1': lambda *a: 0,
        'price_surcharge_rate2': lambda *a: 0,
        'price_discount_rate2': lambda *a: 0,
        'price_surcharge_rate3': lambda *a: 0,
        'price_discount_rate3': lambda *a: 0,
    }

    def _check_period(self, cr, uid, ids, context=None):
        for item in self.browse(cr, uid, ids, context=context):
            days = [0, item.free_period or 0, item.first_slab_last_day or 0, item.second_slab_last_day or 0]
            # Return False if free_period < 0, first_slab_last_day < free_period or second_slab_last_day < first_slab_last_day
            if any((b < a) for (a, b) in zip(days[:-1], days[1:])):
                return False
        return True

    _constraints = [
        (_check_period, 'Error! Free period and slab periods should be positive!', ['free_period', 'first_slab_last_day', 'second_slab_last_day']),
    ]

    def on_change_free_period(self, cr, uid, ids, free_period=0, first_slab_last_day=0, context=None):
        return {'value': {'first_slab_last_day': max(first_slab_last_day, free_period)}}

    def on_change_first_slab_last_day(self, cr, uid, ids, first_slab_last_day=0, second_slab_last_day=0, context=None):
        return {'value': {'second_slab_last_day': max(second_slab_last_day, first_slab_last_day)}}

class product_pricelist(osv.Model):
    _inherit = 'product.pricelist'

    def price_get_multi_from_to(self, cr, uid, pricelist_ids, products_by_from_by_to_by_partner, context=None):
        products_by_from_by_partner = [(t[0], t[1], t[3]) for t in products_by_from_by_to_by_partner]
        products_by_to_by_partner = [(t[0], t[2], t[3]) for t in products_by_from_by_to_by_partner]

        result_from = self.price_get_multi(cr, uid, pricelist_ids, products_by_from_by_partner, context)
        result_to = self.price_get_multi(cr, uid, pricelist_ids, products_by_to_by_partner, context)

        for product_id, from_day, to_day, partner_id in products_by_from_by_to_by_partner:
            for pricelist_id in pricelist_ids:
                to_cost = result_to.get(product_id, {}).get(pricelist_id, 0) * to_day
                from_cost = result_from.get(product_id, {}).get(pricelist_id, 0) * from_day
                unit_cost = (to_cost - from_cost) / (to_day - from_day) if to_day - from_day else 0

                if not result_to.get(product_id):
                    result_to.update({
                        product_id: {},
                        })
                result_to[product_id].update({
                    pricelist_id: unit_cost,
                    })

        return result_to

    def price_get_multi(self, cr, uid, pricelist_ids, products_by_qty_by_partner, context=None):

        """multi products 'price_get'.
           @param pricelist_ids:
           @param products_by_qty:
           @param partner:
           @param context: {
             'date': Date of the pricelist (%Y-%m-%d),}
           @return: a dict of dict with product_id as key and a dict 'price by pricelist' as value
        """

        def _create_parent_category_list(id, lst):
            if not id:
                return []
            parent = product_category_tree.get(id)
            if parent:
                lst.append(parent)
                return _create_parent_category_list(parent, lst)
            else:
                return lst
        # _create_parent_category_list

        if context is None:
            context = {}

        date = context.get('date') or time.strftime('%Y-%m-%d')

        currency_obj = self.pool.get('res.currency')
        product_obj = self.pool.get('product.product')
        product_category_obj = self.pool.get('product.category')
        product_uom_obj = self.pool.get('product.uom')
        supplierinfo_obj = self.pool.get('product.supplierinfo')
        price_type_obj = self.pool.get('product.price.type')

        # product.pricelist.version:
        if not pricelist_ids:
            pricelist_ids = self.pool.get('product.pricelist').search(cr, uid, [], context=context)

        pricelist_version_ids = self.pool.get('product.pricelist.version').search(cr, uid, [
                                                        ('pricelist_id', 'in', pricelist_ids),
                                                        '|',
                                                        ('date_start', '=', False),
                                                        ('date_start', '<=', date),
                                                        '|',
                                                        ('date_end', '=', False),
                                                        ('date_end', '>=', date),
                                                    ])
        if len(pricelist_ids) != len(pricelist_version_ids):
            raise osv.except_osv(_('Warning!'), _("At least one pricelist has no active version !\nPlease create or activate one."))

        # product.product:
        product_ids = [i[0] for i in products_by_qty_by_partner]
        #products = dict([(item['id'], item) for item in product_obj.read(cr, uid, product_ids, ['categ_id', 'product_tmpl_id', 'uos_id', 'uom_id'])])
        products = product_obj.browse(cr, uid, product_ids, context=context)
        products_dict = dict([(item.id, item) for item in products])

        # product.category:
        product_category_ids = product_category_obj.search(cr, uid, [])
        product_categories = product_category_obj.read(cr, uid, product_category_ids, ['parent_id'])
        product_category_tree = dict([(item['id'], item['parent_id'][0]) for item in product_categories if item['parent_id']])

        results = {}
        for product_id, qty, partner in products_by_qty_by_partner:
            for pricelist_id in pricelist_ids:
                price = False

                tmpl_id = products_dict[product_id].product_tmpl_id and products_dict[product_id].product_tmpl_id.id or False

                categ_id = products_dict[product_id].categ_id and products_dict[product_id].categ_id.id or False
                categ_ids = _create_parent_category_list(categ_id, [categ_id])
                if categ_ids:
                    categ_where = '(categ_id IN (' + ','.join(map(str, categ_ids)) + '))'
                else:
                    categ_where = '(categ_id IS NULL)'

                if partner:
                    partner_where = 'base <> -2 OR %s IN (SELECT name FROM product_supplierinfo WHERE product_id = %s) '
                    partner_args = (partner, tmpl_id)
                else:
                    partner_where = 'base <> -2 '
                    partner_args = ()

                cr.execute(
                    'SELECT i.*, pl.currency_id '
                    'FROM product_pricelist_item AS i, '
                        'product_pricelist_version AS v, product_pricelist AS pl '
                    'WHERE (product_tmpl_id IS NULL OR product_tmpl_id = %s) '
                        'AND (product_id IS NULL OR product_id = %s) '
                        'AND (' + categ_where + ' OR (categ_id IS NULL)) '
                        'AND (' + partner_where + ') '
                        'AND price_version_id = %s '
                        'AND (min_quantity IS NULL OR min_quantity <= %s) '
                        'AND i.price_version_id = v.id AND v.pricelist_id = pl.id '
                    'ORDER BY sequence',
                    (tmpl_id, product_id) + partner_args + (pricelist_version_ids[0], qty))
                res1 = cr.dictfetchall()
                uom_price_already_computed = False
                for res in res1:
                    if res:
                        if res['base'] == -1:
                            if not res['base_pricelist_id']:
                                price = 0.0
                            else:
                                price_tmp = self.price_get(cr, uid,
                                        [res['base_pricelist_id']], product_id,
                                        qty, context=context)[res['base_pricelist_id']]
                                ptype_src = self.browse(cr, uid, res['base_pricelist_id']).currency_id.id
                                uom_price_already_computed = True
                                price = currency_obj.compute(cr, uid,
                                        ptype_src, res['currency_id'],
                                        price_tmp, round=False,
                                        context=context)
                        elif res['base'] == -2:
                            # this section could be improved by moving the queries outside the loop:
                            where = []
                            if partner:
                                where = [('name', '=', partner) ]
                            sinfo = supplierinfo_obj.search(cr, uid,
                                    [('product_id', '=', tmpl_id)] + where)
                            price = 0.0
                            if sinfo:
                                qty_in_product_uom = qty
                                from_uom = context.get('uom') or product_obj.read(cr, uid, [product_id], ['uom_id'])[0]['uom_id'][0]
                                supplier = supplierinfo_obj.browse(cr, uid, sinfo, context=context)[0]
                                seller_uom = supplier.product_uom and supplier.product_uom.id or False
                                if seller_uom and from_uom and from_uom != seller_uom:
                                    qty_in_product_uom = product_uom_obj._compute_qty(cr, uid, from_uom, qty, to_uom_id=seller_uom)
                                else:
                                    uom_price_already_computed = True
                                cr.execute('SELECT * ' \
                                        'FROM pricelist_partnerinfo ' \
                                        'WHERE suppinfo_id IN %s' \
                                            'AND min_quantity <= %s ' \
                                        'ORDER BY min_quantity DESC LIMIT 1', (tuple(sinfo),qty_in_product_uom,))
                                res2 = cr.dictfetchone()
                                if res2:
                                    price = res2['price']
                        else:
                            price_type = price_type_obj.browse(cr, uid, int(res['base']))
                            uom_price_already_computed = True
                            price = currency_obj.compute(cr, uid,
                                    price_type.currency_id.id, res['currency_id'],
                                    product_obj.price_get(cr, uid, [product_id],
                                    price_type.field, context=context)[product_id], round=False, context=context)

                        if price is not False:
                            if qty <= 0:
                                price = 0.
                                break
                            price_limit = price
                            if res['slab_rate']:
                                for key in ['free_period', 'first_slab_last_day', 'second_slab_last_day']:
                                    res[key] = min(res[key] or 0, qty)
                                # if products_dict[product_id].additional_storage:
                                #     res['free_period'] = 0
                                for key in ['price_discount_rate1', 'price_surcharge_rate1', 'price_discount_rate2', 'price_surcharge_rate2', 'price_discount_rate3', 'price_surcharge_rate3']:
                                    res[key] = res[key] or 0.0

                                periods_by_discountcoef_by_surcharge = [
                                    (res['free_period'], 0.0, 0.0),
                                    (res['first_slab_last_day'] - res['free_period'], 1.0 + res['price_discount_rate1'], res['price_surcharge_rate1']),
                                    (res['second_slab_last_day'] - res['first_slab_last_day'], 1.0 + res['price_discount_rate2'], res['price_surcharge_rate2']),
                                    (qty - res['second_slab_last_day'], 1.0 + res['price_discount_rate3'], res['price_surcharge_rate3']),
                                ]
                                price = sum([(period*(coef*price + (period > 0 and surcharge or 0))) for period, coef, surcharge in periods_by_discountcoef_by_surcharge])/qty
                                if res['price_round']:
                                    price = tools.float_round(price, precision_rounding=res['price_round'])
                            else:
                                price = price * (1.0+(res['price_discount'] or 0.0))
                                if res['price_round']:
                                    price = tools.float_round(price, precision_rounding=res['price_round'])
                                price += (res['price_surcharge'] or 0.0)
                                if res['price_min_margin']:
                                    price = max(price, price_limit+res['price_min_margin'])
                                if res['price_max_margin']:
                                    price = min(price, price_limit+res['price_max_margin'])
                            break

                    else:
                        # False means no valid line found ! But we may not raise an
                        # exception here because it breaks the search
                        price = False

                if price:
                    results['item_id'] = res['id']
                    if 'uom' in context and not uom_price_already_computed:
                        product = products_dict[product_id]
                        uom = product.uos_id or product.uom_id
                        price = product_uom_obj._compute_price(cr, uid, uom.id, price, context['uom'])

                if results.get(product_id):
                    results[product_id][pricelist_id] = price
                else:
                    results[product_id] = {pricelist_id: price}
        return results


class product_pricelist_item(osv.osv):
    _inherit = 'product.pricelist.item'

    def find_active_item(self, cr, uid, product_id, pricelist_id, context=None):
        today = fields.date.today()
        version_ids = self.pool.get('product.pricelist.version').search(cr, uid, [
                ('pricelist_id', '=', pricelist_id),
                ('active', '=', True),
                '|', ('date_start', '<=', today), ('date_start', '=', False),
                '|', ('date_end', '>=', today), ('date_end', '=', False),
            ])
        item_ids = self.search(cr, uid, [
                ('price_version_id', 'in', version_ids),
                ('product_id', '=', product_id),
            ], order='sequence', limit=1, context=context)

        return item_ids and item_ids[0] or False


