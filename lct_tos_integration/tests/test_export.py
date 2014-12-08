from openerp.tests.common import TransactionCase
from openerp.osv import osv
import netsvc
from ftplib import FTP
import re
import lxml.etree as ET
import os
from StringIO import StringIO
import import_export_tools as iet

class TestExport(TransactionCase):

    def setUp(self):
        super(TestExport, self).setUp()
        self.ftp_config_model = self.registry('ftp.config')
        self.invoice_model = self.registry('account.invoice')
        cr, uid = self.cr, self.uid
        config_ids = self.ftp_config_model.search(cr, uid, [])
        self.config = config_ids and self.ftp_config_model.browse(cr, uid, config_ids)[0] or False
        if not self.config:
            return True
        self.ftp = FTP(host=self.config['addr'],user=self.config['user'], passwd=self.config['psswd'])

    def test_export(self):
        cr, uid = self.cr, self.uid
        if not self.config:
            return True
        ftp, config = self.ftp, self.config
        ftp_config_model = self.ftp_config_model
        iet.purge_ftp(ftp, path=config['outbound_path'], omit=['done'])
        iet.purge_ftp(ftp, path=config['inbound_path'])
        ftp.cwd(config['inbound_path'])

        partner_model = self.registry('res.partner')
        company_id = partner_model.create(cr, uid, {'name': 'New Company', 'is_company': True})
        files_before = iet.ls(ftp)
        self.assertTrue(len(files_before) == 1, 'Creating a new partner should upload an XML file')
        match = re.match("^.+(\d{6}).xml$", files_before[0])
        sequence = int(match.group(1))
        country_model = self.registry('res.country')
        country_id = country_model.search(cr, uid, [])[0]
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
        files_after = iet.ls(ftp)
        filename = ''

        self.assertTrue(len(files_after) == 2, 'Creating a new partner should upload an XML file')
        for cus_file in files_after:
            if cus_file != files_before[0]:
                filename = cus_file
                break
        match = re.match("^CUS_\d{6}_(\d{6}).xml$", filename)
        sequence2 = int(match.group(1))
        self.assertTrue(sequence2 == (sequence+1)%1000000)
        f = StringIO()
        ftp.retrlines('RETR ' + filename, f.write)

        f.seek(0)
        customers = ET.fromstring(f.getvalue())
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
            'country': country_model.browse(cr, uid, country_id).code,
            'email': vals['email'],
            'website': vals['website'],
            'phone': vals['phone']
        }
        for tag, val in expected_values.iteritems():
            self.assertTrue(customer.find(tag).text == val, 'Exported values should correspond to the record. Tag : %s' % tag)

        iet.purge_ftp(ftp, omit=['done'])

        inv_model = self.registry('account.invoice')
        inv_model.unlink(cr, uid, inv_model.search(cr, uid, [('state','=','draft')]))
        local_path = os.path.join(__file__.split(__file__.split(os.sep)[-1])[0], 'xml_files', 'APP_XML_files')
        file_name = os.listdir(local_path)[0]
        f = open(os.path.join(local_path, file_name))
        f = iet.set_appointment_customer(f, partner_id)
        ftp.cwd('/')
        ftp.cwd(config['outbound_path'])
        self.assertTrue(iet.upload_file(ftp, f, file_name))
        self.ftp_config_model.button_import_ftp_data(cr, uid, [self.config.id])
        inv_id = inv_model.search(cr, uid, [('state','=','draft')])[0]
