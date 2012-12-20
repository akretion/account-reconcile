# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Nicolas Bessi, Joel Grand-Guillaume
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
from tools.translate import _
from openerp.osv.orm import Model, fields
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from operator import attrgetter
import datetime


class ErrorTooManyPartner(Exception):
    """
    New Exception definition that is raised when more than one partner is matched by
    the completion rule.
    """
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class AccountStatementProfil(Model):
    """
    Extend the class to add rules per profile that will match at least the partner,
    but it could also be used to match other values as well.
    """

    _inherit = "account.statement.profile"

    _columns = {
        # @Akretion : For now, we don't implement this features, but this would probably be there:
        # 'auto_completion': fields.text('Auto Completion'),
        # 'transferts_account_id':fields.many2one('account.account', 'Transferts Account'),
        # => You can implement it in a module easily, we design it with your needs in mind
        # as well !

        'rule_ids': fields.many2many(
            'account.statement.completion.rule',
            string='Related statement profiles',
            rel='as_rul_st_prof_rel'),
    }

    def find_values_from_rules(self, cr, uid, id, line_id, context=None):
        """
        This method will execute all related rules, in their sequence order,
        to retrieve all the values returned by the first rules that will match.

        :param int/long line_id: id of the concerned account.bank.statement.line
        :return:
            A dict of value that can be passed directly to the write method of
            the statement line or {}
           {'partner_id': value,
            'account_id' : value,

            ...}
        """
        if context is None:
            context = {}
        res = {}
        rule_obj = self.pool.get('account.statement.completion.rule')
        profile = self.browse(cr, uid, id, context=context)
        # We need to respect the sequence order
        sorted_array = sorted(profile.rule_ids, key=attrgetter('sequence'))
        for rule in sorted_array:
            method_to_call = getattr(rule_obj, rule.function_to_call)
            result = method_to_call(cr, uid, line_id, context)
            if result:
                return result
        return res


class AccountStatementCompletionRule(Model):
    """
    This will represent all the completion method that we can have to
    fullfill the bank statement lines. You'll be able to extend them in you own module
    and choose those to apply for every statement profile.
    The goal of a rule is to fullfill at least the partner of the line, but
    if possible also the reference because we'll use it in the reconciliation
    process. The reference should contain the invoice number or the SO number
    or any reference that will be matched by the invoice accounting move.
    """

    _name = "account.statement.completion.rule"
    _order = "sequence asc"

    def _get_functions(self, cr, uid, context=None):
        """
        List of available methods for rules. Override this to add you own.
        """
        return [
            ('get_from_ref_and_invoice', 'From line reference (based on invoice number)'),
            ('get_from_ref_and_so', 'From line reference (based on SO number)'),
            ('get_from_label_and_partner_field', 'From line label (based on partner field)'),
            ('get_from_label_and_partner_name', 'From line label (based on partner name)'),
            ]

    _columns = {
        'sequence': fields.integer('Sequence', help="Lower means parsed first."),
        'name': fields.char('Name', size=128),
        'profile_ids': fields.many2many(
            'account.statement.profile',
            rel='as_rul_st_prof_rel',
            string='Related statement profiles'),
        'function_to_call': fields.selection(_get_functions, 'Method'),
    }

    def get_from_ref_and_invoice(self, cr, uid, line_id, context=None):
        """
        Match the partner based on the invoice number and the reference of the statement
        line. Then, call the generic get_values_for_line method to complete other values.
        If more than one partner matched, raise the ErrorTooManyPartner error.

        :param int/long line_id: id of the concerned account.bank.statement.line
        :return:
            A dict of value that can be passed directly to the write method of
            the statement line or {}
           {'partner_id': value,
            'account_id' : value,

            ...}
        """
        st_obj = self.pool.get('account.bank.statement.line')
        st_line = st_obj.browse(cr, uid, line_id, context=context)
        res = {}
        if st_line:
            inv_obj = self.pool.get('account.invoice')
            inv_id = inv_obj.search(
                    cr,
                    uid,
                    [('number', '=', st_line.ref)],
                    context=context)
            if inv_id:
                if inv_id and len(inv_id) == 1:
                    inv = inv_obj.browse(cr, uid, inv_id[0], context=context)
                    res['partner_id'] = inv.partner_id.id
                elif inv_id and len(inv_id) > 1:
                    raise ErrorTooManyPartner(
                            _('Line named "%s" (Ref:%s) was matched by more '
                              'than one partner.') % (st_line.name, st_line.ref))
                st_vals = st_obj.get_values_for_line(
                        cr,
                        uid,
                        profile_id=st_line.statement_id.profile_id.id,
                        partner_id=res.get('partner_id', False),
                        line_type=st_line.type,
                        amount=st_line.amount,
                        context=context)
                res.update(st_vals)
        return res

    def get_from_ref_and_so(self, cr, uid, line_id, context=None):
        """
        Match the partner based on the SO number and the reference of the statement
        line. Then, call the generic get_values_for_line method to complete other values.
        If more than one partner matched, raise the ErrorTooManyPartner error.

        :param int/long line_id: id of the concerned account.bank.statement.line
        :return:
            A dict of value that can be passed directly to the write method of
            the statement line or {}
           {'partner_id': value,
            'account_id' : value,

            ...}
        """
        st_obj = self.pool.get('account.bank.statement.line')
        st_line = st_obj.browse(cr, uid, line_id, context=context)
        res = {}
        if st_line:
            so_obj = self.pool.get('sale.order')
            so_id = so_obj.search(
                    cr,
                    uid,
                    [('name', '=', st_line.ref)],
                    context=context)
            if so_id:
                if so_id and len(so_id) == 1:
                    so = so_obj.browse(cr, uid, so_id[0], context=context)
                    res['partner_id'] = so.partner_id.id
                elif so_id and len(so_id) > 1:
                    raise ErrorTooManyPartner(
                            _('Line named "%s" (Ref:%s) was matched by more '
                              'than one partner.') %
                            (st_line.name, st_line.ref))
                st_vals = st_obj.get_values_for_line(
                        cr,
                        uid,
                        profile_id=st_line.statement_id.profile_id.id,
                        partner_id=res.get('partner_id', False),
                        line_type=st_line.type,
                        amount=st_line.amount,
                        context=context)
                res.update(st_vals)
        return res

    def get_from_label_and_partner_field(self, cr, uid, line_id, context=None):
        """
        Match the partner based on the label field of the statement line
        and the text defined in the 'bank_statement_label' field of the partner.
        Remember that we can have values separated with ; Then, call the generic
        get_values_for_line method to complete other values.
        If more than one partner matched, raise the ErrorTooManyPartner error.

        :param int/long line_id: id of the concerned account.bank.statement.line
        :return:
            A dict of value that can be passed directly to the write method of
            the statement line or {}
           {'partner_id': value,
            'account_id' : value,

            ...}
            """
        partner_obj = self.pool.get('res.partner')
        st_obj = self.pool.get('account.bank.statement.line')
        st_line = st_obj.browse(cr, uid, line_id, context=context)
        res = {}
        compt = 0
        if st_line:
            ids = partner_obj.search(
                    cr,
                    uid,
                    [('bank_statement_label', '!=', False)],
                    context=context)
            for partner in partner_obj.browse(cr, uid, ids, context=context):
                for partner_label in partner.bank_statement_label.split(';'):
                    if partner_label in st_line.label:
                        compt += 1
                        res['partner_id'] = partner.id
                        if compt > 1:
                            raise ErrorTooManyPartner(
                                    _('Line named "%s" (Ref:%s) was matched by '
                                      'more than one partner.') %
                                    (st_line.name, st_line.ref))
            if res:
                st_vals = st_obj.get_values_for_line(
                        cr,
                        uid,
                        profile_id=st_line.statement_id.profile_id.id,
                        partner_id=res.get('partner_id', False),
                        line_type=st_line.type,
                        amount=st_line.amount,
                        context=context)
                res.update(st_vals)
        return res

    def get_from_label_and_partner_name(self, cr, uid, line_id, context=None):
        """
        Match the partner based on the label field of the statement line
        and the name of the partner.
        Then, call the generic get_values_for_line method to complete other values.
        If more than one partner matched, raise the ErrorTooManyPartner error.

        :param int/long line_id: id of the concerned account.bank.statement.line
        :return:
            A dict of value that can be passed directly to the write method of
            the statement line or {}
           {'partner_id': value,
            'account_id' : value,

            ...}
            """
        # This Method has not been tested yet !
        res = {}
        st_obj = self.pool.get('account.bank.statement.line')
        st_line = st_obj.browse(cr, uid, line_id, context=context)
        if st_line:
            sql = "SELECT id FROM res_partner WHERE name ~* %s"
            pattern = ".*%s.*" % st_line.label
            cr.execute(sql, (pattern,))
            result = cr.fetchall()
            if len(result) > 1:
                raise ErrorTooManyPartner(
                        _('Line named "%s" (Ref:%s) was matched by more '
                          'than one partner.') %
                        (st_line.name, st_line.ref))
            for id in result[0]:
                res['partner_id'] = id
            if res:
                st_vals = st_obj.get_values_for_line(
                        cr,
                        uid,
                        profile_id=st_line.statement_id.profile_id.id,
                        partner_id=res.get('partner_id', False),
                        line_type=st_line.type,
                        amount=st_line.amount,
                        context=context)
                res.update(st_vals)
        return res


class AccountStatementLine(Model):
    """
    Add sparse field on the statement line to allow to store all the
    bank infos that are given by a bank/office. You can then add you own in your
    module. The idea here is to store all bank/office infos in the additionnal_bank_fields
    serialized field when importing the file. If many values, add a tab in the bank
    statement line to store your specific one. Have a look in account_statement_base_import
    module to see how we've done it.
    """
    _inherit = "account.bank.statement.line"

    _columns = {
        'additionnal_bank_fields': fields.serialized(
            'Additionnal infos from bank',
            help="Used by completion and import system. Adds every field that "
                 "is present in your bank/office statement file"),
        'label': fields.sparse(
            type='char',
            string='Label',
            serialization_field='additionnal_bank_fields',
            help="Generic field to store a label given from the "
                 "bank/office on which we can base the default/standard "
                 "providen rule."),
        'already_completed': fields.boolean(
            "Auto-Completed",
            help="When this checkbox is ticked, the auto-completion "
                 "process/button will ignore this line."),
    }

    _defaults = {
        'already_completed': False,
    }

    def get_line_values_from_rules(self, cr, uid, ids, context=None):
        """
        We'll try to find out the values related to the line based on rules setted on
        the profile.. We will ignore line for which already_completed is ticked.

        :return:
            A dict of dict value that can be passed directly to the write method of
            the statement line or {}. The first dict has statement line ID as a key:
            {117009: {'partner_id': 100997, 'account_id': 489L}}
        """
        profile_obj = self.pool.get('account.statement.profile')
        st_obj = self.pool.get('account.bank.statement.line')
        res = {}
        errors_stack = []
        for line in self.browse(cr, uid, ids, context=context):
            if line.already_completed:
                continue
            try:
                # Take the default values
                res[line.id] = st_obj.get_values_for_line(
                        cr,
                        uid,
                        profile_id=line.statement_id.profile_id.id,
                        line_type=line.type,
                        amount=line.amount,
                        context=context)
                # Ask the rule
                vals = profile_obj.find_values_from_rules(
                        cr, uid, line.statement_id.profile_id.id, line.id, context)
                # Merge the result
                res[line.id].update(vals)
            except ErrorTooManyPartner, exc:
                msg = "Line ID %s had following error: %s" % (line.id, exc.value)
                errors_stack.append(msg)
        if errors_stack:
            msg = u"\n".join(errors_stack)
            raise ErrorTooManyPartner(msg)
        return res


class AccountBankSatement(Model):
    """
    We add a basic button and stuff to support the auto-completion
    of the bank statement once line have been imported or manually fullfill.
    """
    _inherit = "account.bank.statement"

    _columns = {
        'completion_logs': fields.text('Completion Log', readonly=True),
    }

    def write_completion_log(self, cr, uid, stat_id, error_msg, number_imported, context=None):
        """
        Write the log in the completion_logs field of the bank statement to let the user
        know what have been done. This is an append mode, so we don't overwrite what
        already recoded.

        :param int/long stat_id: ID of the account.bank.statement
        :param char error_msg: Message to add
        :number_imported int/long: Number of lines that have been completed
        :return : True
        """
        error_log = ""
        user_name = self.pool.get('res.users').read(
                cr, uid, uid, ['name'], context=context)['name']
        log = self.read(
                cr, uid, stat_id, ['completion_logs'], context=context)['completion_logs']
        log_line = log and log.split("\n") or []
        completion_date = datetime.datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        if error_msg:
            error_log = error_msg
        log_line[0:0] = [completion_date + ' : '
            + _("Bank Statement ID %s has %s lines completed by %s") % (stat_id, number_imported, user_name)
            + "\n" + error_log + "-------------" + "\n"]
        log = "\n".join(log_line)
        self.write(cr, uid, [stat_id], {'completion_logs': log}, context=context)
        self.message_post(
                cr, uid,
                [stat_id],
                body=_('Statement ID %s auto-completed for %s lines completed') % (stat_id, number_imported),
                context=context)
        return True

    def button_auto_completion(self, cr, uid, ids, context=None):
        """
        Complete line with values given by rules and tic the already_completed
        checkbox so we won't compute them again unless the user untick them !
        """
        if context is None:
            context = {}
        stat_line_obj = self.pool.get('account.bank.statement.line')
        msg = ""
        compl_lines = 0
        for stat in self.browse(cr, uid, ids, context=context):
            ctx = context.copy()
            for line in stat.line_ids:
                res = {}
                try:
                    res = stat_line_obj.get_line_values_from_rules(
                            cr, uid, [line.id], context=ctx)
                    if res:
                        compl_lines += 1
                except ErrorTooManyPartner, exc:
                    msg += exc.value + "\n"
                except Exception, exc:
                    msg += exc.value + "\n"
                # vals = res and res.keys() or False
                if res:
                    vals = res[line.id]
                    vals['already_completed'] = True
                    stat_line_obj.write(cr, uid, [line.id], vals, context=ctx)
            self.write_completion_log(
                    cr, uid, stat.id, msg, compl_lines, context=context)
        return True
