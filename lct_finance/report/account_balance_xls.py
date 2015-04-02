# -*- encoding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Management Solution
#    Copyright (C) 2004-TODAY Odoo S.A. <http://www.openerp.com>
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


import xlwt
from datetime import datetime
from openerp.osv import orm
from openerp.addons.report_xls.report_xls import report_xls
from openerp.addons.report_xls.utils import rowcol_to_cell, _render
from .account_balance import account_balance_report
from openerp.tools.translate import _
import logging
_logger = logging.getLogger(__name__)


class account_balance_xls_parser(account_balance_report):

    def __init__(self, cr, uid, name, context):
        super(account_balance_xls_parser, self).__init__(cr, uid, name, context=context)
        self.context = context
        wanted_list = self._report_xls_fields(cr, uid, context)
        template_changes = self._report_xls_template(cr, uid, context)
        space_extra = self._report_xls_render_space_extra(cr, uid, context)
        self.localcontext.update({
            'datetime': datetime,
            'wanted_list': wanted_list,
            'template_changes': template_changes,
            'space_extra': space_extra,
        })

    # Most of these do nothing, but the report kind of requires them.

    # override list in inherited module to add/drop columns or change order
    def _report_xls_fields(self, cr, uid, context=None):
        res = [
            'code',
            'name',
            'prev_debit',
            'prev_credit',
            'debit',
            'credit',
            'balance',
        ]
        return res

    # allow inherited modules to extend the query
    def _report_xls_query_extra(self, cr, uid, context=None):
        select_extra = ""
        join_extra = ""
        where_extra = ""
        return (select_extra, join_extra, where_extra)

    # allow inherited modules to add document references
    def _report_xls_document_extra(self, cr, uid, context=None):
        return "''"

    # allow inherited modules to extend the render namespace
    def _report_xls_render_space_extra(self, cr, uid, context=None):
        return None

    # Change/Add Template entries
    def _report_xls_template(self, cr, uid, context=None):
        return {}



class account_balance_xls(report_xls):

    def __init__(self, name, table, rml=False, parser=False, header=True, store=False):
        super(account_balance_xls, self).__init__(name, table, rml, parser, header, store)

        # Cell Styles
        _xs = self.xls_styles
        # header
        rh_cell_format = _xs['bold'] + _xs['fill'] + _xs['borders_all']
        self.rh_cell_style = xlwt.easyxf(rh_cell_format)
        self.rh_cell_style_center = xlwt.easyxf(rh_cell_format + _xs['center'])
        self.rh_cell_style_right = xlwt.easyxf(rh_cell_format + _xs['right'])
        # lines
        acc_cell_format = _xs['borders_all']
        self.acc_cell_style = xlwt.easyxf(acc_cell_format)
        self.acc_cell_style_center = xlwt.easyxf(acc_cell_format + _xs['center'])
        self.acc_cell_style_date = xlwt.easyxf(acc_cell_format + _xs['left'], num_format_str=report_xls.date_format)
        self.acc_cell_style_decimal = xlwt.easyxf(acc_cell_format + _xs['right'], num_format_str=report_xls.decimal_format)
        # totals
        rt_cell_format = _xs['bold'] + _xs['fill'] + _xs['borders_all']
        self.rt_cell_style = xlwt.easyxf(rt_cell_format)
        self.rt_cell_style_right = xlwt.easyxf(rt_cell_format + _xs['right'])
        self.rt_cell_style_decimal = xlwt.easyxf(rt_cell_format + _xs['right'], num_format_str=report_xls.decimal_format)

        # XLS Template
        self.col_specs_lines_template = {
            'code': {
                'header': [1, 20, 'text',None],
                'lines': [1, 0, 'text', _render("l['code']")],
                'totals': [1, 0, 'text', None],
            },
            'name': {
                'header': [1, 20, 'text', None],
                'lines': [1, 0, 'text', _render("l['name']")],
                'totals': [1, 0, 'text', None],
            },
            'prev_debit': {
                'header': [1, 20, 'text', _render("_('Débit')"), None, self.rh_cell_style_center],
                'lines': [1, 0, 'number', _render("l['prev_debit']")],
                'totals': [1, 0, 'number', None],
            },
            'prev_credit': {
                'header': [1, 20, 'text', _render("_('Crédit')"), None, self.rh_cell_style_center],
                'lines': [1, 0, 'number', _render("l['prev_credit']")],
                'totals': [1, 0, 'number', None],
            },
            'debit': {
                'header': [1, 20, 'text', _render("_('Débit')"), None, self.rh_cell_style_center],
                'lines': [1, 0, 'number', _render("l['debit']")],
                'totals': [1, 0, 'number', None, _render("debit_formula")],
            },
            'credit': {
                'header': [1, 20, 'text', _render("_('Crédit')"), None, self.rh_cell_style_center],
                'lines': [1, 0, 'number', _render("l['credit']")],
                'totals': [1, 0, 'number',None,  _render("credit_formula")],
            },
            'balance': {
                'header': [1, 20, 'text', _render("_('Balance')"), None, self.rh_cell_style_center],
                'lines': [1, 0, 'number', _render("l['balance']")],
                'totals': [1, 0, 'number', None, _render("bal_formula")],
            },
        }

    def _account_title(self, o, ws, parser, row_pos, xlwt, _xs):
        cell_style = xlwt.easyxf(_xs['xls_title'])
        cell_style_center = xlwt.easyxf(_xs['xls_title'] + _xs['center'])
        company_name = parser.company.name
        row_specs = [
            [  # company name, start_date
                ('company_name', 5, 0, 'text', company_name),
                ('start_date_lbl', 1, 0, 'text', 'Période du'),
                ('start_date', 1, 0, 'text', parser.get('start_date')),
            ],
            [  # end_date
                ('empty_cell', 5, 0, 'text', ''),
                ('end_date_lbl', 1, 0, 'text', 'au'),
                ('end_date', 1, 0, 'text', parser.get('end_date')),
            ],
            [  # balance des comptes
                ('acc_bal', 7, 0, 'text', 'Balance des comptes', None, cell_style_center),
            ],
            [  # with movements
                ('with_mov', 7, 0, 'text','With movements', None, cell_style_center),
            ],
        ]
        for c_specs in row_specs:
            row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
            row_pos = self.xls_write_row(ws, row_pos, row_data, row_style=cell_style)
        return row_pos + 1

    def _meta_headers(self, o, ws, parser, row_pos, xlwt, _xs):
        row_specs = [
            [  # date de tirage
                ('date_report_lbl', 1, 0, 'text', 'Date de tirage'),
                ('date_report', 1, 0, 'text', parser.get('current_date')),
            ],
            [  # separator
                ('empty_line', 1, 0, 'text', None),
            ],
            [  # soldes d'ouverture etc...
                ('acct_no', 1, 0, 'text', 'Numéro de compte', None, self.rh_cell_style_center),
                ('acct_name', 1, 0, 'text', 'Intitulé des comptes', None, self.rh_cell_style_center),
                ('opening_bal', 2, 0, 'text', "Soldes d'ouverture", None, self.rh_cell_style_center),
                ('mov', 2, 0, 'text', "Mouvements", None, self.rh_cell_style_center),
                ('closing_bal', 1, 0, 'text', 'Soldes de fin de periode', None, self.rh_cell_style_center),
            ],
        ]
        for c_specs in row_specs:
            row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
            row_pos = self.xls_write_row(ws, row_pos, row_data)
        return row_pos

    def _account_lines(self, o, ws, parser, row_pos, xlwt, _xs):
        """
            o: account.account browse record
            ws: worksheet
            parser: parser
            row_pos: int
            xlwt: xlwt module
            _xs: xls styles
        """

        if parser.space_extra:
            locals().update(parser.space_extra)
        wanted_list = self.wanted_list
        debit_pos = self.debit_pos
        credit_pos = self.credit_pos

        # Column headers
        c_specs = map(lambda x: self.render(x, self.col_specs_lines_template, 'header', render_space={'_': _}), wanted_list)
        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
        row_pos = self.xls_write_row(ws, row_pos, row_data, row_style=self.rh_cell_style, set_column_size=True)
        ws.set_horz_split_pos(row_pos)

        # check # lines for totals formula position
        acc_start_pos = row_pos
        acc_cnt = len(parser.lines)
        cnt = 0
        # for l in parser.lines(o):
        for l in parser.lines:
            cnt += 1
            debit_cell = rowcol_to_cell(row_pos, debit_pos)
            credit_cell = rowcol_to_cell(row_pos, credit_pos)
            bal_formula = debit_cell + '-' + credit_cell
            c_specs = map(lambda x: self.render(x, self.col_specs_lines_template, 'lines'), wanted_list)
            row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
            row_pos = self.xls_write_row(ws, row_pos, row_data, row_style=self.acc_cell_style)
            if 'draw_line' in l and l['draw_line'] and cnt != acc_cnt:
                row_pos += 1

        # Totals
        debit_start = rowcol_to_cell(acc_start_pos, debit_pos)
        debit_stop = rowcol_to_cell(row_pos - 1, debit_pos)
        debit_formula = 'SUM(%s:%s)' % (debit_start, debit_stop)
        credit_start = rowcol_to_cell(acc_start_pos, credit_pos)
        credit_stop = rowcol_to_cell(row_pos - 1, credit_pos)
        credit_formula = 'SUM(%s:%s)' % (credit_start, credit_stop)
        debit_cell = rowcol_to_cell(row_pos, debit_pos)
        credit_cell = rowcol_to_cell(row_pos, credit_pos)
        bal_formula = debit_cell + '-' + credit_cell
        c_specs = map(lambda x: self.render(x, self.col_specs_lines_template, 'totals'), wanted_list)
        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
        row_pos = self.xls_write_row(ws, row_pos, row_data, row_style=self.rt_cell_style_right)
        return row_pos + 1

    def generate_xls_report(self, parser, _xs, data, objects, wb):
        """
            parser: parser
            _xs: xls Styles
            data: {}
            objects: account.account browse objects
            wb: xls workbook
        """

        self.wanted_list = wanted_list = parser.wanted_list
        self.col_specs_lines_template.update(parser.template_changes)

        self.debit_pos = 'debit' in wanted_list and wanted_list.index('debit')
        self.credit_pos = 'credit' in wanted_list and wanted_list.index('credit')
        if not (self.credit_pos and self.debit_pos) and 'balance' in wanted_list:
            raise orm.except_orm(_('Customisation Error!'),
                _("The 'Balance' field is a calculated XLS field requiring the presence of the 'Debit' and 'Credit' fields !"))

        for o in objects:
            sheet_name = 'Balance des comptes'
            ws = wb.add_sheet(sheet_name)
            ws.panes_frozen = True
            ws.remove_splits = True
            ws.portrait = 0  # Landscape
            ws.fit_width_to_pages = 1
            row_pos = 0

            # set print header/footer
            ws.header_str = self.xls_headers['standard']
            ws.footer_str = self.xls_footers['standard']

            # Top
            row_pos = self._account_title(o, ws, parser, row_pos, xlwt, _xs)
            # Near top
            row_pos = self._meta_headers(o, ws, parser, row_pos, xlwt, _xs)
            # Data
            row_pos = self._account_lines(o, ws, parser, row_pos, xlwt, _xs)

account_balance_xls('report.xls.account_balance_report', 'account.account',
    parser=account_balance_xls_parser)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
