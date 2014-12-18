# -*- coding: utf-8 -*-

from osv import fields, osv
from lxml import etree
import StringIO
import csv
from openerp.tools import ustr
import codecs, cStringIO
import base64

class UnicodeWriter:
    """
    A CSV writer which will write rows to CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        # Redirect output to a queue
        self.queue = cStringIO.StringIO()
        self.writer = csv.writer(self.queue, delimiter=',', dialect=dialect, **kwds)
        self.stream = f
        self.encoder = codecs.getincrementalencoder(encoding)()

    def writerow(self, row):
        row = [s.replace('\n', ' ').replace('\r', '') for s in row]
        self.writer.writerow([s.encode("utf-8") if s else s for s in row])
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        data = data.decode("utf-8")
        # ... and reencode it into the target encoding
        data = self.encoder.encode(data)
        # write to the target stream
        self.stream.write(data)
        # empty queue
        self.queue.truncate(0)

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)

def optimized_write_csv(info_to_write):
    """
        Write a specific structure into an excel file
    """
    output = StringIO.StringIO()
    c = UnicodeWriter(output)
    for content in info_to_write:
        content = map(ustr, content)
        c.writerow(content)
    return output

class export_article_id(osv.osv_memory):
    _name = "lct.export.button"

    _columns = {
        'name': fields.char("Name"),
        'xls_file' : fields.binary("File",readonly=True),
        'datas_fname' : fields.char("File Name",64),
        'state' : fields.selection([('draft', 'Draft'),('done', 'Done')], string="status"),
    }

    _defaults = {
        'state' : 'draft',
    }

    def get_groups(self, root):
        groups = []
        if root.xpath("//button"):
            if "groups" in root.attrib:
                groups.append(root.attrib['groups'])
            for elmt in list(root):
                groups.extend(self.get_groups(elmt))
        return groups

    def export_button(self, cr, uid, ids, context=None):
        view_obj = self.pool.get("ir.ui.view")
        view_ids = view_obj.search(cr, uid, [('type', 'in', ['tree', 'form'])])

        to_write = []
        to_write.append(['Button Name', 'Button String', 'View Name', 'View Type', 'Model', 'Groups'])
        for view in view_obj.read(cr, uid, view_ids, ['name', 'type', 'model', 'arch']):
            view_xml = etree.fromstring(isinstance(view['arch'], unicode) and view['arch'].encode('utf8') or view['arch'])
            buttons = view_xml.xpath("//button")
            if buttons:
                for button in buttons:
                    groups = self.get_groups(view_xml)
                    if 'groups' in button.attrib:
                        groups.append(button.attrib['groups'])
                    groups = list(set(groups))
                    button_export = []
                    button_export.append('name' in button.attrib and button.attrib['name'] or "")
                    button_export.append('string' in button.attrib and button.attrib['string'] or "")
                    button_export.append(view['name'])
                    button_export.append(view['type'])
                    button_export.append(view['model'])
                    button_export.append(','.join(groups))
                    to_write.append(button_export)

        out = optimized_write_csv(to_write)

        output_filename = "export_button.csv"

        encode_text = base64.encodestring(out.getvalue())
        self.write(cr, uid, ids, {
            'xls_file': encode_text,
            'state': 'done',
            'datas_fname': output_filename
        }, context=context)

        return {
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'lct.export.button',
            'res_id': ids[0],
            'type': 'ir.actions.act_window',
            'target': 'new',
        }
