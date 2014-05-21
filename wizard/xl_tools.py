import xlwt,xlrd



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


