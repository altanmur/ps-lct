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

from xlwt import Workbook, easyxf, Formula
from xlrd import open_workbook, XL_CELL_BLANK
import re
import copy


def get_total_rows(code_tree):
    total_rows = []
    for row, val in code_tree.iteritems():
        if val.get('children', False):
            total_rows += get_total_rows(val['children'])
            total_rows.append(row)
    return total_rows

def write_sum_from_code_tree(sheet, children_code_tree, row, col):
    coords = []
    for child_row in children_code_tree.keys():
        coords.append((child_row, col))
    form = cell_list_sum({'pos': coords})
    set_out_cell(sheet, (row, col), form)

def check_parentship(parent_code, child_code):
    parent_codes = parent_code.split(',')
    child_codes = child_code.split(',')
    return any(all(child_code.startswith(parent_code) for child_code in child_codes) for parent_code in parent_codes)

def add_code_to_tree(code_tree, new_row, new_code):
    new_code_tree = copy.deepcopy(code_tree)

    for row, val in code_tree.iteritems():
        if check_parentship(val['code'], new_code):
            new_code_tree[row]['children'] = add_code_to_tree(code_tree[row]['children'], new_row, new_code)
            return new_code_tree

    new_code_tree[new_row] = {
        'code': new_code,
        'children': {},
    }
    for row, val in code_tree.iteritems():
        if check_parentship(new_code, val['code']):
            new_code_tree[new_row]['children'].update({
                row: copy.deepcopy(val),
            })
            del new_code_tree[row]
    return new_code_tree

def build_code_tree(sheet, col, row1, row2, skip=[]):
    code_tree = {}
    col = get_col(col)
    for row in str_xrange(row1, row2, skip=skip):
        row = get_row(row)
        cell_value = get_cell_value(sheet, (row, col))
        if isinstance(cell_value, unicode) and cell_value[-1].lower() in ['x', 'y', 'z']:
            code = cell_value
        else:
            code = str(int(cell_value))
        code_tree = add_code_to_tree(code_tree, row, code)
    return code_tree

def str_xrange(a, b, skip=[]):
    a, b = int(a), int(b) +1
    for i in xrange(a, b):
        i = str(i)
        if i not in skip:
            yield i

def get_cell_value_by_cell_str(sheet, cell_str):
    return get_cell_value(sheet, get_coord(cell_str))

def get_cell_value(sheet, coord):
    row, col = coord
    if sheet.cell(row, col).ctype == XL_CELL_BLANK:
        return ""
    return sheet.cell(row, col).value

def get_cells_value(sheet, coords):
    values_by_coord = {}
    for coord in coords:
        value_by_coord[coord] = get_cell_value(sheet, coord)
    return values_by_coord

def get_out_cell(out_sheet, coord):
    row = out_sheet._Worksheet__rows.get(coord[0])
    if not row:
        return None
    cell = row._Row__cells.get(coord[1])
    return cell

def set_out_cell(out_sheet, coord, value):
    previous_cell = get_out_cell(out_sheet, coord)
    out_sheet.write(coord[0], coord[1], value)
    if previous_cell:
        new_cell = get_out_cell(out_sheet, coord)
        if new_cell:
            new_cell.xf_idx = previous_cell.xf_idx

def set_out_cells(out_sheet, value_by_coord):
    for coord, value in value_by_coord.iteritems():
        set_out_cell(out_sheet, coord, value)

def set_out_cells_by_cell_str(out_sheet, value_by_cell_str):
    for cell_str, value in value_by_cell_str.iteritems():
        coord = get_coord(cell_str)
        set_out_cell(out_sheet, coord, value)

def get_col_char(col):
    if col < 26:
        return chr(ord("A") + col)
    else:
        return get_col_char(col/26 - 1) + get_col_char(col % 26)

def get_row_char(row):
    return str(row + 1)

def get_row_chars(rows):
    return [get_row_char(row) for row in rows]

def get_char(coord):
    row = get_row_char(coord[0])
    col = get_col_char(coord[1])
    return col + row

def get_col(col_char):
    col = 0
    for i, char in enumerate(reversed(col_char)):
        n = ord(char) - ord("A")
        col += 26**i * (n+1)
    return col - 1

def get_row(row_char):
    return int(row_char) - 1

def get_coord(char):
    m = re.match(r"(?P<col>[A-Z]+)(?P<row>\d+)", char)
    if not m:
        return False
    m = m.groupdict()
    row = get_row(m['row'])
    col = get_col(m['col'])
    return (row, col)

def cell_range_sum(coord_start, coord_end):
    return Formula("SUM(" + get_char(coord_start) + ":" + get_char(coord_end) + ")")

def text_list_sum(texts_by_sign):
    form = ""
    for text in texts_by_sign.get('pos', []):
        form += '+' + text
    if form.startswith('+'):
        form = form[1:]
    for text in  texts_by_sign.get('neg', []):
        form += '-' + text
    return Formula(form)

def cell_list_sum(coords_by_sign) :
    texts_by_sign = {}
    for sign, coords in coords_by_sign.iteritems():
        texts_by_sign[sign] = []
        for coord in coords:
            texts_by_sign[sign].append(get_char(coord))
    return text_list_sum(texts_by_sign)

def num_list_sum(nums_by_sign):
    texts_by_sign = {}
    for sign, nums in coords_by_sign:
        texts_by_sign[sign] = []
        for num in nums:
            texts_by_sign[sign].append(str(num))
    return text_list_sum(texts_by_sign)

def write_row_sum(sheet, rows, sum_col, pos_cols=[], neg_cols=[]):
    values = {}
    for row in rows:
        values[sum_col + row] = text_list_sum({
                                'pos': [col + row for col in pos_cols],
                                'neg': [col + row for col in neg_cols],
                            })
    set_out_cells_by_cell_str(sheet, values)
