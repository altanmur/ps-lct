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

from openerp.osv import fields, osv
import openerp.addons.decimal_precision as dp

class account_account(osv.osv):
    _inherit = 'account.account'

    _columns = {
        # Overridden; exactly the same:
        'balance': fields.function(lambda self, *args, **kwargs: self.__compute(*args, **kwargs),
            digits_compute=dp.get_precision('Account'), string='Balance', multi='balance'),
        'credit': fields.function(lambda self, *args, **kwargs: self.__compute(*args, **kwargs),
            fnct_inv=lambda self, *args, **kwargs: self._set_credit_debit(*args, **kwargs),
            digits_compute=dp.get_precision('Account'), string='Credit', multi='balance'),
        'debit': fields.function(lambda self, *args, **kwargs: self.__compute(*args, **kwargs),
            fnct_inv=lambda self, *args, **kwargs: self._set_credit_debit(*args, **kwargs),
            digits_compute=dp.get_precision('Account'), string='Debit', multi='balance'),
        'foreign_balance': fields.function(lambda self, *args, **kwargs: self.__compute(*args, **kwargs),
            digits_compute=dp.get_precision('Account'), string='Foreign Balance', multi='balance',
            help="Total amount (in Secondary currency) for transactions held in secondary currency for this account."),
        'adjusted_balance': fields.function(lambda self, *args, **kwargs: self.__compute(*args, **kwargs),
            digits_compute=dp.get_precision('Account'), string='Adjusted Balance', multi='balance',
            help="Total amount (in Company currency) for transactions held in secondary currency for this account."),
        'unrealized_gain_loss': fields.function(lambda self, *args, **kwargs: self.__compute(*args, **kwargs),
            digits_compute=dp.get_precision('Account'), string='Unrealized Gain or Loss', multi='balance',
            help="Value of Loss or Gain due to changes in exchange rate when doing multi-currency transactions."),
        # Added
        'prev_credit': fields.function(lambda self, *args, **kwargs: self.__compute(*args, **kwargs),
            digits_compute=dp.get_precision('Account'), string='Previous Credit', multi='balance'),
        'prev_debit': fields.function(lambda self, *args, **kwargs: self.__compute(*args, **kwargs),
            digits_compute=dp.get_precision('Account'), string='Previous Debit', multi='balance'),
        'prev_balance': fields.function(lambda self, *args, **kwargs: self.__compute(*args, **kwargs),
            digits_compute=dp.get_precision('Account'), string='Previous Balance', multi='balance'),
        # 'start_balance': fields.float('Starting Balance', digits=(16, 2)),
    }

    def __compute(self, cr, uid, ids, field_names, arg=None, context=None,
                  query='', query_params=()):
        """ compute the balance, debit and/or credit for the provided
        account ids
        Arguments:
        `ids`: account ids
        `field_names`: the fields to compute (a list of any of
                       'balance', 'debit' and 'credit')
        `arg`: unused fields.function stuff
        `query`: additional query filter (as a string)
        `query_params`: parameters for the provided query string
                        (__compute will handle their escaping) as a
                        tuple
        """
        mapping = {
            'balance': "COALESCE(SUM(l.debit),0) - COALESCE(SUM(l.credit), 0) as balance",
            'debit': "COALESCE(SUM(l.debit), 0) as debit",
            'credit': "COALESCE(SUM(l.credit), 0) as credit",
            # by convention, foreign_balance is 0 when the account has no secondary currency, because the amounts may be in different currencies
            'foreign_balance': "(SELECT CASE WHEN currency_id IS NULL THEN 0 ELSE COALESCE(SUM(l.amount_currency), 0) END FROM account_account WHERE id IN (l.account_id)) as foreign_balance",
        }
        #get all the necessary accounts
        children_and_consolidated = self._get_children_and_consol(cr, uid, ids, context=context)
        #compute for each account the balance/debit/credit from the move lines
        null_result = dict((fn, 0.0) for fn in field_names)
        accounts = dict([(x, null_result.copy()) for x in children_and_consolidated])
        res = {}
        if children_and_consolidated:
            aml_query = self.pool.get('account.move.line')._query_get(cr, uid, context=context)

            wheres = [""]
            if query.strip():
                wheres.append(query.strip())
            if aml_query.strip():
                wheres.append(aml_query.strip())
            for special in ['f', 't']:
                filters = " AND ".join(wheres)
                filters += " AND l.period_id IN (SELECT id FROM account_period WHERE special = '%s') " % special
                # IN might not work ideally in case there are too many
                # children_and_consolidated, in that case join on a
                # values() e.g.:
                # SELECT l.account_id as id FROM account_move_line l
                # INNER JOIN (VALUES (id1), (id2), (id3), ...) AS tmp (id)
                # ON l.account_id = tmp.id
                # or make _get_children_and_consol return a query and join on that
                request = ("SELECT l.account_id as id, " +\
                           ', '.join(mapping.values()) +
                           " FROM account_move_line l" \
                           " WHERE l.account_id IN %s " \
                                + filters +
                           " GROUP BY l.account_id")
                params = (tuple(children_and_consolidated),) + query_params
                cr.execute(request, params)

                for row in cr.dictfetchall():
                    if special == 'f':
                        # Due to the order in which we do true, false, this shouldn't
                        # be necessary, but this dependence on the order in which we
                        # work has bitten me in the rear end more than once, so let's
                        # foolproof this:
                        if accounts[row['id']]['balance']:
                            row['balance'] += accounts[row['id']]['balance']
                        # Now we continue...
                        accounts[row['id']].update(row)
                    else:
                        accounts[row['id']].update(
                            {
                                'prev_credit': row['credit'],
                                'prev_debit': row['debit'],
                                'balance': accounts[row['id']]['balance'] + row['balance'],
                            })

            # consolidate accounts with direct children
            children_and_consolidated.reverse()
            brs = list(self.browse(cr, uid, children_and_consolidated, context=context))
            sums = {}
            currency_obj = self.pool.get('res.currency')
            while brs:
                current = brs.pop(0)
                for fn in field_names:
                    sums.setdefault(current.id, {})[fn] = accounts.get(current.id, {}).get(fn, 0.0)
                    for child in current.child_id:
                        if child.company_id.currency_id.id == current.company_id.currency_id.id:
                            sums[current.id][fn] += sums[child.id][fn]
                        else:
                            sums[current.id][fn] += currency_obj.compute(cr, uid, child.company_id.currency_id.id, current.company_id.currency_id.id, sums[child.id][fn], context=context)

                # as we have to relay on values computed before this is calculated separately than previous fields
                if current.currency_id and current.exchange_rate and \
                            ('adjusted_balance' in field_names or 'unrealized_gain_loss' in field_names):
                    # Computing Adjusted Balance and Unrealized Gains and losses
                    # Adjusted Balance = Foreign Balance / Exchange Rate
                    # Unrealized Gains and losses = Adjusted Balance - Balance
                    adj_bal = sums[current.id].get('foreign_balance', 0.0) / current.exchange_rate
                    sums[current.id].update({'adjusted_balance': adj_bal, 'unrealized_gain_loss': adj_bal - sums[current.id].get('balance', 0.0)})

            for id in ids:
                res[id] = sums.get(id, null_result)
        else:
            for id in ids:
                res[id] = null_result
        return res
