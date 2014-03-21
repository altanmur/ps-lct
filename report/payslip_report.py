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

from osv.orm import TransientModel
from osv import fields
from tools.translate import _
from xlwt import Workbook, easyxf
import base64
import StringIO
from openerp.modules import get_module_path
from zipfile import ZipFile
import os

base_bath = get_module_path('lct_hr')

# mapping = ['basic', 'seniority', 'benefits', 'overtime', 'transportation allowance',
#             'representation allowance', 'individual allowance', 'performance allowance',
#             'other allowances', 'gross', 'cnss', 'irpp', 'tcs', 'cnss 17.5%', 'ts 3%', 'advance on salary',
#             'loan repayments', 'other deductions', 'to pay']

class payslip_report(TransientModel):
    _name = 'payslip_report'
    _description = "Payslip report"

    _columns = {
        'payslip_ids': fields.many2many('hr.payslip', 'payslip_report_payslip_rel', 'report_id', 'payslip_id', 'Payslips'),
        'out_file': fields.binary('Report',readonly=True),
        'datas_fname': fields.char('File name', 64),
        'state': fields.selection([('draft', 'Draft'),('done', 'Done')], string="Status"),
    }

    _defaults = {
        'datas_fname': 'Bulletin de paie.xls',
        'state': 'draft',
    }

    # Returns only the lines that actually appear on the payslip
    def get_payslip_lines(self, cr, uid, obj, context=None):
        payslip_line = self.pool.get('hr.payslip.line')
        res = []
        ids = []
        for id in range(len(obj)):
            if obj[id].appears_on_payslip == True:
                ids.append(obj[id].id)
        if ids:
            res = payslip_line.browse(cr, uid, ids, context=context)
        return res

    def export_xls(self, cr, uid, ids, context=None):
        for report in self.browse(cr, uid, ids, context=context):
            payslip_ids = context.get('active_ids')
            payslips = self.pool.get('hr.payslip').browse(cr, uid, payslip_ids, context=context)
            filenames = []
            for payslip in payslips:
                lines = self.get_payslip_lines(cr, uid, payslip.line_ids, context=context)

                xls = Workbook()
                # font_bold = Font()
                # font_bold.bold = True
                # style_bold = XFStyle()
                # style_bold.font = font_bold
                style_default = easyxf('font: height 200')
                style_bold = easyxf('font: bold on, height 200')
                style_bold_center = easyxf('font: bold on, height 200; align: horiz center')
                style_bold_center_wrap = easyxf('font: bold on, height 200; align: wrap on, horiz center')
                style_bold_right = easyxf('font: bold on, height 200; align: horiz right')
                style_center = easyxf('align: horiz center; font: height 200')
                style_right = easyxf('align: horiz right; font: height 200')
                sheet1 = xls.add_sheet('Pay book')
                sheet1.paper_size_code = 77
                sheet1.col(0).width = 256*10
                sheet1.col(8).width = 256*15
                sheet1.col(2).width = sheet1.col(6).width = sheet1.col(9).width = 256*16
                # Fixed content:
                # TODO: auto-translate the hardcoded French strings and company info
                # Also, we could store this in a dict: {fieldname: (row, col), ...} and then
                # retrieve field value and write in row, col in a for-loop over the dict
                ##################
                # TOP LEFT BLOCK #
                ##################
                # Strats at r0, c0
                sheet1.insert_bitmap(base_bath + '/report/logo.bmp', 1, 0)
                for row in range(100):
                    sheet1.row(row).set_style(style_default)
                    sheet1.row(row).height = 240
                sheet1.write(0, 1, u'BULLETIN DE PAIE', style_bold_center)
                sheet1.write(1, 4, u'Lomé Container Terminal S.A.', style_bold_right)
                sheet1.write(4, 0, u'Zone Portuaire Rte A3 Akodessewa', style_bold)
                sheet1.write(5, 0, u'Immeuble MSC TOGO', style_bold)
                sheet1.write(6, 0, u'09 BP 9103 Lomé', style_bold)
                sheet1.write(8, 2, u'N° Employeur:', style_right)
                sheet1.write(8, 4, u'17295', style_bold_right)
                sheet1.write(9, 2, u'NIF:', style_right)
                sheet1.write(9, 4, u'090164 W', style_bold_right)
                ####################
                # TOP CENTER BLOCK #
                ####################
                # Starts at r0, c6
                sheet1.write(0, 6, u'Periode du')
                sheet1.write_merge(0, 0, 7, 8, '%s - %s' % (payslip.date_from, payslip.date_to))
                sheet1.write(1, 6, u"Date d'embauche:")
                sheet1.write(1, 7, payslip.employee_id.start_date)
                sheet1.write(2, 6, u'Matricule:')
                sheet1.write(2, 7, payslip.employee_id.reg_nbr)
                sheet1.write(3, 6, u'Niveau:')
                sheet1.write(3, 7, self.pool.get('hr.contract').get_cat(payslip.contract_id.hr_class))
                sheet1.write(4, 6, u'Indice sal.')
                sheet1.write(4, 7, payslip.contract_id.hr_class)
                sheet1.write(5, 6, u'Coefficient:')
                sheet1.write(5, 7, payslip.contract_id.echelon)
                sheet1.write_merge(6, 7, 6, 7, u'Employ Occupé', style_center)
                sheet1.write_merge(8, 9, 6, 7, payslip.employee_id.job_id.name, style_center)
                ###################
                # TOP RIGHT BLOCK #
                ###################
                # Starts at r0, c8
                sheet1.write(0, 9, u'Date de paiement:')
                sheet1.write(0, 10, '???')
                sheet1.write_merge(1, 1, 8, 10, u'NOM & PRENOMS', style_center)
                sheet1.write_merge(2, 2, 8, 10, payslip.employee_id.name, style_center)
                sheet1.write_merge(3, 3, 8, 10, u'ADRESSE', style_bold_center)
                sheet1.write_merge(4, 4, 8, 10, u'S/C LCT 09 BP 9103 LOME', style_bold_center)
                sheet1.write(5, 8, u'N° CNSS')
                sheet1.write(6, 8, payslip.employee_id.cnss_nbr)
                sheet1.write(5, 9, u'ANCIENNETE')
                sheet1.write(6, 9, '%dA, %dM, %dJ' % self.pool.get('hr.employee').get_seniority_ymd(cr, uid, payslip.employee_id.id, context=context))
                sheet1.write(5, 10, u'HORAIRE')
                sheet1.write(6, 10, payslip.contract_id.working_hours.name)
                ###############
                # LINE HEADER #
                ###############
                # Starts at 10, 0
                sheet1.write_merge(10, 10, 0, 2, u'Convention collective:', style_right)
                sheet1.write_merge(10, 10, 3, 7, u'Convention collective Interprofessionelle du Togo')
                sheet1.write(10, 8, u'Département:')
                sheet1.write_merge(10, 10, 9, 10, payslip.employee_id.department_id.name)
                # 2nd header
                sheet1.write_merge(11,12, 0, 0, u'N°', style_bold_center)
                sheet1.write_merge(11, 12, 1, 2, u'Designation', style_bold_center)
                sheet1.write_merge(11,12, 3, 3, u'NOMBRE DE JOURS', style_bold_center_wrap)
                sheet1.write_merge(11,12, 4, 4, u'BASE', style_bold_center)
                sheet1.write_merge(11, 11, 5, 7, u'PART SALARIALE', style_bold_center)
                sheet1.write(12, 5, u'TAUX', style_bold_center)
                sheet1.write(12, 6, u'GAIN', style_bold_center)
                sheet1.write(12, 7, u'RETENUE', style_bold_center)
                sheet1.write_merge(11, 11, 8, 10, u'PART PATRONALE', style_bold_center)
                sheet1.write(12, 8, u'TAUX', style_bold_center)
                sheet1.write(12, 9, u'GAIN', style_bold_center)
                sheet1.write(12, 10, u'RETENUE', style_bold_center)
                #########
                # LINES #
                #########
                # Starts at 13, 0
                for line in lines:
                    row = 13 + lines.index(line)
                    sheet1.write(row, 0, _(line.code), style_center)
                    sheet1.write_merge(row, row, 1, 2, _(line.name))
                    sheet1.write(row, 3, len(payslip.worked_days_line_ids))
                    sheet1.write(row, 4, line.amount)
                    if line.salary_rule_id.category_id.name != 'Employer Contributions':
                        sheet1.write(row, 5, '%.2f%%' % (line.amount_percentage or 100,), style_right)
                        sheet1.write(row, 6, line.total)
                    else:
                        sheet1.write(row, 8, '%.2f%%' % (line.amount_percentage or 100,), style_right)
                        sheet1.write(row, 9, line.total)




                # add header
                # sheet1.write(1, 0, 'From %s' % dt_start, style_bold)
                # sheet1.write(1, 1, 'To %s' % dt_end.split()[0], style_bold)
                # for title in header:
                #     sheet1.write(2, header.index(title), title)
                # row = 3
                # for slip_id in ordered_ids:
                #     raw_data = row_data[slip_id]
                #     # TODO: these need to become rules on the payslip and just taken from there.
                #     sheet1.write(row, 0, raw_data['reg_nbr'])
                #     sheet1.write(row, 1, raw_data['name_related'])
                #     for field in mapping:
                #         if field in raw_data:
                #             sheet1.write(row, mapping.index(field) + 2, raw_data[field])
                #     row += 1
                fn_report = "%s - %s - %s (%s).xls" % (report.datas_fname[:-4], payslip.employee_id.reg_nbr, payslip.employee_id.name, payslip.id)
                if len(payslip_ids) > 1:
                    xls.save('/tmp/' + fn_report)
                    filenames.append('/tmp/' + fn_report)
                else:
                    output = StringIO.StringIO()
                    xls.save(output)
                    encode_text = base64.encodestring(output.getvalue())
            if filenames:
                # compress all xls files in a zip file, and update datas_fname and encode_text
                fn_report = '/tmp/%s.zip' % (report.datas_fname[:-4])
                with ZipFile(fn_report, 'w', allowZip64=True) as output:
                    for filename in filenames:
                        output.write(filename)
                with open(fn_report, 'r') as archive:
                    encode_text = base64.encodestring(archive.read())
            self.write(cr,uid,ids,{'state': 'done', 'out_file': encode_text, 'datas_fname': fn_report},context=context)
            # Don't forget to clean up /tmp!
            if filenames:
                for filename in filenames:
                    try:
                        os.unlink(filename)
                    except:
                        pass  # We don't want to suddenly stop when something fails; the rest still needs to be deleted
                os.unlink(fn_report)
            return {'type': 'ir.actions.client', 'tag': 'reload_dialog',}
