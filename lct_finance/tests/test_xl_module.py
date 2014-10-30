from openerp.tests.common import TransactionCase
from ..tools import xl_module as xlm
import copy
import re

class TestXlModule(TransactionCase):

    def setUp(self):
        super(TestXlModule, self).setUp()
        self.code_tree = {
            1: {
                'code': '11',
                'children': {
                    2: {'code': '112'},
                    3: {
                        'code': '1115',
                        'children': {
                            8: '11157',
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

    def test_coord_str_conversion(self):
        self.assertEqual(xlm.get_row_str(52), "53")
        self.assertEqual(xlm.get_col_str(14033), "TST")
        self.assertEqual(xlm.get_coord_str((52, 14033)), "TST53")

    def test_str_coord_conversion(self):
        self.assertEqual(xlm.get_row("53"), 52)
        self.assertEqual(xlm.get_col("TST"), 14033)
        self.assertEqual(xlm.get_coord("TST53"), (52, 14033))

    def test_add_code_to_tree(self):
        code_tree = self.code_tree

        xlm.add_code_to_tree(code_tree, 9, '111')

        expected_code_tree = {
            1: {
                'code': '11',
                'children': {
                    9: {
                        'code': '111',
                        'children': {
                            3: {
                                'code': '1115',
                                'children': {
                                    8: '11157',
                                },
                            },
                        },
                    },
                    4: {'code': '113'},
                    2: {'code': '112'},
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

        self.assertEqual(code_tree, expected_code_tree)


    def test_add_code_group_to_tree(self):
        code_tree = self.code_tree

        xlm.add_code_to_tree(code_tree, 9, '111,112')

        expected_code_tree = {
            1: {
                'code': '11',
                'children': {
                    9: {
                        'code': '111,112',
                        'children': {
                            3: {
                                'code': '1115',
                                'children': {
                                    8: '11157',
                                },
                            },
                            2: {'code': '112'},
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

        self.assertEqual(code_tree, expected_code_tree)

    def test_cell_list_sum(self):
        coords_by_sign = {
            'pos': [(0, 1), (10, 5)],
            'neg': [(5, 8), (4, 9), (10, 7)],
        }

        list_sum = xlm.cell_list_sum(coords_by_sign).text()

        terms = ['+B1', '+F11', '-I6', '-J5', '-H11']

        self.assertEqual(len(list_sum) + 1, sum(len(term) for term in terms))

        for term in terms:
            try:
                self.assertIn(term, list_sum)
            except:
                self.assertTrue(list_sum.startswith(term.lstrip('+')))

