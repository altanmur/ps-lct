import paramiko
import datetime

t = paramiko.Transport(("192.168.0.11", 22))
t.connect(username="openerp", password="openerp")
sftp = paramiko.SFTPClient.from_transport(t)
file_path = __file__.split('create_xml.py')[0]
name = "VBL_IN_"+datetime.datetime.now().strftime('%y-%m-%d')+"_SEQ000001.xml"
sftp.put(file_path + "VBL_IN.xml", "/home/ftp/data/openerp/test/transfer_complete/"+name)
name = "APP_IN_"+datetime.datetime.now().strftime('%y-%m-%d')+"_SEQ000001.xml"
sftp.put(file_path + "APP_IN.xml", "/home/ftp/data/openerp/test/transfer_complete/"+name)
