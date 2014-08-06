from openerp.tests.common import TransactionCase
from openerp.osv import osv
from ftplib import FTP
import re
import xml.etree.ElementTree as ET
import os

class TestExport(TransactionCase):

    def setUp(self):
        super(TestExport, self).setUp()
        self.ftp_config_model = self.registry('ftp.config')
        self.invoice_model = self.registry('account.invoice')
        cr, uid = self.cr, self.uid
        config_ids = self.ftp_config_model.search(cr, uid, [])
        self.ftp_config_model.unlink(cr, uid, config_ids)
        self.config = config = dict(
            name="Config",
            active=True,
            addr='192.168.0.11',
            user='openerp',
            psswd='Azerty01',
            inbound_path='test',
            outbound_path='test'
        )
        self.config_id = self.ftp_config_model.create(cr, uid, config)
        self.ftp = FTP(host=config['addr'],user=config['user'], passwd=config['psswd'])


    def test_export(self):
        cr, uid = self.cr, self.uid
        ftp, config = self.ftp, self.config
        ftp.cwd(config['inbound_path'] + '/transfer_complete')
        for f in ftp.nlst():
            try:
                ftp.delete(f)
            except:
                ftp.rmd(f)
        partner_model = self.registry('res.partner')
        company_id = partner_model.create(cr, uid, {'name': 'New Company', 'is_company': True})
        files_before = ftp.nlst()
        self.assertTrue(len(files_before) == 1, 'Creating a new partner should upload an XML file')
        match = re.match("^.+SEQ(\d{6}).xml$", files_before[0])
        self.assertTrue(match is not None, 'Bad filename format')
        sequence = int(match.group(1))
        country_id = self.registry('res.country').create(cr, uid, {'name': 'New Country'})
        vals = {
            'name': 'New customer',
            'street': 'Street 1',
            'street2': 'Street 2',
            'ref': 'REF0',
            'parent_id': company_id,
            'city': 'City',
            'zip': '1000',
            'country_id': country_id,
            'email': 'email@domain.com',
            'website': 'www.domain.com',
            'phone': '0454545454',
        }
        partner_id = partner_model.create(cr, uid, vals)
        files_after = ftp.nlst()
        filename = ''

        self.assertTrue(len(files_after) == 2, 'Creating a new partner should upload an XML file')
        for file in files_after:
            if file != files_before[0]:
                filename = file
                break
        match = re.match("^CUS_CREATE_\d{6}_SEQ(\d{6}).xml$", filename)
        self.assertTrue(match is not None, 'Bad filename format')
        sequence2 = int(match.group(1))
        self.assertTrue(sequence2 == (sequence+1)%1000000)
        local_path = __file__.split(__file__.split('/')[-1])[0]
        with open(local_path + filename, 'w+') as f:
            ftp.retrlines('RETR ' + filename, f.write)
        tree = ET.parse(local_path + filename)
        customers = tree.getroot()
        customer = customers.findall('customer')
        self.assertTrue(len(customer) == 1, 'There should be one and only one customer in the xml file when one customer is created')
        customer = customer[0]
        expected_values = {
            'customer_id': vals['name'],
            'customer_key': vals['ref'],
            'name': 'New Company',
            'street': vals['street'] + ', ' + vals['street2'],
            'city': vals['city'],
            'zip': vals['zip'],
            'country': 'New Country',
            'email': vals['email'],
            'website': vals['website'],
            'phone': vals['phone']
        }

        for tag, val in expected_values.iteritems():
            self.assertTrue(customer.find(tag).text == val, 'Exported values should correspond to the record')
        os.remove(local_path + filename)



    # def test_only_one_active(self):
    #     cr, uid = self.cr, self.uid
    #     config2 = dict(
    #         name="Config2",
    #         active=True,
    #         addr='Address',
    #         user='user',
    #         psswd='password',
    #         inbound_path='in_path',
    #         outbound_path='out_path'
    #         )
    #     with self.assertRaises(Exception,
    #         msg='Creating a second active config should raise an error'):
    #         self.ftp_config_model.create(cr, uid, config2)

    # def test_import(self):
    #     cr, uid = self.cr, self.uid
    #     config, ftp = self.config, self.ftp
    #     ftp.cwd(config['outbound_path'] + '/transfer_complete')
    #     for file in ftp.nlst():
    #         try:
    #             ftp.delete(file)
    #         except:
    #             ftp.rmd(file)
    #     self.registry('res.partner').create(cr, uid, {'name': 'MSK'})
    #     inv_ids = self.invoice_model.search(cr, uid, [('type2','=','vessel')])
    #     if inv_ids:
    #         self.invoice_model.unlink(cr, uid, inv_ids)
    #     import create_xml
    #     sleep(0.1)
    #     self.ftp_config_model.button_import_data(cr, uid, [self.config_id])
    #     inv_ids = self.invoice_model.search(cr, uid, [('type2','=','vessel')])
    #     self.assertEqual(len(inv_ids),1,msg='Importing the xml file should create 1 invoice')
    #     invoice = self.invoice_model.browse(cr, uid, inv_ids)[0]
    #     products = [line.product_id.name for line in invoice.invoice_line]
    #     expected_products = [u'Discharge import 40 F GP', u'Load export 20 E GP', u'Discharge import 20 F GP', u'Hatch cover move', u'Gearbox count']
    #     for expected_product in expected_products:
    #         self.assertTrue(expected_product in products,"Products should all be imported, missing '%s'" % expected_product)