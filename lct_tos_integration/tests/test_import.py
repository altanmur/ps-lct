from openerp.tests.common import TransactionCase
from openerp.osv import osv
from ftplib import FTP
from time import sleep
from itertools import combinations
import paramiko
import datetime


class TestImport(TransactionCase):

    def setUp(self):
        super(TestImport, self).setUp()
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
            inbound_path='InBound',
            outbound_path='test/transfer_complete'
        )
        self.config_id = self.ftp_config_model.create(cr, uid, config)
        self.ftp = FTP(host=config['addr'],user=config['user'], passwd=config['psswd'])

    def test_only_one_active(self):
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

    def create_xml(self):
        t = paramiko.Transport(("192.168.0.11", 22))
        t.connect(username="openerp", password="openerp")
        sftp = paramiko.SFTPClient.from_transport(t)
        file_path = __file__.split('test_import.py')[0]
        name = "VBL_"+datetime.datetime.now().strftime('%y%m%d')+"_000001.xml"
        sftp.put(file_path + "VBL_IN.xml", "/home/ftp/data/openerp/test/transfer_complete/"+name)
        name = "APP_"+datetime.datetime.now().strftime('%y%m%d')+"_000001.xml"
        sftp.put(file_path + "APP_IN.xml", "/home/ftp/data/openerp/test/transfer_complete/"+name)

    def test_import(self):
        cr, uid = self.cr, self.uid
        config, ftp = self.config, self.ftp
        ftp.cwd(config['outbound_path'])
        for file in ftp.nlst():
            try:
                ftp.delete(file)
            except:
                ftp.rmd(file)
        self.registry('res.partner').create(cr, uid, {'name': 'MSK'})
        inv_ids = self.invoice_model.search(cr, uid, [('type2','=','vessel')])
        if inv_ids:
            self.invoice_model.unlink(cr, uid, inv_ids)
        self.create_xml()
        self.ftp_config_model.button_import_data(cr, uid, [self.config_id])
        inv_ids = self.invoice_model.search(cr, uid, [('type2','=','vessel')])
        self.assertEqual(len(inv_ids),1,msg='Importing the xml file should create 1 invoice of type Vessel Billing')
        invoice = self.invoice_model.browse(cr, uid, inv_ids)[0]
        products = [line.product_id.name for line in invoice.invoice_line]
        expected_products = [u'Discharge import 40 F GP', u'Load export 20 E GP', u'Discharge import 20 F GP', u'Hatch cover move', u'Gearbox count']
        for expected_product in expected_products:
            self.assertTrue(expected_product in products,"Products should all be imported, missing '%s'" % expected_product)

        inv_ids = self.invoice_model.search(cr, uid, [('type2','=','appointment')])
        self.assertEqual(len(inv_ids),1,msg='Importing the xml file should create 1 invoice of type Appointment')
        invoice = self.invoice_model.browse(cr, uid, inv_ids)[0]
        products = [line.product_id.name for line in invoice.invoice_line]
        expected_products = [u'Storage import 20 F GP', u'Storage import 40 F GP', u'Reefer plugging import 20 F GP']
        print products
        for expected_product in expected_products:
            self.assertTrue(expected_product in products,"Products should all be imported, missing '%s'" % expected_product)
