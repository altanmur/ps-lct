# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-TODAY OpenERP S.A. <http://www.openerp.com>
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

from openerp.addons.account.report.account_general_ledger import general_ledger

# Monkey see, monkey patch!
def patch_lines(self, account):
    """ Return all the account_move_line of account with their account code counterparts """
    move_state = ['draft','posted']
    if self.target_move == 'posted':
        move_state = ['posted', '']
    # First compute all counterpart strings for every move_id where this account appear.
    # Currently, the counterpart info is used only in landscape mode
    sql = """
        SELECT m1.move_id,
            array_to_string(ARRAY(SELECT DISTINCT a.code
                                      FROM account_move_line m2
                                      LEFT JOIN account_account a ON (m2.account_id=a.id)
                                      WHERE m2.move_id = m1.move_id
                                      AND m2.account_id<>%%s), ', ') AS counterpart
            FROM (SELECT move_id
                    FROM account_move_line l
                    LEFT JOIN account_move am ON (am.id = l.move_id)
                    WHERE am.state IN %s and %s AND l.account_id = %%s GROUP BY move_id) m1
    """% (tuple(move_state), self.query)
    self.cr.execute(sql, (account.id, account.id))
    counterpart_res = self.cr.dictfetchall()
    counterpart_accounts = {}
    for i in counterpart_res:
        counterpart_accounts[i['move_id']] = i['counterpart']
    del counterpart_res

    # Then select all account_move_line of this account
    if self.sortby == 'sort_journal_partner':
        sql_sort='j.code, p.name, l.move_id'
    else:
        sql_sort='l.create_date, l.move_id'
    sql = """
        SELECT l.id AS lid, l.create_date AS ldate, j.code AS lcode, l.currency_id, l.amount_currency, l.ref AS lref,
            l.name AS lname, COALESCE(l.debit,0) AS debit, COALESCE(l.credit,0) AS credit, l.period_id AS lperiod_id,
            l.partner_id AS lpartner_id, m.name AS move_name, m.id AS mmove_id,per.code as period_code,
            c.symbol AS currency_code, i.id AS invoice_id, i.type AS invoice_type, i.number AS invoice_number,
            p.name AS partner_name
        FROM account_move_line l
        JOIN account_move m on (l.move_id=m.id)
        LEFT JOIN res_currency c on (l.currency_id=c.id)
        LEFT JOIN res_partner p on (l.partner_id=p.id)
        LEFT JOIN account_invoice i on (m.id =i.move_id)
        LEFT JOIN account_period per on (per.id=l.period_id)
        JOIN account_journal j on (l.journal_id=j.id)
        WHERE %s AND m.state IN %s AND l.account_id = %%s ORDER by %s
    """ %(self.query, tuple(move_state), sql_sort)
    self.cr.execute(sql, (account.id,))
    res_lines = self.cr.dictfetchall()
    res_init = []
    if res_lines and self.init_balance:
        #FIXME: replace the label of lname with a string translatable
        sql = """
            SELECT 0 AS lid, '' AS ldate, '' AS lcode, COALESCE(SUM(l.amount_currency),0.0) AS amount_currency,
                '' AS lref, 'Initial Balance' AS lname, COALESCE(SUM(l.debit),0.0) AS debit,
                COALESCE(SUM(l.credit),0.0) AS credit, '' AS lperiod_id, '' AS lpartner_id, '' AS move_name,
                '' AS mmove_id, '' AS period_code, '' AS currency_code, NULL AS currency_id, '' AS invoice_id,
                '' AS invoice_type, '' AS invoice_number, '' AS partner_name
            FROM account_move_line l
            LEFT JOIN account_move m on (l.move_id=m.id)
            LEFT JOIN res_currency c on (l.currency_id=c.id)
            LEFT JOIN res_partner p on (l.partner_id=p.id)
            LEFT JOIN account_invoice i on (m.id =i.move_id)
            JOIN account_journal j on (l.journal_id=j.id)
            WHERE %s AND m.state IN %s AND l.account_id = %%s
        """ %(self.init_query, tuple(move_state))
        self.cr.execute(sql, (account.id,))
        res_init = self.cr.dictfetchall()
    res = res_init + res_lines
    account_sum = 0.0
    for l in res:
        l['move'] = l['move_name'] != '/' and l['move_name'] or ('*'+str(l['mmove_id']))
        l['partner'] = l['partner_name'] or ''
        account_sum += l['debit'] - l['credit']
        l['progress'] = account_sum
        l['line_corresp'] = l['mmove_id'] == '' and ' ' or counterpart_accounts[l['mmove_id']].replace(', ',',')
        # Modification of amount Currency
        if l['credit'] > 0:
            if l['amount_currency'] != None:
                l['amount_currency'] = abs(l['amount_currency']) * -1
        if l['amount_currency'] != None:
            self.tot_currency = self.tot_currency + l['amount_currency']
    return res

general_ledger.lines = patch_lines
