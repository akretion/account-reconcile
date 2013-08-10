# -*- coding: utf-8 -*-
##############################################################################
#
#    account_statement_sale_order for OpenERP
#    Copyright (C) 2013 Akretion Chafique DELLI <chafique.delli@akretion.com>
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
from openerp.osv import osv, orm, fields



class AccountStatementLine(orm.Model):
    _inherit = "account.bank.statement.line"

    _columns = {
        'sale_ids': fields.many2many('sale.order', string='Sale Orders',)

    }

    def _update_line(self, cr, uid, vals, context=None):
        if 'sale_ids' in vals:
            line_id = vals.pop('id')
            self.write(cr, uid, line_id, vals, context=context)
        else:
            super(AccountStatementLine, self)._update_line(cr, uid, vals, context=context)


    def onchange_sale_ids(self, cr, uid, ids, sale_ids, profile_id=None, context=None):
        """
        Override of the basic method as we need to pass the profile_id in the on_change_type
        call.
        Moreover, we now call the get_account_and_type_for_counterpart method now to get the
        type to use.
        """
        warning_msg = False
        sale_obj = self.pool.get('sale.order')
        if not sale_ids:
            return {}
        if sale_ids:
            if len(sale_ids[0][2]) > 1:
                partner = False
                for sale in sale_obj.browse(cr, uid, sale_ids[0][2], context=context):
                    if partner:
                        if sale.partner_id != partner:
                            warning_msg = {
                                'title': _('Error !'),
                                'message': _('The sale orders chosen have to belong to the same partner'),
                            }
                    else:
                        partner = sale.partner_id
            sale = sale_obj.browse(cr, uid, sale_ids[0][2:3][0], context=context)
            partner_id = sale[0].partner_id.id
            account_id = sale[0].partner_id.property_account_receivable.id
            already_completed = True
        return {'value': {'partner_id': partner_id,
                          'account_id': account_id,
                          'already_completed': already_completed,},
                'warning':warning_msg}

    def _check_partner_id(self, cr, uid, ids, context=None):
        for line in self.browse(cr, uid, ids, context=context):
            for sale_id in line.sale_ids:
                if sale_id.partner_id != line.sale_ids[0].partner_id:
                    raise osv.except_osv (_('Error on the line %s !') % line.id ,
                                    _('The sale orders chosen have to belong to the same partner'))
        return True

    _constraints = [
        (_check_partner_id,
         'The sale orders chosen have to belong to the same partner',
         ['sale_ids']),
    ]

class AccountStatementCompletionRule(orm.Model):
    """
    This will represent all the completion method that we can have to
    fullfill the bank statement lines. You'll be able to extend them in you own module
    and choose those to apply for every statement profile.
    The goal of a rule is to fullfill at least the partner of the line, but
    if possible also the reference because we'll use it in the reconciliation
    process. The reference should contain the invoice number or the SO number
    or any reference that will be matched by the invoice accounting move.
    """

    _inherit = "account.statement.completion.rule"

    #Sorry for the copy paste but there is no way to inherit correctly
    #account_statement_base_completion need some refactor
    def get_from_ref_and_so(self, cr, uid, st_line, context=None):
        """
        Match the partner based on the SO number and the reference of the statement
        line. Then, call the generic get_values_for_line method to complete other values.
        If more than one partner matched, raise the ErrorTooManyPartner error.

        :param int/long st_line: read of the concerned account.bank.statement.line
        :return:
            A dict of value that can be passed directly to the write method of
            the statement line or {}
           {'partner_id': value,
            'account_id': value,

            ...}
        """
        st_obj = self.pool.get('account.bank.statement.line')
        res = {}
        if st_line:
            so_obj = self.pool.get('sale.order')
            so_id = so_obj.search(cr,
                                  uid,
                                  [('name', '=', st_line['ref'])],
                                  context=context)
            if so_id:
                if so_id and len(so_id) == 1:
                    so = so_obj.browse(cr, uid, so_id[0], context=context)
                    res['partner_id'] = so.partner_id.id
                    res['sale_ids'] = [(6, 0, [so.id])] #chg
                elif so_id and len(so_id) > 1:
                    raise ErrorTooManyPartner(_('Line named "%s" (Ref:%s) was matched by more '
                                                'than one partner while looking on SO by ref.') %
                                              (st_line['name'], st_line['ref']))
                st_vals = st_obj.get_values_for_line(cr,
                                                     uid,
                                                     profile_id=st_line['profile_id'],
                                                     master_account_id=st_line['master_account_id'],
                                                     partner_id=res.get('partner_id', False),
                                                     line_type='customer',
                                                     amount=st_line['amount'] if st_line['amount'] else 0.0,
                                                     context=context)
                res.update(st_vals)
        return res






class account_bank_statement(orm.Model):
    _inherit = "account.bank.statement"

    def _prepare_counterpart_move_line(self, *args, **kwargs):
        context = kwargs.get('context')
        if context is None:
            ctx = {}
        else:
            ctx = context.copy()
        ctx['countrepart'] = True
        kwargs['context'] = ctx
        return super(account_bank_statement, self)._prepare_counterpart_move_line(*args, **kwargs)       


    def _prepare_move_line_vals(self, cr, uid, st_line, *args, **kwargs):
        res = super(account_bank_statement, self)._prepare_move_line_vals(cr, uid, st_line, *args, **kwargs)
        if not kwargs.get('context', {}).get('countrepart'):
            res['sale_ids'] = [(6, 0, [sale.id for sale in st_line.sale_ids])]
        return res


