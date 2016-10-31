# -*- coding: utf-8 -*-
# © 2016 Akretion
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)
from openerp import _, models
from openerp.addons.account_move_base_import.models.account_move \
    import ErrorTooManyPartner


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _update_line(self, vals):
        if 'sale_ids' in vals:
            line_id = vals.pop('id')
            self.browse(line_id).write(vals)
        else:
            super(AccountMoveLine, self)._update_line(vals)


class AccountMoveCompletionRule(models.Model):
    _name = "account.move.completion.rule"
    _inherit = "account.move.completion.rule"


    def get_from_name_and_so(self, line):
        """
        Match the partner based on the SO number and the reference of the
        move line. Then, call the generic get_values_for_line method to
        complete other values. If more than one partner matched, raise the
        ErrorTooManyPartner error. Also link the SO found to the move line.

        :param int/long st_line: read of the concerned
        account.bank.statement.line

        :return:
            A dict of value that can be passed directly to the write method of
            the move line or {}
           {'partner_id': value,
            'account_id': value,

            ...}
        """
        res = super(AccountMoveCompletionRule, self).get_from_name_and_so(
            line)
        so_obj = self.env['sale.order']
        orders = so_obj.search([('name', '=', line.name)])
        if len(orders) > 1:
            raise ErrorTooManyPartner(
                _('Line named "%s"  was matched by more '
                  'than one partner while looking on SO by ref.') %
                line.name)
        if len(orders) == 1:
            res['sale_ids'] = [(6, 0, [orders.id])]
        return res
