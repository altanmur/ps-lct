
import xlwt,xlrd



def getOutCell(outSheet, colIndex, rowIndex):
    row = outSheet._Worksheet__rows.get(rowIndex)
    if not row: return None
    cell = row._Row__cells.get(colIndex)
    return cell

def writeToCell(outSheet, col, row, value):
    previousCell = self._getOutCell(outSheet, col, row)
    outSheet.write(row, col, value)
    if previousCell:
        newCell = self._getOutCell(outSheet, col, row)
        if newCell:
            newCell.xf_idx = previousCell.xf_idx

   
