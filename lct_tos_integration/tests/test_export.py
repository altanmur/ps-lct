from openerp.tests.common import TransactionCase
from openerp.osv import osv
from ftplib import FTP
import re
import lxml.etree as ET
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
            addr='10.10.0.9',
            user='openerp',
            psswd='Azerty01',
            inbound_path='test_inbound/transfer_complete',
            outbound_path='test_outbound/transfer_complete'
        )
        self.config_id = self.ftp_config_model.create(cr, uid, config)
        self.ftp = FTP(host=config['addr'],user=config['user'], passwd=config['psswd'])


    def test_export(self):
        cr, uid = self.cr, self.uid
        ftp, config = self.ftp, self.config
        ftp.cwd(config['inbound_path'])
        for f in ftp.nlst():
            try:
                ftp.delete(f)
            except:
                ftp.rmd(f)
        partner_model = self.registry('res.partner')
        company_id = partner_model.create(cr, uid, {'name': 'New Company', 'is_company': True})
        files_before = ftp.nlst()
        self.assertTrue(len(files_before) == 1, 'Creating a new partner should upload an XML file')
        match = re.match("^.+(\d{6}).xml$", files_before[0])
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
        match = re.match("^CUS_\d{6}_(\d{6}).xml$", filename)
        sequence2 = int(match.group(1))
        self.assertTrue(sequence2 == (sequence+1)%1000000)
        local_path = __file__.split(__file__.split('/')[-1])[0]
        with open(local_path + filename, 'w+') as f:
            ftp.retrlines('RETR ' + filename, f.write)
        try:
            tree = ET.parse(local_path + filename)
            customers = tree.getroot()
            customer = customers.findall('customer')
            self.assertTrue(len(customer) == 1, 'There should be one and only one customer in the xml file when one customer is created')
            customer = customer[0]
            expected_values = {
                'customer_id': str(partner_id),
                'customer_key': vals['ref'],
                'name': vals['name'],
                'street': vals['street'] + ', ' + vals['street2'],
                'city': vals['city'],
                'zip': vals['zip'],
                'country': 'New Country',
                'email': vals['email'],
                'website': vals['website'],
                'phone': vals['phone']
            }

            for tag, val in expected_values.iteritems():
                self.assertTrue(customer.find(tag).text == val, 'Exported values should correspond to the record. Tag : %s' % tag)
            os.remove(local_path + filename)
        except:
            os.remove(local_path + filename)
            raise
