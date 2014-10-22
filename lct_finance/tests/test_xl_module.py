from openerp.tests.common import TransactionCase
from ..tools import xl_module as xlm
import copy

class TestXlModule(TransactionCase):

    def test_coord_str_conversion(self):
        self.assertEqual(xlm.get_row_str(52), "53")
        self.assertEqual(xlm.get_col_str(14033), "TST")
        self.assertEqual(xlm.get_coord_str((52, 14033)), "TST53")

    def test_str_coord_conversion(self):
        self.assertEqual(xlm.get_row("53"), 52)
        self.assertEqual(xlm.get_col("TST"), 14033)
        self.assertEqual(xlm.get_coord("TST53"), (52, 14033))

    def test_build_code_tree(self):
        code_tree = {
            1: {
                'code': '11',
                'children': {
                    2: {'code': '112'},
                    3: {
                        'code': '1115',
                        'children': {
                            8: '11157'
                        },
                    },
                    4: {'code': '113'},
                },
            },
            6: {
                'code': '16',
                'children': {
                    7: {
                        'code': '165',
                        'children': {
                            5: {'code': '1658'},
                        }
                    }
                }
            }
        }

        new_code_tree = xlm.add_code_to_tree(code_tree, 9, '111')

        expected_code_tree = copy.deepcopy(code_tree)
        expected_code_tree[1]['children'].update({
            9: {
                'code': '111',
                'children': {
                    3: copy.deepcopy(expected_code_tree[1]['children'][3])
                },
        }})
        del expected_code_tree[1]['children'][3]

        self.assertEqual(new_code_tree, expected_code_tree)
