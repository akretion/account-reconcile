# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Joel Grand-Guillaume
#    Copyright 2011-2012 Camptocamp SA
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
import sys
import traceback

import psycopg2

from openerp.tools.translate import _
import datetime
from openerp.osv.orm import Model
from openerp.osv import fields, osv
from parser import new_bank_statement_parser
from openerp.tools.config import config


class AccountStatementProfil(Model):
    _inherit = "account.statement.profile"

    def get_import_type_selection(self, cr, uid, context=None):
        """
        Has to be inherited to add parser
        """
        return [('generic_csvxls_so', 'Generic .csv/.xls based on SO Name')]

    def _get_import_type_selection(self, cr, uid, context=None):
        """
        Call method which can be inherited
        """
        return self.get_import_type_selection(cr, uid, context=context)

    _columns = {
        'launch_import_completion': fields.boolean(
            "Launch completion after import",
            help="Tic that box to automatically launch the completion "
                 "on each imported file using this profile."),
        'last_import_date': fields.datetime("Last Import Date"),
        #  we remove deprecated as it floods logs in standard/warning level sob...
        'rec_log': fields.text('log', readonly=True),  # Deprecated
        'import_type': fields.selection(
            _get_import_type_selection,
            'Type of import',
            required=True,
            help="Choose here the method by which you want to import bank"
                 "statement for this profile."),

    }

    def write_logs_after_import(self, cr, uid, ids, statement_id, num_lines, context):
        """
        Write the log in the logger

        :param int/long statement_id: ID of the concerned account.bank.statement
        :param int/long num_lines: Number of line that have been parsed
        :return: True
        """
        self.message_post(cr,
                          uid,
                          ids,
                          body=_('Statement ID %s have been imported with %s lines.') %
                                (statement_id, num_lines),
                          context=context)
        return True

    def prepare_global_commission_line_vals(
            self, cr, uid, parser, result_row_list, profile, statement_id, context):
        """
        Prepare the global commission line if there is one. The global
        commission is computed by by calling the get_st_line_commision
        of the parser. Feel free to override the method to compute
        your own commission line from the result_row_list.

            :param:    browse_record of the current parser
            :param:    result_row_list: [{'key':value}]
            :param:    profile: browserecord of account.statement.profile
            :param:    statement_id: int/long of the current importing statement ID
            :param:    context: global context
            return:    dict of vals that will be passed to create method of statement line.
        """
        comm_values = False
        if parser.get_st_line_commision():
            partner_id = profile.partner_id and profile.partner_id.id or False
            commission_account_id = profile.commission_account_id and profile.commission_account_id.id or False
            commission_analytic_id = profile.commission_analytic_id and profile.commission_analytic_id.id or False
            comm_values = {
                'name': 'IN ' + _('Commission line'),
                'date': parser.get_statement_date(),
                'amount': parser.get_st_line_commision(),
                'partner_id': partner_id,
                'type': 'general',
                'statement_id': statement_id,
                'account_id': commission_account_id,
                'ref': 'commission',
                'analytic_account_id': commission_analytic_id,
                # !! We set the already_completed so auto-completion will not update those values!
                'already_completed': True,
            }
        return comm_values

    def prepare_statement_lines_vals(
            self, cr, uid, parser_vals, account_payable, account_receivable,
            statement_id, context):
        """
        Hook to build the values of a line from the parser returned values. At
        least it fullfill the statement_id and account_id. Overide it to add your
        own completion if needed.

        :param dict of vals from parser for account.bank.statement.line (called by
                parser.get_st_line_vals)
        :param int/long account_payable: ID of the receivable account to use
        :param int/long account_receivable: ID of the payable account to use
        :param int/long statement_id: ID of the concerned account.bank.statement
        :return: dict of vals that will be passed to create method of statement line.
        """
        statement_obj = self.pool.get('account.bank.statement')
        values = parser_vals
        values['statement_id'] = statement_id
        date = values.get('date')
        period_memoizer = context.get('period_memoizer')
        if not period_memoizer:
            period_memoizer = {}
            context['period_memoizer'] = period_memoizer
        if period_memoizer.get(date):
            values['period_id'] = period_memoizer[date]
        else:
            # This is awfully slow...
            periods = self.pool.get('account.period').find(cr, uid,
                                                           dt=values.get('date'),
                                                           context=context)
            values['period_id'] = periods[0]
            period_memoizer[date] = periods[0]
        values['type'] = 'general'
        return values

    def prepare_tranfer_line_vals(self, cursor, uid, parser, result_row_list,
                                        profile, statement_id, context=None):
        if parser.get_transfer_amount():
            partner_id = profile.partner_id and profile.partner_id.id or False
            transfer_account_id = profile.internal_account_transfer_id.id or False
            statement_line_obj = self.pool.get('account.bank.statement.line')
            return {
                'name': _('Transfer'),
                'date': parser.get_statement_date(),
                'amount': parser.get_transfer_amount(),
                'partner_id': partner_id,
                'type': 'general',
                'statement_id': statement_id,
                'account_id': transfer_account_id,
                'ref': 'transfer',
                # !! We set the already_completed so auto-completion will not update those values !
                'already_completed': True,
            }



    def _add_special_line(self, cursor, uid, statement_id, parser, result_row_list, prof, context=None):
        statement_line_obj = self.pool.get('account.bank.statement.line')
        # Build and create the global commission line for the whole statement
        transfer_vals = self.prepare_tranfer_line_vals(cursor, uid, parser, result_row_list, prof, statement_id, context)
        if transfer_vals:
            statement_line_obj.create(cursor, uid, transfer_vals, context=context)


    def statement_import(self, cr, uid, ids, profile_id, file_stream, ftype="csv", context=None):
        """
        Create a bank statement with the given profile and parser. It will fullfill the bank statement
        with the values of the file providen, but will not complete data (like finding the partner, or
        the right account). This will be done in a second step with the completion rules.
        It will also create the commission line if it apply and record the providen file as
        an attachement of the bank statement.

        :param int/long profile_id: ID of the profile used to import the file
        :param filebuffer file_stream: binary of the providen file
        :param char: ftype represent the file exstension (csv by default)
        :return: ID of the created account.bank.statemênt
        """
        statement_obj = self.pool.get('account.bank.statement')
        statement_line_obj = self.pool.get('account.bank.statement.line')
        attachment_obj = self.pool.get('ir.attachment')
        prof_obj = self.pool.get("account.statement.profile")
        if not profile_id:
            raise osv.except_osv(_("No Profile!"),
                                 _("You must provide a valid profile to import a bank statement!"))
        prof = prof_obj.browse(cr, uid, profile_id, context=context)
        context['profile'] = prof
        parser = new_bank_statement_parser(prof.import_type, ftype=ftype)
        result_row_list = parser.parse(file_stream, context=context)
        # Check all key are present in account.bank.statement.line!!
        if not result_row_list:
            raise osv.except_osv(_("Nothing to import"),
                                 _("The file is empty"))
        parsed_cols = parser.get_st_line_vals(result_row_list[0], context=context).keys()
        for col in parsed_cols:
            if col not in statement_line_obj._columns:
                raise osv.except_osv(_("Missing column!"),
                                     _("Column %s you try to import is not "
                                       "present in the bank statement line!") % col)
        st_name = parser.get_statement_name()
        if st_name != '/':
            st_name = '%s%s'%(prof.bank_statement_prefix, st_name)
        st_vals = {
            'profile_id': prof.id,
            'name': st_name,
            'date': parser.get_statement_date(),
            'balance_start': parser.get_start_balance(),
            'balance_end_real': parser.get_end_balance(),
        }
 
        statement_id = statement_obj.create(cr, uid, st_vals, context=context)
        if prof.receivable_account_id:
            account_receivable = account_payable = prof.receivable_account_id.id
        else:
            account_receivable, account_payable = statement_obj.get_default_pay_receiv_accounts(
                                                       cr, uid, context)
        try:
            # Record every line in the bank statement and compute the global commission
            # based on the commission_amount column
            statement_store = []
            for line in result_row_list:
                parser_vals = parser.get_st_line_vals(line, context=context)
                values = self.prepare_statement_lines_vals(cr, uid, parser_vals, account_payable,
                                                             account_receivable, statement_id, context)
                statement_store.append(values)
            # Hack to bypass ORM poor perfomance. Sob...
            statement_line_obj._insert_lines(cr, uid, statement_store, context=context)


            self._add_special_line(cr, uid, statement_id, parser, result_row_list, prof, context=context)
            # Build and create the global commission line for the whole statement
            comm_vals = self.prepare_global_commission_line_vals(cr, uid, parser, result_row_list,
                                                                 prof, statement_id, context)
            if comm_vals:
                statement_line_obj.create(cr, uid, comm_vals, context=context)
            else:
                # Trigger store field computation if someone has better idea
                start_bal = statement_obj.read(cr, uid, statement_id,
                                               ['balance_start'],
                                               context=context)
                start_bal = start_bal['balance_start']
                statement_obj.write(cr, uid, [statement_id],
                                    {'balance_start': start_bal})

            attachment_obj.create(cr,
                                  uid,
                                  {'name': 'statement file',
                                   'datas': file_stream,
                                   'datas_fname': "%s.%s" % (
                                       datetime.datetime.now().date(),
                                       ftype),
                                   'res_model': 'account.bank.statement',
                                   'res_id': statement_id},
                                  context=context)

            # If user ask to launch completion at end of import, do it!
            if prof.launch_import_completion:
                statement_obj.button_auto_completion(cr, uid, [statement_id], context)

            # Write the needed log infos on profile
            self.write_logs_after_import(cr, uid, prof.id,
                                         statement_id,
                                         len(result_row_list),
                                         context)

        except Exception:
            #statement_obj.unlink(cr, uid, [statement_id], context=context)
            error_type, error_value, trbk = sys.exc_info()
            st = "Error: %s\nDescription: %s\nTraceback:" % (error_type.__name__, error_value)
            st += ''.join(traceback.format_tb(trbk, 30))
            if config['debug_mode']:
                raise
            raise osv.except_osv(_("Statement import error"),
                                 _("The statement cannot be created: %s") % st)
        return [statement_id]


class AccountStatementLine(Model):
    """
    Add sparse field on the statement line to allow to store all the
    bank infos that are given by an office. In this basic sample case
    it concern only commission_amount.
    """
    _inherit = "account.bank.statement.line"

    def _get_available_columns(self, statement_store):
        """Return writeable by SQL columns"""
        statement_line_obj = self.pool['account.bank.statement.line']
        model_cols = statement_line_obj._columns
        avail = [k for k, col in model_cols.iteritems() if not hasattr(col, '_fnct')]
        keys = [k for k in statement_store[0].keys() if k in avail]
        keys.sort()
        return keys

    def _insert_lines(self, cr, uid, statement_store, context=None):
        """ Do raw insert into database because ORM is awfully slow
            when doing batch write. It is a shame that batch function
            does not exist"""
        statement_line_obj = self.pool['account.bank.statement.line']
        statement_line_obj.check_access_rule(cr, uid, [], 'create')
        statement_line_obj.check_access_rights(cr, uid, 'create', raise_exception=True)
        cols = self._get_available_columns(statement_store)
        tmp_vals = (', '.join(cols), ', '.join(['%%(%s)s' % i for i in cols]))
        sql = "INSERT INTO account_bank_statement_line (%s) VALUES (%s);" % tmp_vals
        try:
            cr.executemany(sql, tuple(statement_store))
        except psycopg2.Error as sql_err:
            cr.rollback()
            raise osv.except_osv(_("ORM bypass error"),
                                 sql_err.pgerror)

    def _update_line(self, cr, uid, vals, context=None):
        """ Do raw update into database because ORM is awfully slow
            when cheking security."""
        cols = self._get_available_columns([vals])
        tmp_vals = (', '.join(['%s = %%(%s)s' % (i, i) for i in cols]))
        sql = "UPDATE account_bank_statement_line SET %s where id = %%(id)s;" % tmp_vals
        try:
            cr.execute(sql, vals)
        except psycopg2.Error as sql_err:
            cr.rollback()
            raise osv.except_osv(_("ORM bypass error"),
                                 sql_err.pgerror)

    _columns = {
        'commission_amount': fields.sparse(
            type='float',
            string='Line Commission Amount',
            serialization_field='additionnal_bank_fields'),
        'account_id': fields.many2one('account.account','Account'),
 
    }
