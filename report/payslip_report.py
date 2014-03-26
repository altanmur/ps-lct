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
from datetime import date
from dateutil.relativedelta import relativedelta


base_bath = get_module_path('lct_hr')


class payslip_report(TransientModel):
    _name = 'payslip_report'
    _description = "Payslip report"

    _columns = {
        'export_selected_only': fields.boolean('Export selected payslips only'),
        'payslip_ids': fields.many2many('hr.payslip', 'payslip_report_payslip_rel', 'report_id', 'payslip_id', 'Payslips'),
        'dt_start': fields.date('Start date'),
        'dt_end': fields.date('End date'),
        'out_file': fields.binary('Report',readonly=True),
        'datas_fname': fields.char('File name', 64),
        'state': fields.selection([('draft', 'Draft'),('done', 'Done')], string="Status"),
    }

    _defaults = {
        'export_selected_only': True,
        'dt_start': lambda self, *args, **kwargs: self._get_dt_start(*args, **kwargs),
        'dt_end': lambda self, *args, **kwargs: self._get_dt_end(*args, **kwargs),
        'datas_fname': 'Bulletin de paie.xls',
        'state': 'draft',
    }

    def _get_dt_start(self, cr, uid, context=None):
        today = date.today().replace(day=1)
        return today.strftime("%Y-%m-%d")

    def _get_dt_end(self, cr, uid, context=None):
        end_of_month = (date.today() + relativedelta(months=1)).replace(day=1)
        return end_of_month.strftime("%Y-%m-%d")

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
            payslip_ids = []
            if report.export_selected_only:
                payslip_ids = context.get('active_ids')
            else:
                payslip_ids = self.pool.get('hr.payslip').search(cr, uid, [('date_from', '>=', report.dt_start), ('date_to', '<=', report.dt_end)], context=context)
            payslips = self.pool.get('hr.payslip').browse(cr, uid, payslip_ids, context=context)
            filenames = []
            for payslip in payslips:
                lines = self.get_payslip_lines(cr, uid, payslip.line_ids, context=context)

                xls = Workbook()
                style_default = easyxf('font: height 200')
                style_bold_boxed = easyxf('font: bold on, height 200; align: wrap on; border: top thin, bottom thin, left thin, right thin')
                style_bold_center_boxed = easyxf('font: bold on, height 200; align: horiz center, wrap on; border: top thin, bottom thin, left thin, right thin')
                style_bold_right_boxed = easyxf('font: bold on, height 200; align: horiz right, wrap on; border: top thin, bottom thin, left thin, right thin')
                style_leftbox = easyxf('font: height 200; border: top thin, bottom thin, left thin')
                style_rightbox = easyxf('font: height 200; border: top thin, bottom thin, right thin')
                style_leftfence = easyxf('font: height 200; border: left thin')
                style_rightfence = easyxf('font: height 200; border: right thin')
                style_fenced = easyxf('font: height 200; border: left thin, right thin')
                style_bold_right_rightfence = easyxf('font: bold on, height 200; align: horiz right; border: right thin')
                style_bold_fenced = easyxf('font: bold on, height 200; border: left thin, right thin')
                style_bold_center_fenced = easyxf('font: bold on, height 200; align: horiz center; border: left thin, right thin')
                style_center_fenced = easyxf('font: height 200; align: horiz center; border: left thin, right thin')
                style_center_boxed = easyxf('font: height 200; align: horiz center; border: left thin, right thin, top thin, bottom thin')
                style_right_fenced = easyxf('align: horiz right; font: height 200; border: left thin, right thin')
                style_right_leftfence = easyxf('align: horiz right; font: height 200; border: left thin')
                style_right_leftbox = easyxf('align: horiz right; font: height 200; border: left thin, top thin, bottom thin')
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
                sheet1.insert_bitmap(base_bath + '/report/logo.bmp', 1, 1)
                for row in range(100):
                    sheet1.row(row).set_style(style_default)
                    sheet1.row(row).height = 240
                sheet1.write_merge(0, 0, 0, 5, u'BULLETIN DE PAIE', style_bold_center_boxed)
                sheet1.write(1, 5, u'Lomé Container Terminal S.A.', style_bold_right_rightfence)
                sheet1.write(1, 0, '', style_leftfence)
                sheet1.write_merge(2, 3, 0, 5, '', style_fenced)
                sheet1.write_merge(4, 4, 0, 5, u'Zone Portuaire Rte A3 Akodessewa', style_bold_fenced)
                sheet1.write_merge(5, 5, 0, 5, u'Immeuble MSC TOGO', style_bold_fenced)
                sheet1.write_merge(6, 6, 0, 5, u'09 BP 9103 Lomé', style_bold_fenced)
                sheet1.write_merge(7, 7, 0, 5, '', style_fenced)
                sheet1.write_merge(8, 8, 0, 2, u'N° Employeur:', style_right_leftfence)
                sheet1.write(8, 5, u'17295', style_bold_right_rightfence)
                sheet1.write_merge(9, 9, 0, 2, u'NIF:', style_right_leftfence)
                sheet1.write(9, 5, u'090164 W', style_bold_right_rightfence)
                ####################
                # TOP CENTER BLOCK #
                ####################
                # Starts at r0, c6
                sheet1.write(0, 6, u'Periode du', style_leftbox)
                sheet1.write_merge(0, 0, 7, 8, '%s - %s' % (payslip.date_from, payslip.date_to), style_rightbox)
                sheet1.write(1, 6, u"Date d'embauche:")
                sheet1.write(1, 7, payslip.employee_id.start_date, style_rightfence)
                sheet1.write(2, 6, u'Matricule:')
                sheet1.write(2, 7, payslip.employee_id.reg_nbr, style_rightfence)
                sheet1.write(3, 6, u'Niveau:')
                sheet1.write(3, 7, self.pool.get('hr.contract').get_cat(payslip.contract_id.hr_class), style_rightfence)
                sheet1.write(4, 6, u'Indice sal.')
                sheet1.write(4, 7, payslip.contract_id.hr_class, style_rightfence)
                sheet1.write(5, 6, u'Coefficient:')
                sheet1.write(5, 7, payslip.contract_id.echelon, style_rightfence)
                sheet1.write_merge(6, 7, 6, 7, u'Emploi Occupé', style_center_boxed)
                sheet1.write_merge(8, 9, 6, 7, payslip.employee_id.job_id.name, style_center_boxed)
                ###################
                # TOP RIGHT BLOCK #
                ###################
                # Starts at r0, c8
                sheet1.write(0, 9, u'Date de paiement:', style_leftbox)
                sheet1.write(0, 10, '???', style_rightbox)
                sheet1.write_merge(1, 1, 8, 10, u'NOM & PRENOMS', style_center_fenced)
                sheet1.write_merge(2, 2, 8, 10, payslip.employee_id.name, style_center_fenced)
                sheet1.write_merge(3, 3, 8, 10, u'ADRESSE', style_bold_center_fenced)
                sheet1.write_merge(4, 4, 8, 10, u'S/C LCT 09 BP 9103 LOME', style_bold_center_fenced)
                sheet1.write(5, 8, u'N° CNSS', style_center_boxed)
                sheet1.write(6, 8, payslip.employee_id.cnss_nbr, style_center_boxed)
                sheet1.write(5, 9, u'ANCIENNETE', style_center_boxed)
                sheet1.write(6, 9, '%dA, %dM, %dJ' % self.pool.get('hr.employee').get_seniority_ymd(cr, uid, payslip.employee_id.id, context=context), style_center_boxed)
                sheet1.write(5, 10, u'HORAIRE', style_center_boxed)
                sheet1.write(6, 10, payslip.contract_id.working_hours.name, style_center_boxed)
                sheet1.write_merge(7, 9, 8, 10, '', style_center_boxed)
                ###############
                # LINE HEADER #
                ###############
                # Starts at 10, 0
                sheet1.write_merge(10, 10, 0, 2, u'Convention collective:', style_right_leftbox)
                sheet1.write_merge(10, 10, 3, 7, u'Convention collective Interprofessionelle du Togo', style_rightbox)
                sheet1.write(10, 8, u'Département:', style_leftbox)
                sheet1.write_merge(10, 10, 9, 10, payslip.employee_id.department_id.name, style_rightbox)
                # 2nd header
                sheet1.write_merge(11,12, 0, 0, u'N°', style_bold_center_boxed)
                sheet1.write_merge(11, 12, 1, 2, u'Designation', style_bold_center_boxed)
                sheet1.write_merge(11,12, 3, 3, u'NOMBRE DE JOURS', style_bold_center_boxed)
                sheet1.write_merge(11,12, 4, 4, u'BASE', style_bold_center_boxed)
                sheet1.write_merge(11, 11, 5, 7, u'PART SALARIALE', style_bold_center_boxed)
                sheet1.write(12, 5, u'TAUX', style_bold_center_boxed)
                sheet1.write(12, 6, u'GAIN', style_bold_center_boxed)
                sheet1.write(12, 7, u'RETENUE', style_bold_center_boxed)
                sheet1.write_merge(11, 11, 8, 10, u'PART PATRONALE', style_bold_center_boxed)
                sheet1.write(12, 8, u'TAUX', style_bold_center_boxed)
                sheet1.write(12, 9, u'GAIN', style_bold_center_boxed)
                sheet1.write(12, 10, u'RETENUE', style_bold_center_boxed)
                #########
                # LINES #
                #########
                # Starts at 13, 0
                for row_offset, line in enumerate(lines):
                    row = 13 + row_offset
                    if row_offset == len(lines) - 1:
                        continue
                    sheet1.write(row, 0, _(line.code), style_center_fenced)
                    sheet1.write_merge(row, row, 1, 2, _(line.name), style_fenced)
                    sheet1.write(row, 3, len(payslip.worked_days_line_ids), style_fenced)
                    sheet1.write(row, 4, line.amount, style_fenced)
                    if line.salary_rule_id.category_id.name != 'Employer Contributions':
                        sheet1.write(row, 5, '%.2f%%' % (line.amount_percentage or 100,), style_right_fenced)
                        sheet1.write(row, 6, line.total, style_fenced)
                        sheet1.write(row, 7, '', style_fenced)
                        sheet1.write(row, 8, '', style_fenced)
                        sheet1.write(row, 9, '', style_fenced)
                        sheet1.write(row, 10, '', style_fenced)
                    else:
                        sheet1.write(row, 5, '', style_fenced)
                        sheet1.write(row, 6, '', style_fenced)
                        sheet1.write(row, 7, '', style_fenced)
                        sheet1.write(row, 8, '%.2f%%' % (line.amount_percentage or 100,), style_right_fenced)
                        sheet1.write(row, 9, line.total, style_fenced)
                        sheet1.write(row, 10, '', style_fenced)
                # Last line: To Pay. Special format for this one.
                last_line = lines[-1]
                row = 13 + len(lines) - 1
                sheet1.write(row, 0, _(line.code), style_bold_center_boxed)
                sheet1.write_merge(row, row, 1, 2, _(line.name), style_bold_boxed)
                sheet1.write(row, 3, len(payslip.worked_days_line_ids), style_bold_boxed)
                sheet1.write(row, 4, line.amount, style_bold_boxed)
                sheet1.write(row, 5, '%.2f%%' % (last_line.amount_percentage or 100,), style_bold_right_boxed)
                sheet1.write(row, 6, last_line.total, style_bold_center_boxed)
                sheet1.write(row, 7, '', style_center_boxed)
                sheet1.write(row, 8, '', style_center_boxed)
                sheet1.write(row, 9, '', style_center_boxed)
                sheet1.write(row, 10, '', style_center_boxed)
                ##############
                # BOTTOM BOX #
                ##############
                # sheet1.write_merge(start_row, start_row, 0, 10, '', style_border_top)
                # # No way; this is just too much of a hassle to compute. Leaving the partial work in
                # # as comment, but not implementing actually looking up values for period and entire year,
                # # it will go slow as hell when you do this for 4k employees!
                # sheet1.write_merge(start_row, start_row, 0, 2, u'Montants', style_center_boxed)
                # sheet1.write(start_row, 3, u'de la période', style_center_boxed)
                # sheet1.write(start_row, 4, u"de l'année", style_center_boxed)
                # sheet1.write_merge(start_row, start_row, 5, 6, u'Net à payer:', style_center_boxed)
                # sheet1.write_merge(start_row, start_row, 7, 7, u'XXX', style_center_boxed)
                # sheet1.write_merge(start_row, start_row, 8, 10, u'CONGES', style_bold_center_boxed)


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
