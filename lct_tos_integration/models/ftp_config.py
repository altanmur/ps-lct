# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-TODAY OpenERP S.A. <http://www.openerp.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import fields, osv
from ftplib import FTP
from lxml import etree as ET
import os
from datetime import datetime
import re
import io

class ftp_config(osv.osv):
    _name="ftp.config"

    _columns = {
        'name': fields.char('Name', required=True),
        'addr': fields.char('Server Address', required=True),
        'user': fields.char('Username', required=True),
        'psswd': fields.char('Password', required=True),
        'inbound_path': fields.char('Path of inbound folder', required=True),
        'outbound_path': fields.char('Path of outbound folder', required=True),
        'active': fields.boolean('Active'),
        'last_import': fields.date('Last Import', readonly=True)
    }

    def _check_active(self, cr, uid, ids, context=None):
        config_ids = self.search(cr, uid, [('active','=',True)], context=context)
        return len(config_ids) <= 1

    _constraints = [
        (_check_active, 'There can only be one active ftp configuration', ['active']),
    ]

    # Data Import

    def _get_elmnt_text(self, elmnt, tag):
        sub_elmnt = elmnt.find(tag)
        if sub_elmnt is not None:
            return sub_elmnt.text
        else:
            raise osv.except_osv(('Error in file %s' % self.curr_file),('Unable to find tag %s\nin element : %s' % (tag, elmnt.tag)))

    def _get_product_info(self, cr, uid, model, field, value, label):
        ids = self.pool.get(model).search(cr, uid, [(field, '=', value)])
        if not ids:
            if value:
                raise osv.except_osv(('Error in file %s' % self.curr_file), ('The following information (%s = %s) does not exist') % (label, value))
            else:
                raise osv.except_osv(('Error in file %s' % self.curr_file), ('The following information (%s) was not found') % (label,))
        return ids[0]

    def _get_product_properties(self, cr, uid, line, product_map, context=None):
        product_properties = {}

        category = self._get_elmnt_text(line, product_map['category_id'])
        category_name = 'Import' if category == 'I' else 'Export' if category == 'E' else False
        if not category_name:
            raise osv.except_osv(('Error in file %s' % self.curr_file), ('Some information (category_id) could not be found on product'))
        product_properties['category_id'] = {
            'name': category_name,
            'id': self._get_product_info(cr, uid, 'lct.product.category', 'name', category_name, 'Category')
        }

        size_size = int(self._get_elmnt_text(line, product_map['size_id']))
        product_properties['size_id'] = {
            'name': size_size,
            'id': self._get_product_info(cr, uid, 'lct.product.size', 'size', size_size, 'Size')
        }

        status = self._get_elmnt_text(line, product_map['status_id'])
        status_name = 'Full' if status == 'F' \
            else 'Empty' if status == 'E' \
            else False
        product_properties['status_id'] = {
            'name': status_name,
            'id': self._get_product_info(cr, uid, 'lct.product.status', 'name', status_name, 'Status')
        }

        type_name = self._get_elmnt_text(line, product_map['type_id'])
        product_properties['type_id'] = {
            'name': type_name,
            'id': self._get_product_info(cr, uid, 'lct.product.type', 'name', type_name, 'Type')
        }

        return product_properties

    def _get_app_lines(self, cr, uid, lines, line_map, context=None):
        product_model = self.pool.get('product.product')
        if len(lines) < 1:
            return []

        lines_vals = {}
        for line in lines.findall('line'):
            product_properties = self._get_product_properties(cr, uid, line, line_map['product_map'], context=context)
            services = {
                'Storage': self._get_elmnt_text(line, 'storage'),
                'Reefer': self._get_elmnt_text(line, 'plugged_time'),
            }
            for service, quantity in services.iteritems():
                if quantity and int(quantity) > 0:
                    product_properties['service_id'] = {
                        'name': service,
                        'id': self._get_product_info(cr, uid, 'lct.product.service', 'name', service, 'Status')
                    }
                    product_domain = [(name, '=', product_properties[name]['id']) for name in ['category_id', 'size_id', 'status_id', 'type_id', 'service_id']]
                    product_ids = product_model.search(cr, uid, product_domain, context=context)
                    product = product_ids and product_model.browse(cr, uid, product_ids, context=context)[0] or False
                    if not product:
                        raise osv.except_osv(('Error in file %s' % self.curr_file), ('No product could be found for this combination : '
                                '\n category_id : %s \n service_id : %s \n size_id : %s \n status_id : %s \n type_id : %s' % \
                                tuple(product_properties[name]['name'] for name in ['category_id',  'service_id', 'size_id', 'status_id', 'type_id'])))
                    try:
                        cont_nr_name = line.find('container_number').text
                        cont_nr_mgc_nr = (0,0,{'name': cont_nr_name})
                    except:
                        raise osv.except_osv(('Error in file %s' % self.curr_file), ('Could not find the container number'))

                    if product.name in lines_vals:
                        lines_vals[product.name]['quantity'] += int(quantity)
                        lines_vals[product.name]['cont_nr_ids'].extend([cont_nr_mgc_nr] * int(quantity))
                    else:
                        vals = {}
                        for field, tag in line_map.iteritems():
                            if isinstance(tag, str):
                                vals[field] = self._get_elmnt_text(line,tag)
                        vals['cont_nr_ids'] = [cont_nr_mgc_nr] * int(quantity)
                        account = product.property_account_income or (product.categ_id and product.categ_id.property_account_income_categ) or False
                        if account:
                            vals['account_id'] = account.id
                        else:
                            raise osv.except_osv(('Error in file %s' % self.curr_file), ('Could not find an income account on product %s ') % product.name)
                        vals.update({
                            'product_id': product.id,
                            'name' : product.name,
                            'price_unit': product.list_price,
                            'quantity': int(quantity),
                        })
                        lines_vals[product.name] = vals
        return [(0,0,vals) for vals in lines_vals.values()]

    def _get_vbl_lines(self, cr, uid, lines, line_map, context=None):
        product_model = self.pool.get('product.product')
        if len(lines) < 1:
            return []

        lines_vals = {}
        for line in lines.findall('line'):
            category = self._get_elmnt_text(line, line_map['product_map']['category_id'])
            if category == 'I':
                category_name, service_name = 'Import', 'Discharge'
            elif category == 'E':
                category_name, service_name = 'Export', 'Load'
            else:
                raise osv.except_osv(('Error in file %s' % self.curr_file), ('Some information (category_id) could not be found on product'))
            category_id = self._get_product_info(cr, uid, 'lct.product.category', 'name', category_name, 'Category Type')
            service_id = self._get_product_info(cr, uid, 'lct.product.service', 'name', service_name, 'Service')

            size_size = int(self._get_elmnt_text(line,line_map['product_map']['size_id']))
            size_id = self._get_product_info(cr, uid, 'lct.product.size', 'size', size_size, 'Size')

            status = self._get_elmnt_text(line,line_map['product_map']['status_id'])
            status_name = 'Full' if status == 'F' \
                else 'Empty' if status == 'E' \
                else False
            status_id = self._get_product_info(cr, uid, 'lct.product.status', 'name', status_name, 'Status')

            type_name = 'GP' if self._get_elmnt_text(line,line_map['product_map']['type_id']) == 'GP' \
                else False

            type_id = self._get_product_info(cr, uid, 'lct.product.type', 'name', type_name, 'Type')

            product_domain = [(name, '=', eval(name)) for name in ['category_id', 'service_id', 'size_id', 'status_id', 'type_id']]
            product_ids = product_model.search(cr, uid, product_domain, context=context)
            product = product_ids and product_model.browse(cr, uid, product_ids, context=context)[0] or False
            if not product:
                raise osv.except_osv(('Error in file %s' % self.curr_file), ('No product could be found for this combination : '
                        '\n category_id : %s \n service_id : %s \n size_id : %s \n status_id : %s \n type_id : %s' % \
                        (category_name, service_name, size_size, status_name, type_name)))
            try:
                cont_nr_name = line.find('container_number').text
                cont_nr_mgc_nr = (0,0,{'name': cont_nr_name})
            except:
                raise osv.except_osv(('Error in file %s' % self.curr_file), ('Could not find the container number'))

            if product.name in lines_vals:
                lines_vals[product.name]['quantity'] += 1
                lines_vals[product.name]['cont_nr_ids'].append(cont_nr_mgc_nr)
            else:
                vals = {}
                for field, tag in line_map.iteritems():
                    if isinstance(tag, str):
                        vals[field] = self._get_elmnt_text(line,tag)
                vals['cont_nr_ids'] = [cont_nr_mgc_nr]
                account = product.property_account_income or (product.categ_id and product.categ_id.property_account_income_categ) or False
                if account:
                    vals['account_id'] = account.id
                else:
                    raise osv.except_osv(('Error in file %s' % self.curr_file), ('Could not find an income account on product %s ') % product.name)
                vals.update({
                    'product_id': product.id,
                    'name' : product.name,
                    'price_unit': product.list_price,
                    'quantity': 1,
                })
                lines_vals[product.name] = vals
        return [(0,0,vals) for vals in lines_vals.values()]

    def _get_invoice_vals(self, cr, uid, invoice, invoice_type, context=None):
        invoice_map = {
            'partner_id': 'customer_id',
            'appoint_ref': 'appointment_reference',
            'appoint_date': 'appointment_date',
            'date_due': 'pay_through_date',
            'line_map':  {
                'product_map':{
                    'category_id': 'category',
                    'size_id': 'container_size',
                    'status_id': 'status',
                    'type_id': 'container_type',
                },
                'cont_operator': 'container_operator',
            },
        } if invoice_type == 'app' \
        else {
            'partner_id': 'vessel_operator_id',
            'call_sign': 'call_sign',
            'lloyds_nr': 'lloyds_number',
            'vessel_ID': 'vessel_id',
            'berth_time': 'berthing_time',
            'dep_time': 'departure_time',
            'line_map':  {
                'product_map':{
                    'category_id': 'transaction_category_id',
                    'size_id': 'container_size',
                    'status_id': 'container_status',
                    'type_id': 'container_type_id',
                },
                'cont_operator': 'container_operator_id',
            },
        }

        partner_model = self.pool.get('res.partner')
        vals = {}
        for field, tag in invoice_map.iteritems():
            if isinstance(tag, str):
                vals[field] = self._get_elmnt_text(invoice, tag)

        if not vals['partner_id'].isdigit():
            raise osv.except_osv(('Error in file %s' % self.curr_file), ('customer_id should be an integer'))
        partner_ids = partner_model.search(cr, uid, [('id', '=', int(vals['partner_id']))], context=context)
        if partner_ids:
            vals['partner_id'] = partner_ids[0]
        else:
            raise osv.except_osv(('Error in file %s' % self.curr_file), ('No customer with this name (%s) was found' % vals['partner_id'] ))

        invoice_line = self._get_app_lines(cr, uid, invoice.find('lines'), invoice_map['line_map'], context=context) \
                if invoice_type == 'app' \
                else self._get_vbl_lines(cr, uid, invoice.find('lines'), invoice_map['line_map'], context=context)

        partner  = partner_model.browse(cr, uid, vals['partner_id'], context=context)
        account = partner.property_account_receivable
        if account:
            vals['account_id'] = account.id
        else:
            raise osv.except_osv(('Error in file %s' % self.curr_file), ('No account receivable could be found on cutomer %s' % partner.name))

        vals.update({
            'date_invoice': datetime.today().strftime('%Y-%m-%d'),
            'invoice_line': invoice_line,
            'state': 'draft',
            'type': 'out_invoice',
        })
        return vals

    def _import_app(self, cr, uid, appointments, context=None):
        appointment_ids = []
        if not appointments.findall('appointment'):
            raise osv.except_osv(('Warning in file %s' % self.curr_file),('This file contains no appointment'))
        invoice_model = self.pool.get('account.invoice')
        for appointment in appointments.findall('appointment'):
            appointment_vals = self._get_invoice_vals(cr, uid, appointment, 'app', context=context)
            appointment_vals['type2'] = 'appointment'
            individual = appointment.find('individual_customer')
            appointment_vals['individual_cust'] = True if individual is not None and individual.text == 'IND' else False
            appointment_ids.append(invoice_model.create(cr, uid, appointment_vals, context=context))
        return appointment_ids

    def _import_vbl(self, cr, uid, vbillings, context=None):
        vbilling_ids = []
        if not vbillings.findall('vbilling'):
            raise osv.except_osv(('Warning in file %s' % self.curr_file),('This file contains no vessel billing'))
        product_model = self.pool.get('product.product')
        invoice_model = self.pool.get('account.invoice')
        for vbilling in vbillings.findall('vbilling'):
            vbilling_vals = self._get_invoice_vals(cr, uid, vbilling, 'vbl', context=context)
            vbilling_vals['type2'] = 'vessel'
            if vbilling.find('hatchcovers_moves') is not None and int(self._get_elmnt_text(vbilling, 'hatchcovers_moves')) > 0:
                product_ids = product_model.search(cr, uid, [('name', '=', 'Hatch cover move')], context=context)
                if not product_ids:
                    raise osv.except_osv(('Error in file %s' % self.curr_file), ('No product found for "Hatch cover move"'))
                product = product_model.browse(cr, uid, product_ids, context=context)[0]
                line_vals = {
                    'product_id': product.id,
                    'name' : product.name,
                    'quantity': int(self._get_elmnt_text(vbilling, 'hatchcovers_moves')),
                    'price_unit': product.list_price,
                }
                account = product.property_account_income or (product.categ_id and product.categ_id.property_account_income_categ) or False
                if account:
                    line_vals['account_id'] = account.id
                else:
                    raise osv.except_osv(('Error in file %s' % self.curr_file), ('Could not find an income account on product %s ') % product.name)
                vbilling_vals['invoice_line'].append((0,0,line_vals))
            if vbilling.find('gearbox_count') is not None and int(self._get_elmnt_text(vbilling, 'gearbox_count')) > 0:
                product_ids = product_model.search(cr, uid, [('name', '=', 'Gearbox count')], context=context)
                if not product_ids:
                    raise osv.except_osv(('Error in file %s' % self.curr_file), ('No product found for "Gearbox count"'))
                product = product_model.browse(cr, uid, product_ids, context=context)[0]
                line_vals = {
                    'product_id': product.id,
                    'name' : product.name,
                    'quantity': int(self._get_elmnt_text(vbilling, 'gearbox_count')),
                    'price_unit': product.list_price,
                }
                account = product.property_account_income or (product.categ_id and product.categ_id.property_account_income_categ) or False
                if account:
                    line_vals['account_id'] = account.id
                else:
                    raise osv.except_osv(('Error in file %s' % self.curr_file), ('Could not find an income account on product %s ') % product.name)
                vbilling_vals['invoice_line'].append((0,0,line_vals))
            vbilling_ids.append(invoice_model.create(cr, uid, vbilling_vals, context=context))
        return vbilling_ids

    def _import_data(self, cr, uid, ids, context=None):
        if not ids:
            return []

        config_obj = self.browse(cr, uid, ids, context=context)[0]
        ftp = FTP(host=config_obj.addr, user=config_obj.user, passwd=config_obj.psswd)
        outbound_path =  config_obj.outbound_path
        ftp.cwd(outbound_path)
        module_path = __file__.split('models')[0]
        invoice_ids = []
        archive_path = 'done'
        log_path = 'logs'
        errors = []
        for path in [archive_path, log_path]:
            if path not in ftp.nlst():
                ftp.mkd(path)
        cr.commit()
        for filename in ftp.nlst():
            self.curr_file = filename
            loc_file = os.path.join(module_path, 'tmp', filename)
            try:
                with open(loc_file, 'w+') as f:
                    ftp.retrlines('RETR ' + filename, f.write)
            except:
                continue
            if re.match('^VBL_\d{6}_\d{6}\.xml$', filename):
                try:
                    root = ET.parse(loc_file).getroot()
                    invoice_ids.extend(self._import_vbl(cr, uid, root, context=context))
                except Exception as e:
                    errors.append(e)
                    os.remove(loc_file); cr.rollback(); continue
            elif re.match('^APP_\d{6}_\d{6}\.xml$', filename):
                try:
                    root = ET.parse(loc_file).getroot()
                    invoice_ids.extend(self._import_app(cr, uid, root, context=context))
                except Exception as e:
                    errors.append(e)
                    os.remove(loc_file); cr.rollback(); continue
            else:
                errors.append(osv._except_osv((('File format Error'),('While processing %s. Unknown file name format' % self.curr_file))))
                os.remove(loc_file); cr.rollback(); continue
            os.remove(loc_file)
            toname = archive_path + '/' + filename
            toname_base = toname[:-4]
            n = 1
            while toname in ftp.nlst(archive_path):
                toname = toname_base + '-' + str(n) + '.xml'
                n += 1
            try:
                ftp.rename(filename, toname)
            except Exception as e:
                errors.append(e)
                cr.rollback(); continue
            cr.commit()
        if errors:
            log_file = datetime.now().strftime('%Y%m%d_%H%M%S')
            with open(log_file, 'w+') as f:
                for e in errors:
                    f.write(type(e).__name__ + ": " + " - ".join([mssg for mssg in e.args]))
            ftp.storlines('STOR ' + log_path + '/' + log_file, open(log_file))
            os.remove(log_file)
        return invoice_ids

    def button_import_data(self, cr, uid, ids, context=None):
        return self._import_data(cr, uid, ids, context=context)

    def cron_import_data(self, cr, uid, context=None):
        self._import_data(cr, uid, self.search(cr, uid, [('active','=',True)]), context=context)

    # Data Export

    def _dict_to_tree(self, vals, elmnt):
        for tag, val in vals.iteritems():
            subelmnt = ET.SubElement(elmnt, tag)
            if not val:
                pass
            elif isinstance(val, unicode):
                subelmnt.text = val
            elif isinstance(val, str):
                subelmnt.text = unicode(val)
            elif isinstance(val, int) or isinstance(val, long) and not isinstance(val, bool):
                subelmnt.text = unicode(str(val))
            elif isinstance(val,dict):
                self._dict_to_tree(val, subelmnt)
            elif isinstance(val,list):
                for list_elem in val:
                    self._dict_to_tree(list_elem, subelmnt)

    def _write_partners_tree(self, cr, uid, partner_ids, context=None):
        root = ET.Element('customers')
        partner_model = self.pool.get('res.partner')
        partners = partner_model.browse(cr, uid, partner_ids, context=context)
        for partner in partners:
            values = {
                'customer_id': partner.id,
                'customer_key': partner.ref,
                'name': partner.name,
                'street': (partner.street + ( (', ' + partner.street2) if partner.street2 else '') if partner.street else '') or False,
                'city': partner.city,
                'zip': partner.zip,
                'country': partner.country_id and partner.country_id.name,
                'email': partner.email,
                'website': partner.website,
                'phone': partner.phone or partner.mobile or False
            }
            self._dict_to_tree(values, ET.SubElement(root, 'customer'))
        return root

    def _write_app_tree(self, cr, uid, app_id, payment_id, context=None):
        root = ET.Element('appointments')
        invoice_model = self.pool.get('account.invoice')
        voucher_model = self.pool.get('account.voucher')
        invoice = invoice_model.browse(cr, uid, app_id, context=context)
        voucher = voucher_model.browse(cr, uid, payment_id, context=context)
        values = {
            'customer_id': invoice.partner_id.name,
            'individual_customer': 'IND' if invoice.individual_cust else 'STD',
            'appointment_reference': invoice.appoint_ref,
            'appointment_date': invoice.appoint_date,
            'payment_made': 'YES',
            'pay_through_date': invoice.date_due,
            'payment_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'cashier_receipt_number': voucher.cashier_rcpt_nr, # TODO
        }
        self._dict_to_tree(values, ET.SubElement(root, 'appointment'))
        return root

    def _write_xml_file(self, local_file, root):
        with io.open(local_file, 'w+', encoding='utf-8') as f:
            f.write(u'<?xml version="1.0" encoding="utf-8"?>')
            f.write(ET.tostring(root, encoding='utf-8', pretty_print=True).decode('utf-8'))

    def _upload_file(self, cr, uid, local_path, file_name, context=None):
        local_file = local_path + file_name
        try:
            ftp_config_ids = self.search(cr, uid, [('active','=',True)], context=context)
            ftp_config_id = ftp_config_ids and ftp_config_ids[0] or False
            config_obj = self.browse(cr, uid, ftp_config_id, context=context)
            ftp = FTP(host=config_obj.addr, user=config_obj.user, passwd=config_obj.psswd)
            inbound_path =  config_obj.inbound_path.rstrip('/') + "/"
            ftp.cwd(inbound_path)
            with open(local_file, 'r') as f:
                ftp.storlines('STOR ' + file_name, f)
        except:
            os.remove(local_file)
            raise

    def export_partners(self, cr, uid, partner_ids, context=None):
        if not partner_ids:
            return []
        ftp_config_ids = self.search(cr, uid, [('active','=',True)], context=context)
        if not ftp_config_ids:
            raise osv.except_osv(('Error'), ('Impossible to find an active FTP configuration to export this partner'))
        root = self._write_partners_tree(cr, uid, partner_ids, context=context)

        sequence = self.pool.get('ir.sequence').get_next_by_xml_id(cr, uid, 'lct_tos_integration', 'sequence_partner_export', context=context)

        local_path = __file__.split('models')[0] + "tmp/"
        file_name = 'CUS_' + datetime.today().strftime('%y%m%d') + '_' + sequence + '.xml'
        self._write_xml_file(local_path + file_name, root)
        self._upload_file(cr, uid, local_path, file_name, context=context)
        return partner_ids

    def export_app(self, cr, uid, app_id, payment_id, context=None):
        if not (app_id and payment_id):
            return []
        root = self._write_app_tree(cr, uid, app_id, payment_id, context=context)

        sequence = self.pool.get('ir.sequence').get_next_by_xml_id(cr, uid, 'lct_tos_integration', 'sequence_appointment_validate_export', context=context)
        local_path = __file__.split('models')[0] + "tmp/"
        file_name = 'APP_' + datetime.today().strftime('%y%m%d') + '_' + sequence + '.xml'
        self._write_xml_file(local_path + file_name, root)
        self._upload_file(cr, uid, local_path, file_name, context=context)
