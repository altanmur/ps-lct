import paramiko
import datetime
import ipdb

name = "VBL_IN_"+datetime.datetime.now().strftime('%y-%m-%d')+"_SEQ000001.xml"
t = paramiko.Transport(("192.168.0.11", 22))
t.connect(username="openerp", password="openerp")
sftp = paramiko.SFTPClient.from_transport(t)
file_path = __file__.split('create_xml.py')[0]
sftp.put(file_path + "VBL_IN.xml", "/home/ftp/data/openerp/test/"+name)
