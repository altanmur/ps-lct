from openerp.tests.common import TransactionCase
from openerp.osv import osv



class TestProductSearch(TransactionCase):

    def setUp(self):
        super(TestProductSearch, self).setUp()
        self.product_model = self.registry('product.product')

    def _get_prop_id(self, xml_id):
        cr, uid, = self.cr, self.uid

        module = 'lct_tos_integration'
        imd_model = self.registry('ir.model.data')

        return imd_model.get_record_id(cr, uid, module, xml_id)

    def test_when_true_properties(self):
        cr, uid, = self.cr, self.uid
        product_model = self.product_model

        properties = {
            'category_id': self._get_prop_id('lct_product_category_import'),
            'service_ids': [self._get_prop_id('lct_product_service_storage')],
            'sub_category_id': self._get_prop_id('lct_product_sub_category_transitsahel'),
            'size_id': self._get_prop_id('lct_product_size_40'),
            'type_id': self._get_prop_id('lct_product_type_gp'),
            'status_id': False,
        }

        product_ids = product_model.get_products_by_properties(cr, uid, properties)
        self.assertNotEqual(product_ids, False)
        self.assertEqual(len(product_ids), 1)

        product = product_model.browse(cr, uid, product_ids[0])
        self.assertTrue(product.exists())
        self.assertEqual(product.category_id.id, properties['category_id'])
        self.assertEqual(product.sub_category_id.id, properties['sub_category_id'])
        self.assertEqual(product.size_id.id, properties['size_id'])
        self.assertEqual(product.type_id.id, properties['type_id'])
        self.assertEqual(product.status_id.id, properties['status_id'])
        self.assertEqual(product.service_id.id, properties['service_ids'][0])


    def test_when_false_properties(self):
        cr, uid, = self.cr, self.uid
        product_model = self.product_model

        properties = {
            'category_id': self._get_prop_id('lct_product_category_specialhandlingcode'),
            'service_ids': [self._get_prop_id('lct_product_service_cleaning')],
            'size_id': self._get_prop_id('lct_product_size_20'),

            # Sub-category, Type and Status should not be defined
            'sub_category_id': self._get_prop_id('lct_product_sub_category_transitsahel'),
            'type_id': self._get_prop_id('lct_product_type_reeferdg'),
            'status_id': self._get_prop_id('lct_product_status_empty'),
        }

        product_ids = product_model.get_products_by_properties(cr, uid, properties)
        self.assertNotEqual(product_ids, False)
        self.assertEqual(len(product_ids), 1)

        product = product_model.browse(cr, uid, product_ids[0])
        self.assertTrue(product.exists())
        self.assertEqual(product.category_id.id, properties['category_id'])
        self.assertEqual(product.size_id.id, properties['size_id'])
        self.assertEqual(product.service_id.id, properties['service_ids'][0])

        self.assertEqual(product.sub_category_id.id, False)
        self.assertEqual(product.type_id.id, False)
        self.assertEqual(product.status_id.id, False)


