from openerp.tests.common import TransactionCase
from openerp.osv import osv
import os
from ftplib import FTP
from lxml import etree as ET


class TestImport(TransactionCase):

    def setUp(self):
        super(TestImport, self).setUp()
        self.ftp_config_model = self.registry('ftp.config')
        self.invoice_model = self.registry('account.invoice')
        self.partner_model = self.registry('res.partner')
        self.import_data_model = self.registry('lct.tos.import.data')
        cr, uid = self.cr, self.uid
        config_ids = self.ftp_config_model.search(cr, uid, [])
        self.ftp_config_model.unlink(cr, uid, config_ids)
        self.config = config = dict(
            name="Config",
            active=True,
            addr='10.10.0.9',
            user='openerp',
            psswd='Azerty01',
            inbound_path='test_inbound/transfer_complete',
            outbound_path='test_outbound/transfer_complete'
        )
        self.config_id = self.ftp_config_model.create(cr, uid, config)
        currency_id = self.registry('res.currency').search(cr, uid, [('name','=','XOF')])[0]
        self.registry('res.company').write(cr, uid, 1, {'currency_id': currency_id})
        self.registry('product.price.type').write(cr, uid, 1, {'currency_id': currency_id})
        self.registry('product.price.type').write(cr, uid, 2, {'currency_id': currency_id})


    def test_only_one_active_config(self):
        cr, uid = self.cr, self.uid
        config2 = dict(
            name="Config2",
            active=True,
            addr='Address',
            user='user',
            psswd='password',
            inbound_path='in_path',
            outbound_path='out_path'
            )
        with self.assertRaises(Exception,
                msg='Creating a second active config should raise an error'):
            self.ftp_config_model.create(cr, uid, config2)

    def _create_pricelist(self):
        cr, uid = self.cr, self.uid
        pricelist_model = self.registry('product.pricelist')
        product_model = self.registry('product.product')
        product_id = product_model.search(cr, uid, [('name','=','GP STORAGE 20 EXPORT FULL')])[0]
        product_model.write(cr, uid, [product_id], {'list_price': 50.})
        tariff_rate_vals = [
            (0,0,{
                'product_id': product_id,
                'min_quantity': 0,
                'sequence': 1,
                'slab_rate': True,
                'price_discount_rate1': -0.5,
                'price_discount_rate2': -0.25,
                'price_discount_rate3': 0.,
                'free_period': 5,
                'first_slab_last_day': 10,
                'second_slab_last_day': 15,
                'base': 1,
            }),
        ]
        product_id = product_model.search(cr, uid, [('name','=','GP REEFER 20 EXPORT FULL')])[0]
        product_model.write(cr, uid, [product_id], {'list_price': 16.})
        tariff_rate_vals.append(
            (0,0,{
                'product_id': product_id,
                'min_quantity': 0,
                'sequence': 1,
                'slab_rate': True,
                'price_discount_rate1': -0.4,
                'price_discount_rate2': -0.3,
                'price_discount_rate3': 0.,
                'free_period': 5,
                'first_slab_last_day': 10,
                'second_slab_last_day': 15,
                'base': 1,
            })
        )
        product_id = product_model.search(cr, uid, [('name','=','GP REEFER 40 IMPORT FULL')])[0]
        product_model.write(cr, uid, [product_id], {'list_price': 58.})
        tariff_rate_vals.append(
            (0,0,{
                'product_id': product_id,
                'min_quantity': 0,
                'sequence': 1,
                'slab_rate': True,
                'price_discount_rate1': -0.6,
                'price_discount_rate2': -0.2,
                'price_discount_rate3': 0.,
                'free_period': 5,
                'first_slab_last_day': 10,
                'second_slab_last_day': 15,
                'base': 1,
            })
        )
        product_id = product_model.search(cr, uid, [('name','=','GP DISCHARGE 20 IMPORT FULL')])[0]
        product_model.write(cr, uid, [product_id], {'list_price': 15.})
        tariff_rate_vals.append(
            (0,0,{
                'product_id': product_id,
                'min_quantity': 0,
                'sequence': 1,
                'slab_rate': False,
                'price_discount': -0.25,
                'base': 1,
            })
        )
        product_id = product_model.search(cr, uid, [('name','=','GP DISCHARGE 40 IMPORT FULL')])[0]
        product_model.write(cr, uid, [product_id], {'list_price': 20.})
        tariff_rate_vals.append(
            (0,0,{
                'product_id': product_id,
                'min_quantity': 0,
                'sequence': 1,
                'slab_rate': False,
                'price_discount': -0.5,
                'base': 1,
            })
        )
        product_id = product_model.search(cr, uid, [('name','=','Gearbox count')])[0]
        product_model.write(cr, uid, [product_id], {'list_price': 11.})
        tariff_rate_vals.append(
            (0,0,{
                'product_id': product_id,
                'min_quantity': 0,
                'sequence': 1,
                'slab_rate': False,
                'price_discount': -0.3,
                'base': 1,
            })
        )
        product_id = product_model.search(cr, uid, [('name','=','Hatch cover move')])[0]
        product_model.write(cr, uid, [product_id], {'list_price': 13.})
        tariff_rate_vals.append(
            (0,0,{
                'product_id': product_id,
                'min_quantity': 0,
                'sequence': 1,
                'slab_rate': False,
                'price_discount': -0.4,
                'base': 1,
            })
        )
        tariff_vals = [
            (0,0,{
                'name': 'Test Tariff',
                'items_id': tariff_rate_vals,
            }),
        ]
        tariff_template_vals = {
            'name': 'Test Tariff Template',
            'currency_id': 42,
            'type': 'sale',
            'version_id': tariff_vals,
        }
        pricelist_model.create(cr, uid, tariff_template_vals)
        self.pricelist = pricelist_model.browse(cr, uid, pricelist_model.create(cr, uid, tariff_template_vals))

    def _prepare_import(self):
        cr, uid = self.cr, self.uid
        config = self.config
        self._create_pricelist()
        self.partner_id = self.partner_model.create(cr, uid,{
            'name': 'Test Customer',
            'property_product_pricelist': self.pricelist.id,
            })
        ftp = FTP(host=config['addr'], user=config['user'], passwd=config['psswd'])
        ftp.cwd(config['outbound_path'])
        for outbound_file in ftp.nlst():
            if outbound_file != "done":
                try:
                    ftp.delete(outbound_file)
                except:
                    ftp.rmd(outbound_file)
        xml_dirs = ['APP_XML_files', 'VBL_XML_files']
        local_path_path = os.path.join(__file__.split(__file__.split(os.sep)[-1])[0], 'xml_files')
        config = self.config
        ftp = FTP(host=config['addr'], user=config['user'], passwd=config['psswd'])
        ftp.cwd(config['outbound_path'])
        for outbound_file in ftp.nlst():
            if outbound_file != "done":
                try:
                    ftp.delete(outbound_file)
                except:
                    ftp.rmd(outbound_file)
        local_path_path = os.path.join(__file__.split(__file__.split(os.sep)[-1])[0], 'xml_files')
        app_dir = os.path.join(local_path_path, 'APP_XML_files')
        for xml_file in (os.path.join(app_dir, file_name) for file_name in  os.listdir(app_dir)):
            tree = ET.parse(open(xml_file))
            root = tree.getroot()
            for appoint in root.findall('appointment'):
                appoint.find('customer_id').text = str(self.partner_id)
            open(xml_file, 'w+').write(ET.tostring(tree, pretty_print=True))
        vbl_dir = os.path.join(local_path_path, 'VBL_XML_files')
        for xml_file in (os.path.join(vbl_dir, file_name) for file_name in  os.listdir(vbl_dir)):
            tree = ET.parse(open(xml_file))
            root = tree.getroot()
            for vessel in root.findall('vbilling'):
                vessel.find('vessel_operator_id').text = str(self.partner_id)
            open(xml_file, 'w+').write(ET.tostring(tree, pretty_print=True))
        xml_dirs = [app_dir, vbl_dir]
        for xml_dir in xml_dirs:
            for xml_file in os.listdir(xml_dir):
                xml_abs_file = os.path.join(xml_dir, xml_file)
                ftp.storlines(''.join(['STOR ', xml_file]), open(xml_abs_file))

    def test_import(self):
        cr, uid = self.cr, self.uid
        ftp_config_model = self.ftp_config_model
        invoice_model, import_data_model = self.invoice_model, self.import_data_model
        product_model = self.registry('product.product')
        self._prepare_import()
        vessel_ids = self.invoice_model.search(cr, uid, [('type2','=','vessel')])
        appoint_ids = self.invoice_model.search(cr, uid, [('type2','=','appointment')])
        data_ids = import_data_model.search(cr, uid, [])
        if data_ids:
            import_data_model.unlink(cr, uid, data_ids)
        ftp_config_model.button_import_ftp_data(cr, uid, [self.config_id])

        appoints = invoice_model.browse(cr, uid, invoice_model.search(cr, uid, [('type2','=','appointment'), ('id', 'not in', appoint_ids)], order='appoint_ref'))
        self.assertTrue(len(appoints) == 2, 'Importing should create 2 appointments')
        self.assertTrue(appoints[0].appoint_ref == 'LCT2014062400289', 'Importing should create an appointment with reference: LCT2014062400289')
        lines = sorted(appoints[0].invoice_line, key=lambda x: x.name.lower())
        self.assertTrue(len(lines) == 3)
        self.assertTrue(lines[0].name == 'GP REEFER 20 EXPORT FULL')
        self.assertTrue(lines[0].quantity == 1)
        self.assertTrue(lines[0].price_unit == 70.4)
        self.assertTrue(lines[1].name == 'GP REEFER 40 IMPORT FULL')
        self.assertTrue(lines[1].quantity == 1)
        self.assertTrue(lines[1].price_unit == 464.)
        self.assertTrue(lines[2].name == 'GP STORAGE 20 EXPORT FULL')
        self.assertTrue(lines[2].quantity == 2)
        self.assertTrue(lines[2].price_unit == 281.25)
        self.assertTrue(appoints[1].appoint_ref == 'LCT2014070900019', 'Importing should create an appointment with reference: LCT2014070900019')
        self.assertTrue(len(appoints[1].invoice_line) == 0)

        vessels = invoice_model.browse(cr, uid, invoice_model.search(cr, uid, [('type2','=','vessel'), ('id', 'not in', vessel_ids)], order='call_sign'))
        self.assertTrue(len(vessels) == 1, 'Importing should create 1 vessel billing')
        self.assertTrue(vessels[0].call_sign == 'CALLSIGN000', 'Importing should create an appointment with reference: CALLSIGN000')

        lines = sorted(vessels[0].invoice_line, key=lambda x: x.name.lower())
        self.assertTrue(len(lines) == 4)

        self.assertTrue(lines[0].name == 'Gearbox count')
        self.assertTrue(lines[0].quantity == 14)
        self.assertTrue(lines[0].price_unit == 7.7)
        self.assertTrue(lines[1].name == 'GP DISCHARGE 20 IMPORT FULL')
        self.assertTrue(lines[1].quantity == 1)
        self.assertTrue(lines[1].price_unit == 11.25)
        self.assertTrue(lines[2].name == 'GP DISCHARGE 40 IMPORT FULL')
        self.assertTrue(lines[2].quantity == 1)
        self.assertTrue(lines[2].price_unit == 10.)
        self.assertTrue(lines[3].name == 'Hatch cover move')
        self.assertTrue(lines[3].quantity == 6)
        self.assertTrue(lines[3].price_unit == 7.8)


