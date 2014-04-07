# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright 2012-2013 Camptocamp SA (Guewen Baconnier)
#    Copyright (C) 2010   Sébastien Beau
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

from openerp.osv.orm import AbstractModel, TransientModel
from datetime import datetime, timedelta
from tools import DEFAULT_SERVER_DATE_FORMAT

import logging
from contextlib import contextmanager

_logger = logging.getLogger(__name__)

@contextmanager
def commit(cr):
    """
    Commit the cursor after the ``yield``, or rollback it if an
    exception occurs.

    Warning: using this method, the exceptions are logged then discarded.
    """
    try:
        yield
    except Exception, e:
        cr.rollback()
        raise
        _logger.exception('Error during an automatic workflow action.')
    else:
        cr.commit()


class easy_reconcile_simple(AbstractModel):

    _name = 'easy.reconcile.simple'
    _inherit = 'easy.reconcile.base'

    # has to be subclassed
    # field name used as key for matching the move lines
    _key_field = None

    def _is_finish(self, line, next_line, context=None):
        return line[self._key_field] != next_line[self._key_field]

    def rec_auto_lines_simple(self, cr, uid, rec, lines, context=None):
        if context is None:
            context = {}

        if self._key_field is None:
            raise ValueError("_key_field has to be defined")

        count = 0
        res = []
        while (count < len(lines)):
            for i in xrange(count+1, len(lines)):
                writeoff_account_id = False
                if self._is_finish(lines[count], lines[i], context=context):
                    break

                check = False
                if lines[count]['credit'] > 0 and lines[i]['debit'] > 0:
                    credit_line = lines[count]
                    debit_line = lines[i]
                    check = True
                elif lines[i]['credit'] > 0  and lines[count]['debit'] > 0:
                    credit_line = lines[i]
                    debit_line = lines[count]
                    check = True
                if not check:
                    continue

                reconciled, dummy = self._reconcile_lines(
                    cr, uid, rec, [credit_line, debit_line],
                    allow_partial=False, context=context)
                if reconciled:
                    res += [credit_line['id'], debit_line['id']]
                    del lines[i]
                    break
            count += 1
        return res, []  # empty list for partial, only full rec in "simple" rec

    def _simple_order(self, rec, *args, **kwargs):
        return "ORDER BY account_move_line.%s" % self._key_field

    def _action_rec(self, cr, uid, rec, context=None):
        """Match only 2 move lines, do not allow partial reconcile"""
        select = self._select(rec)
        select += ", account_move_line.%s " % self._key_field
        where, params = self._where(rec)
        where += " AND account_move_line.%s IS NOT NULL " % self._key_field

        where2, params2 = self._get_filter(cr, uid, rec, context=context)
        query = ' '.join((
            select,
            self._from(rec),
            where, where2,
            self._simple_order(rec)))

        cr.execute(query, params + params2)
        lines = cr.dictfetchall()
        return self.rec_auto_lines_simple(cr, uid, rec, lines, context)


class easy_reconcile_simple_name(TransientModel):

    _name = 'easy.reconcile.simple.name'
    _inherit = 'easy.reconcile.simple'

    # has to be subclassed
    # field name used as key for matching the move lines
    _key_field = 'name'


class easy_reconcile_simple_partner(TransientModel):

    _name = 'easy.reconcile.simple.partner'
    _inherit = 'easy.reconcile.simple'

    # has to be subclassed
    # field name used as key for matching the move lines
    _key_field = 'partner_id'


class easy_reconcile_simple_reference(TransientModel):

    _name = 'easy.reconcile.simple.reference'
    _inherit = 'easy.reconcile.simple'

    # has to be subclassed
    # field name used as key for matching the move lines
    _key_field = 'ref'


class easy_reconcile_simple_date(TransientModel):
    _name = 'easy.reconcile.simple.date'
    _inherit = 'easy.reconcile.simple'
    _auto = True  # False when inherited from AbstractModel

    # has to be subclassed
    # field name used as key for matching the move lines
    _key_field = 'date'


    def _is_finish(self, line, next_line, context=None):
        line_date = datetime.strptime(line['date'], DEFAULT_SERVER_DATE_FORMAT)
        next_line_date = datetime.strptime(next_line['date'], DEFAULT_SERVER_DATE_FORMAT)
        return not(timedelta(days=-30) <= line_date - next_line_date <= timedelta(days=30))


class easy_reconcile_all_move_partner(TransientModel):
    _name = 'easy.reconcile.all.move.partner'
    _inherit = 'easy.reconcile.base'
    _auto = True  # False when inherited from AbstractModel
    
    def _action_rec(self, cr, uid, rec, context=None):
        """Match all move lines of a partner, do not allow partial reconcile"""
        res = []
        query = \
        """SELECT partner_id FROM account_move_line
            WHERE account_id=%s AND reconcile_id is NULL
            GROUP BY partner_id
            HAVING  sum(debit) = sum(credit)
        """
        move_line_obj = self.pool['account.move.line']
        params = (rec.account_id.id,)
        cr.execute(query, params)
        partner_ids = cr.fetchall()
        for partner_id in partner_ids:
            line_ids = move_line_obj.search(cr, uid, [
                ('partner_id', '=', partner_id[0]),
                ('account_id', '=', rec.account_id.id),
                ('reconcile_id', '=', False),
                ], context=context)
            with commit(cr):
                move_line_obj.reconcile(
                    cr, uid,
                    line_ids,
                    type='auto',
                    context=context)
                print 'reconcile', line_ids
                res += line_ids
        return res, []


