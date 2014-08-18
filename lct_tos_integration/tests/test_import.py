from openerp.tests.common import TransactionCase
from openerp.osv import osv
import paramiko
import os
from lxml import etree as ET


class TestImport(TransactionCase):

    def setUp(self):
        super(TestImport, self).setUp()
        self.ftp_config_model = self.registry('ftp.config')
        self.invoice_model = self.registry('account.invoice')
        self.partner_model = self.registry('res.partner')
        cr, uid = self.cr, self.uid
        config_ids = self.ftp_config_model.search(cr, uid, [])
        self.ftp_config_model.unlink(cr, uid, config_ids)
        self.config = config = dict(
            name="Config",
            active=True,
            addr='192.168.0.11',
            user='openerp',
            psswd='Azerty01',
            inbound_path='test_inbound/transfer_complete',
            outbound_path='test_outbound/transfer_complete'
        )
        self.config_id = self.ftp_config_model.create(cr, uid, config)

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

    def _prepare_import(self):
        t = paramiko.Transport(("192.168.0.11", 22))
        t.connect(username="openerp", password="openerp")
        sftp = paramiko.SFTPClient.from_transport(t)
        outbound_path = "/home/ftp/data/openerp/" + self.config['outbound_path'] + '/'
        for outbound_file in sftp.listdir(outbound_path):
            if outbound_file == 'logs':
                for log_file in sftp.listdir(outbound_path + outbound_file):
                    try:
                        sftp.remove(outbound_path + outbound_file + '/' + log_file)
                    except:
                        pass
            try:
                sftp.remove(outbound_path + outbound_file)
            except:
                pass
        xml_dirs = ['APP_XML_files']
        local_path_path = os.path.join(__file__.split(__file__.split('/')[-1])[0], 'xml_files')
        for xml_dir in xml_dirs:
            local_path = os.path.join(local_path_path,xml_dir)
            for xml_file in os.listdir(local_path):
                xml_abs_file = os.path.join(local_path, xml_file)
                sftp.put(xml_abs_file, outbound_path + xml_file)

    def _assertNoLogs(self):
        t = paramiko.Transport(("192.168.0.11", 22))
        t.connect(username="openerp", password="openerp")
        sftp = paramiko.SFTPClient.from_transport(t)
        log_path = "/home/ftp/data/openerp/" + self.config['outbound_path'] + '/logs/'
        self.assertTrue(not sftp.listdir(log_path), 'Importing valid files should be successful')

    def test_import(self):
        cr, uid = self.cr, self.uid
        self._prepare_import()
        inv_ids = self.invoice_model.search(cr, uid, ['|',('type2','=','vessel'),('type2','=','appointment')])
        if inv_ids:
            self.invoice_model.unlink(cr, uid, inv_ids)
        self.ftp_config_model.button_import_ftp_data(cr, uid, [self.config_id])
        vessel_ids = self.invoice_model.search(cr, uid, [('type2','=','vessel')])
        self._assertNoLogs()
