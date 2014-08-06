from openerp.tests.common import TransactionCase
from openerp.osv import osv
from ftplib import FTP


class TestExport(TransactionCase):

    def setUp(self):
        setUp(TestExport, self).setUp()