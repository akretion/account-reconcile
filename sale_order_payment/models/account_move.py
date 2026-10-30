# Copyright 2026 Akretion (https://www.akretion.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    journal_type = fields.Selection(related="journal_id.type")

    def _post(self, soft=True):
        posted_moves = super()._post(soft=soft)
        posted_moves._reconcile_sale_order_payments()
        return posted_moves

    def _reconcile_sale_order_payments(self):
        """Reconcile the receivable of the invoices with the payments that
        have been registered on the sale orders they are invoiced from."""
        for invoice in self.filtered(
            lambda move: move.state == "posted" and move.move_type == "out_invoice"
        ):
            orders = invoice.invoice_line_ids.sale_line_ids.order_id.filtered(
                "payment_line_ids"
            )
            for order in orders:
                invoice._reconcile_with_sale_order_payments(order)

    def _reconcile_with_sale_order_payments(self, order):
        """Reconcile the receivable lines of this invoice with the payment
        lines of the given sale order.

        The reconciliation is partial when the amounts don't match, which is
        the case when the invoice covers only a part of the sale order: the
        remaining amount of the payment stays available to be reconciled with
        the next invoice of the order.

        :return: True when a reconciliation has been made
        """
        self.ensure_one()
        receivable_lines = self.line_ids.filtered(
            lambda line: line.account_id.account_type == "asset_receivable"
            and not line.reconciled
        )
        payment_lines = order.payment_line_ids.filtered(
            lambda line: line.parent_state == "posted"
            and not line.reconciled
            and line.account_id in receivable_lines.account_id
        )
        if not receivable_lines or not payment_lines:
            return False
        (receivable_lines + payment_lines).reconcile()
        return True
