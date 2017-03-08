import openpyxl
import csv
import os


XLS_PATH = 'product.xlsx'
CSV_PATH = 'data'
MODEL_NAME = 'product.product'

HEADER_ROW = 2
XMLID_TAIL = '_j17'

# Might worth to do this with xmlrpc
MAP_XMLIDS = {
    'category_id/id': {
        'I': 'lct_product_category_import',
        'E': 'lct_product_category_export',
        'Z': 'lct_product_category_export_e_r',
    },
    'sub_category_id/id': {
        'None': 'lct_product_sub_category_localimport',
        'T1': 'lct_product_sub_category_transitsahel',
        'T2': 'lct_product_sub_category_transitcoastal',
        'FZ': 'lct_product_sub_category_freezone',
    },
    'size_id/id': {
        '20': 'lct_product_size_20',
        '40': 'lct_product_size_40',
    },
    'status_id/id': {
        'F': 'lct_product_status_full',
        'E': 'lct_product_status_empty',
    },
    'service_id/id': {
        'INS': 'lct_product_service_inspection',
        'PTI': 'lct_product_service_pretripinspection',
        'SCC': 'lct_product_service_scanning',
        'REP': 'lct_product_service_repaired',
        'UMC': 'lct_product_service_umccinspection',
        'WAS': 'lct_product_service_washing',
        'CFS': 'lct_product_service_cfs',
        'CLN': 'lct_product_service_cleaning',
        'CUS': 'lct_product_service_customs',
        'EXM': 'lct_product_service_deliveryforexamination',
        'DDA': 'lct_product_service_directdelivery',
    },
}

def _get_cell_name(col, row):
    str_col = ''
    while col:
        str_col = chr((col-1)%26 + 65) + str_col
        col = (col-1) / 26
    return '%s%s' %(str_col, row)

def _get_val(sheet, col, row):
    cell_name = _get_cell_name(col, row)
    return sheet[cell_name].value or None

def _mapped_values(key, value, map_xmlids=MAP_XMLIDS):
    if key not in map_xmlids:
        if value == 'YES':
            return 1
        if value == 'NO':
            return 0
        return value
    return map_xmlids.get(key, {}).get(value.__str__())

def _name2xmlid(name, tail=XMLID_TAIL):
    res = ''.join(l for l in name.replace(' - ', '-') if l.isalnum() or l == ' ').replace(' ', '_').lower() + tail
    res = res.replace('export_', 'e')
    res = res.replace('import', 'i')
    res = res.replace('free_zone', 'fz')
    res = res.replace('full', 'f')
    res = res.replace('empty', 'm')
    res = res.replace('products', 'p')

    res = res.replace('with_bundle_', 'wb')
    res = res.replace('neighboring_countries_', 'nc')
    res = res.replace('cargostuffing_', 'cs')
    res = res.replace('cargodestuffing_', 'cds')
    res = res.replace('additional_storage', 'ad')
    res = res.replace('with_bundle', 'wb')
    res = res.replace('on_truck', 'ot')
    res = res.replace('outside_port_yard', 'opy')
    res = res.replace('inside_port_yard', 'ipy')
    if len(res) >= 64:
        print "XML_ID is limited to 64 (%s)" %res
    return res

def _sheet2csv(sheet, header_row=HEADER_ROW):
    path = '%s/%s' %(CSV_PATH, sheet.title)
    file = '%s.csv' %MODEL_NAME
    if not os.path.exists(path):
        os.makedirs(path)
    res = '%s/%s' %(path, file)
    with open(res, 'wb') as csvfile:
        spamwriter = csv.writer(csvfile, delimiter=',', quotechar='"')

        i, columns_ids = 1, {}
        while _get_val(sheet, i, header_row):
            columns_ids.update({
                _get_val(sheet, i, header_row): i
            })
            i += 1
        header = [k for k in columns_ids.keys()]
        header.append('id')
        spamwriter.writerow(header)

        j = header_row + 1
        while _get_val(sheet, 1, j):
            line = [_mapped_values(k, _get_val(sheet, i, j)) for k,i in columns_ids.items()]
            line.append(_name2xmlid(_get_val(sheet, columns_ids.get('name'), j)))
            spamwriter.writerow(line)
            j += 1
    return res


wb = openpyxl.load_workbook(XLS_PATH)
sheet = wb.get_active_sheet()
paths = []

for sn in wb.sheetnames:
    sheet = wb.get_sheet_by_name(sn)
    paths.append(_sheet2csv(sheet))

print '\n'.join(paths)
