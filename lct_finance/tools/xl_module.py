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

from xlwt import Formula
from xlrd import XL_CELL_BLANK
import re
import copy

def xrange_skip(a, b, skip=[]):
    for i in xrange(a, b):
        if i not in skip:
            yield i

def str_xrange_skip(a, b, skip=[]):
    for i in xrange(int(a), int(b) + 1):
        i = str(i)
        if i not in skip:
            yield i

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

def check_parentship(parents, childs):
    parent_codes = parents.split(',')
    child_codes = childs.split(',')
    return any(all(child_code.startswith(parent_code) for child_code in child_codes) for parent_code in parent_codes)

def add_code_to_tree(code_tree, new_row, new_code):
    for row, val in code_tree.items():
        if check_parentship(val['code'], new_code):
            return add_code_to_tree(code_tree[row]['children'], new_row, new_code)

    code_tree[new_row] = {
        'code': new_code,
        'children': {},
    }
    for row, val in code_tree.items():
        if row != new_row and check_parentship(new_code, val['code']):
            code_tree[new_row]['children'].update({row: copy.deepcopy(val)})
            del code_tree[row]

def build_code_tree(sheet, col_str, row_str1, row_str2, skip=[]):
    code_tree = {}
    col = get_col(col_str)
    for row_str in str_xrange_skip(row_str1, row_str2, skip=skip):
        row = get_row(row_str)
        cell_value = get_cell_value(sheet, (row, col))
        if isinstance(cell_value, unicode) and cell_value[-1].lower() in ['x', 'y', 'z']:
            code = cell_value
        else:
            code = str(int(cell_value))
        add_code_to_tree(code_tree, row, code)
    return code_tree

def get_cell_value_by_coord_str(sheet, coord_str):
    return get_cell_value(sheet, get_coord(coord_str))

def get_cell_value(sheet, coord):
    row, col = coord
    if sheet.cell(row, col).ctype == XL_CELL_BLANK:
        return ""
    return sheet.cell(row, col).value

def get_cells_value(sheet, coords):
    return {coord: get_cell_value(sheet, coord) for coord in coords}

def get_out_cell(sheet, coord):
    row = sheet._Worksheet__rows.get(coord[0])
    if not row:
        return None
    cell = row._Row__cells.get(coord[1])
    return cell

def set_out_cell(sheet, coord, value):
    previous_cell = get_out_cell(sheet, coord)
    sheet.write(coord[0], coord[1], value)
    if previous_cell:
        new_cell = get_out_cell(sheet, coord)
        if new_cell:
            new_cell.xf_idx = previous_cell.xf_idx

def set_out_cells(sheet, value_by_coord):
    for coord, value in value_by_coord.iteritems():
        set_out_cell(sheet, coord, value)

def set_out_cells_by_coord_str(sheet, value_by_coord_str):
    for coord_str, value in value_by_coord_str.iteritems():
        coord = get_coord(coord_str)
        set_out_cell(sheet, coord, value)

def get_col_str(col):
    if col < 26:
        return chr(ord("A") + col)
    else:
        return get_col_str(col/26-1) + get_col_str(col%26)

def get_row_str(row):
    return str(row + 1)

def get_row_strs(rows):
    return [get_row_str(row) for row in rows]

def get_coord_str(coord):
    row = get_row_str(coord[0])
    col = get_col_str(coord[1])
    return col + row

def get_col(col_str):
    col = 0
    for i, char in enumerate(reversed(col_str)):
        n = ord(char) - ord("A")
        col += 26**i * (n+1)
    return col - 1

def get_row(row_str):
    return int(row_str) - 1

def get_coord(coord_str):
    m = re.match(r"(?P<col>[A-Z]+)(?P<row>\d+)", coord_str)
    if not m:
        return False
    m_dict = m.groupdict()
    row = get_row(m_dict['row'])
    col = get_col(m_dict['col'])
    return (row, col)

def cell_range_sum(coord_start, coord_end):
    return Formula("SUM(" + get_coord_str(coord_start) + ":" + get_coord_str(coord_end) + ")")

def text_list_sum(texts_by_sign):
    form = ""
    for text in texts_by_sign.get('pos', []):
        form += '+' + text
    for text in  texts_by_sign.get('neg', []):
        form += '-' + text
    if form.startswith('+'):
        form = form[1:]
    return Formula(form)

def cell_list_sum(coords_by_sign) :
    texts_by_sign = {}
    for sign, coords in coords_by_sign.iteritems():
        texts_by_sign[sign] = []
        for coord in coords:
            texts_by_sign[sign].append(get_coord_str(coord))
    return text_list_sum(texts_by_sign)

def write_row_sum(sheet, rows, sum_col, pos_cols=[], neg_cols=[]):
    values = {}
    for row in rows:
        values[sum_col + row] = text_list_sum({
                                'pos': [col + row for col in pos_cols],
                                'neg': [col + row for col in neg_cols],
                            })
    set_out_cells_by_coord_str(sheet, values)
