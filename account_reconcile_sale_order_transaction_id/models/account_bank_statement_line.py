# Copyright 2026 Akretion (https://www.akretion.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import models


class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    def _get_reconcile_line_for_sale_order(
        self, sale_order, kind, reconcile_auxiliary_id
    ):
        res = super()._get_reconcile_line_for_sale_order(
            sale_order, kind, reconcile_auxiliary_id
        )
        if sale_order.transaction_id:
            res["transaction_id"] = sale_order.transaction_id
            # we want to keep the amount of transaction, if transaction ref is here
            # it should not concerns multiple orders.
            if (
                self.company_id.account_reconcile_sale_order_mode == "payment"
                and sale_order.transaction_id in self.payment_ref
                and self.amount != sale_order.amount_total
            ):
                res["amount"] = -self.amount
                res["credit"] = self.amount
        return res

    def _reconcile_move_line_vals(self, line, move_id=False):
        vals = super()._reconcile_move_line_vals(line, move_id=move_id)
        if line.get("transaction_id"):
            vals["transaction_id"] = line["transaction_id"]
        return vals
