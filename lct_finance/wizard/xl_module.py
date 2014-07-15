
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


from xlwt import Workbook,easyxf,Formula
from xlrd import open_workbook,XL_CELL_BLANK
from xlutils.copy import copy

# Formats

def getOutCell(outSheet, colIndex, rowIndex):
    row = outSheet._Worksheet__rows.get(rowIndex)
    if not row: return None
    cell = row._Row__cells.get(colIndex)
    return cell

def setOutCell(outSheet, col, row, value):
    previousCell = getOutCell(outSheet, col, row)
    outSheet.write(row, col, value)
    if previousCell:
        newCell = getOutCell(outSheet, col, row)
        if newCell:
            newCell.xf_idx = previousCell.xf_idx

def get_char(i) :
    if i<26:
        return chr(ord("A")+i)
    else :
        return get_char(i/26-1) + get_char(i%26)

def range_sum(i1, j1, i2, j2) :
    return Formula("SUM(" + get_char(j1) + str(i1+1) + ":" + get_char(j2) + str(i2+1) + ")")

def list_sum(indices, text=False) :
    form = ""
    for i in indices:
        if i[2]>0 :
            form += "+" + get_char(i[1]) + str(i[0]+1)
        elif i[2]<0 :
            form += "-" + get_char(i[1]) + str(i[0]+1)
    if form[0] == "+":
        form = form[1:]
    if text:
        return form
    else:
        return Formula(form)




def xl_format(f=""):
    return {
        "bold" : 'font: bold 1;',
        "hor-center" : 'alignment: horizontal center;',
        "hor-right" : 'alignment: horizontal right;',
        "hor-left" : 'alignment: horizontal left;',
        "vert-center" : 'alignment: vertical center;',
        "italic" : 'font: italic 1;',
        "text-white" : 'font: color white;',
        "text-red" : 'font: color red;',
        "text-12" : 'font: height 240;',
        "text-14" : 'font: height 280;',
        "background-green" : 'pattern: pattern solid, fore_color green;',
        "background-black" : 'pattern: pattern solid, fore_color black;',
        "wrap" : 'alignment: wrap 1;',
        "border-l" : 'border : left medium;',
        "border-r" : 'border : right medium;',
        "border-b" : 'border : bottom medium;',
        "border-t" : 'border : top medium;',
        "background-blue" : 'pattern: pattern solid, fore_color blue;',
        "background-black" : 'pattern: pattern solid, fore_color black;',
    }[f]


def cell_format(format_list=()) :
    format_s = ""
    for f in format_list :
        format_s += xl_format(f)
    return easyxf(format_s)


line = cell_format((
    "vert-center",
    "hor-right",
    "wrap",
))
black_line = cell_format((
    "vert-center",
    "wrap",
    "text-white",
    "background-black",
))
black_red_line = cell_format((
    "vert-center",
    "wrap",
    "text-red",
    "background-black",
))
blue_line = cell_format((
    "vert-center",
    "wrap",
    "text-white",
    "background-blue",
))
blue_red_line = cell_format((
    "vert-center",
    "wrap",
    "text-red",
    "background-blue",
))
total_left = cell_format((
    "bold",
    "hor-center",
    "vert-center",
    "border-t",
    "border-l",
    "border-b",
    "wrap",
))
total_center = cell_format((
    "bold",
    "hor-center",
    "vert-center",
    "border-t",
    "border-b",
))
total_right = cell_format((
    "bold",
    "hor-center",
    "vert-center",
    "border-t",
    "border-r",
    "border-b",
    "wrap",
))
total_blue = cell_format((
    "bold",
    "vert-center",
    "hor-center",
    "border-t",
    "border-b",
    "text-white",
    "background-blue",
))
total_blue_red = cell_format((
    "bold",
    "vert-center",
    "hor-center",
    "border-t",
    "border-b",
    "text-red",
    "background-blue",
))
total_black = cell_format((
    "bold",
    "vert-center",
    "hor-center",
    "border-t",
    "border-b",
    "text-white",
    "background-black",
))
total_black_red = cell_format((
    "bold",
    "vert-center",
    "hor-center",
    "border-t",
    "border-b",
    "text-red",
    "background-black",
))
title1 = cell_format((
    "hor-center",
    "vert-center",
    "background-black",
    "text-white",
    "text-12",
))
title2 = cell_format((
    "bold",
    "vert-center",
    "background-green",
    "text-white",
    "text-14",
))
label_left = cell_format((
    "bold",
    "italic",
    "vert-center",
    "hor-center",
    "border-l",
    "border-t",
    "border-b",
    "wrap",
))
label_right = cell_format((
    "bold",
    "italic",
    "vert-center",
    "hor-center",
    "border-r",
    "border-t",
    "border-b",
    "wrap",
))
label_center = cell_format((
    "bold",
    "italic",
    "vert-center",
    "hor-center",
    "border-t",
    "border-b",
    "wrap",
))
label_black = cell_format((
    "bold",
    "italic",
    "vert-center",
    "hor-center",
    "border-t",
    "border-b",
    "wrap",
    "background-black",
    "text-white",
))
label_black_red = cell_format((
    "bold",
    "italic",
    "vert-center",
    "hor-center",
    "border-t",
    "border-b",
    "wrap",
    "background-black",
    "text-red",
))
label_month = cell_format((
    "bold",
    "italic",
    "vert-center",
    "hor-center",
    "border-t",
    "border-b",
    "wrap",
    "background-blue",
    "text-white",
))
label_blue_red = cell_format((
    "bold",
    "italic",
    "vert-center",
    "hor-center",
    "border-t",
    "border-b",
    "wrap",
    "background-blue",
    "text-red",
))
as_name = cell_format((
    "bold",
    "italic",
    "hor-center",
    "vert-center",
    "wrap",
    "border-l",
))
line_right = cell_format((
    "vert-center",
    "hor-right",
    "wrap",
    "border-r",
))
line_left = cell_format((
    "vert-center",
    "hor-left",
    "wrap",
    "border-l",
))
