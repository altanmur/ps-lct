# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2014 OpenERP (<openerp@openerp-HP-ProBook-430-G1>)
#    All Rights Reserved
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
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

from osv import fields, osv
from tools.translate import _
from xlwt import Workbook, easyxf
from xlrd import open_workbook, XL_CELL_BLANK
import xlutils.copy
import StringIO
import base64
from datetime import datetime, timedelta
from ..tools import xl_module as xlm
import zipfile
import os


class liasse_fiscale(osv.osv_memory):
    _name = "lct_finance.liasse.fiscale"

    _columns = {
        "fiscalyear_id": fields.many2one('account.fiscalyear', required=True, string="Fiscal Year"),
        "date_of_report": fields.date("Date of Report", required=True),
    }

    _defaults = {
        "fiscalyear_id": lambda self, cr, uid, context: self.__get_curr_fy(cr, uid, context=None),
        "date_of_report": fields.date.today(),
    }

    def _check_date(self, cr, uid, ids, context=None):
        for liasse_fiscale in self.browse(cr, uid, ids, context=context):
            fiscalyear = liasse_fiscale.fiscalyear_id
            date_start = datetime.strptime(fiscalyear.date_start, '%Y-%m-%d')
            date_stop = datetime.strptime(fiscalyear.date_stop, '%Y-%m-%d')
            date_report = datetime.strptime(liasse_fiscale.date_of_report, '%Y-%m-%d')
            if date_report > date_stop or date_report < date_start:
                return False
        return True

    _constraints = [
        (_check_date, 'The date of report must be in fiscal year.', ['date_of_report', 'fiscalyear_id']),
    ]


    def __get_curr_fy(self, cr, uid, context=None):
        domain = [('date_start', '<=', fields.date.today()), ('date_stop', '>=', fields.date.today())]
        fy_ids = self.pool.get('account.fiscalyear').search(cr, uid, domain, context=context)
        return fy_ids and fy_ids[0] or False

    def _write_accounts_info(self, cr, uid, sheet, code_tree, mapping, context=None):
        account_model = self.pool.get('account.account')
        accounts_tree = {}
        for row, val in code_tree.iteritems():
            if val['children']:
                for col in mapping.keys():
                    xlm.write_sum_from_code_tree(sheet, val['children'], row, col)
                self._write_accounts_info(cr, uid, sheet, val['children'], mapping, context=context)
            else:
                account_id = account_model.find_by_code(cr, uid, val['code'], context=context)
                if not account_id:
                    continue
                account = account_model.browse(cr, uid, account_id, context=context)
                debit = account.debit
                credit = account.credit
                prev_debit = account.prev_debit
                prev_credit = account.prev_credit
                prev_balance = prev_debit - prev_credit
                balance = prev_balance + debit - credit

                account_vals = {
                    'move_debit': debit,
                    'move_credit': credit,
                    'prev_debit': prev_debit,
                    'prev_credit': prev_credit,
                    'balance': balance,
                    'prev_balance': prev_balance,
                }
                for col, attr in mapping.iteritems():
                    value = account_vals[attr]
                    xlm.set_out_cell(sheet, (row, col), value)

    def _write_calc(self, cr, uid, template, report, context=None):
        account_model = self.pool.get('account.account')
        fy_model = self.pool.get('account.fiscalyear')

        fy_code = fy_model.browse(cr, uid, context.get('fiscalyear'), context=context).code
        prev_fy_code = fy_model.browse(cr, uid, context.get('prev_fiscalyear'), context=context).code


        # Info complémentaires

        template_sheet = template.sheet_by_index(0)
        work_sheet = report.get_sheet(0)
        xlm.set_out_cells(work_sheet, {
            xlm.get_coord("D3"): fy_code,
            xlm.get_coord("D10"): fy_code,
            xlm.get_coord("C4"): prev_fy_code,
            xlm.get_coord("C5"): prev_fy_code,
            xlm.get_coord("E10"): prev_fy_code,
        })


        # Classe 1

        template_sheet = template.sheet_by_index(1)
        work_sheet = report.get_sheet(1)

        xlm.set_out_cells(work_sheet, {
            xlm.get_coord("D7"): prev_fy_code,
            xlm.get_coord("F7"): fy_code,
        })

        code_tree = xlm.build_code_tree(template_sheet, "B", "10", "101")
        code_tree = {
            xlm.get_row("102"): {
                'code': '1',
                'children': code_tree,
            }
        }
        mapping = {
            xlm.get_col("D"): 'prev_debit',
            xlm.get_col("E"): 'prev_credit',
            xlm.get_col("F"): 'move_debit',
            xlm.get_col("G"): 'move_credit',
        }
        self._write_accounts_info(cr, uid, work_sheet, code_tree, mapping, context=context)


        # Classe 2

        template_sheet = template.sheet_by_index(2)
        work_sheet = report.get_sheet(2)

        xlm.set_out_cells(work_sheet, {
            xlm.get_coord("D6"): prev_fy_code,
            xlm.get_coord("E6"): fy_code,
        })

        code_tree = xlm.build_code_tree(template_sheet, "B", "10", "155",
                                        skip=["43", "44", "84", "85", "114", "122", "123", "124", "135", "136", "155"])
        code_tree = {
            xlm.get_row("156"): {
                'code': '2',
                'children': code_tree,
            }
        }
        mapping = {
            xlm.get_col("D"): 'prev_balance',
            xlm.get_col("E"): 'move_debit',
            xlm.get_col("K"): 'move_credit',
        }
        self._write_accounts_info(cr, uid, work_sheet, code_tree, mapping, context=context)


        # Classe 3

        template_sheet = template.sheet_by_index(3)
        work_sheet = report.get_sheet(3)

        xlm.set_out_cells(work_sheet, {
            xlm.get_coord("D5"): prev_fy_code,
            xlm.get_coord("E5"): fy_code,
        })

        code_tree = xlm.build_code_tree(template_sheet, "B", "8", "55",
                                        skip=["41", "42", "52", "53", "54"])
        code_tree = {
            xlm.get_row("56"): {
                'code': '3',
                'children': code_tree,
            }
        }
        mapping = {
            xlm.get_col("D"): 'prev_balance',
            xlm.get_col("E"): 'move_debit',
            xlm.get_col("F"): 'move_credit',
        }
        self._write_accounts_info(cr, uid, work_sheet, code_tree, mapping, context=context)


        # Classe 4

        template_sheet = template.sheet_by_index(4)
        work_sheet = report.get_sheet(4)

        xlm.set_out_cells(work_sheet, {
            xlm.get_coord("D5"): prev_fy_code,
            xlm.get_coord("F5"): fy_code,
        })

        code_tree = xlm.build_code_tree(template_sheet, "B", "8", "97",
                                        skip=["52"])
        code_tree = {
            xlm.get_row("98"): {
                'code': '4',
                'children': code_tree,
            }
        }
        mapping = {
            xlm.get_col("D"): 'prev_debit',
            xlm.get_col("E"): 'prev_credit',
            xlm.get_col("F"): 'move_debit',
            xlm.get_col("G"): 'move_credit',
        }
        self._write_accounts_info(cr, uid, work_sheet, code_tree, mapping, context=context)


        # Classe 5

        template_sheet = template.sheet_by_index(5)
        work_sheet = report.get_sheet(5)

        xlm.set_out_cells(work_sheet, {
            xlm.get_coord("D5"): prev_fy_code,
            xlm.get_coord("F5"): fy_code,
        })

        code_tree = xlm.build_code_tree(template_sheet, "B", "8", "67",
                                        skip=[])
        code_tree = {
            xlm.get_row("68"): {
                'code': '5',
                'children': code_tree,
            }
        }
        mapping = {
            xlm.get_col("D"): 'prev_debit',
            xlm.get_col("E"): 'prev_credit',
            xlm.get_col("F"): 'move_debit',
            xlm.get_col("G"): 'move_credit',
        }
        self._write_accounts_info(cr, uid, work_sheet, code_tree, mapping, context=context)


        # Classe 6

        template_sheet = template.sheet_by_index(6)
        work_sheet = report.get_sheet(6)

        xlm.set_out_cells(work_sheet, {
            xlm.get_coord("D5"): prev_fy_code,
            xlm.get_coord("E5"): fy_code,
        })

        code_tree = xlm.build_code_tree(template_sheet, "B", "7", "266",
                                        skip=[])
        code_tree = {
            xlm.get_row("268"): {
                'code': '6',
                'children': code_tree,
            }
        }
        mapping = {
            xlm.get_col("D"): 'prev_balance',
            xlm.get_col("E"): 'balance',
        }
        self._write_accounts_info(cr, uid, work_sheet, code_tree, mapping, context=context)


        # Classe 7

        template_sheet = template.sheet_by_index(7)
        work_sheet = report.get_sheet(7)

        xlm.set_out_cells(work_sheet, {
            xlm.get_coord("D5"): prev_fy_code,
            xlm.get_coord("E5"): fy_code,
        })

        code_tree = xlm.build_code_tree(template_sheet, "B", "7", "123",
                                        skip=[])
        code_tree = {
            xlm.get_row("125"): {
                'code': '7',
                'children': code_tree,
            }
        }
        mapping = {
            xlm.get_col("D"): 'prev_balance',
            xlm.get_col("E"): 'balance',
        }
        self._write_accounts_info(cr, uid, work_sheet, code_tree, mapping, context=context)


        # Classe 8

        template_sheet = template.sheet_by_index(8)
        work_sheet = report.get_sheet(8)

        xlm.set_out_cells(work_sheet, {
            xlm.get_coord("D5"): prev_fy_code,
            xlm.get_coord("E5"): fy_code,
        })

        code_tree = xlm.build_code_tree(template_sheet, "B", "7", "63",
                                        skip=[])
        code_tree = {
            xlm.get_row("65"): {
                'code': '8',
                'children': code_tree,
            }
        }
        mapping = {
            xlm.get_col("D"): 'prev_balance',
            xlm.get_col("E"): 'balance',
        }
        self._write_accounts_info(cr, uid, work_sheet, code_tree, mapping, context=context)

    def print_report(self, cr, uid, ids, name, context=None):
        if context is None:
            context = {}

        fy_model = self.pool.get('account.fiscalyear')
        fiscalyear = self.browse(cr, uid, ids, context=context)[0].fiscalyear_id
        context['fiscalyear'] = fiscalyear and fiscalyear.id
        date_start = fiscalyear.date_start
        fiscalyear_ids = fy_model.search(cr, uid, [('date_stop', '<=', date_start)], order='date_start', limit=1, context=context)
        context['prev_fiscalyear'] = fiscalyear_ids and fiscalyear_ids[0] or False
        context['date_from'] = '1000-01-01'
        context['date_to'] = self.browse(cr, uid, ids[0], context=context).date_of_report
        module_path = __file__.split('wizard')[0]
        xls_path = os.path.join(module_path, 'data', 'Donnees liasse fiscale.xls')
        template = open_workbook(xls_path, formatting_info=True)
        workbook = xlutils.copy.copy(template)
        self._write_calc(cr, uid, template, workbook, context=context)

        data_xls_sIO = StringIO.StringIO()
        zip_sIO = StringIO.StringIO()
        workbook.save(data_xls_sIO)
        zip_file = zipfile.ZipFile(zip_sIO, 'w')
        data_xls_sIO.seek(0)
        zip_file.writestr('Liasse fiscale/Donnees liasse fiscale.xls', data_xls_sIO.getvalue())
        xls_path = os.path.join(module_path, 'data', 'Calculs liasse fiscale.xls')
        zip_file.write(xls_path, arcname='Liasse fiscale/Calculs liasse fiscale.xls')
        xls_path = os.path.join(module_path, 'data', 'Liasse fiscale.xls')
        zip_file.write(xls_path, arcname='Liasse fiscale/Liasse fiscale.xls')
        zip_file.close()
        zip_sIO.seek(0)
        zip_b64 = base64.b64encode(zip_sIO.getvalue())

        dlwizard = self.pool.get('lct_finance.file.download').create(cr, uid, {'file': zip_b64, 'file_name': 'Liasse fiscale.zip'}, context=dict(context, active_ids=ids))
        return {
            'view_mode': 'form',
            'view_id': False,
            'view_type': 'form',
            'res_model': 'lct_finance.file.download',
            'res_id': dlwizard,
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'new',
            'domain': '[]',
            'context': dict(context, active_ids=ids)
        }
