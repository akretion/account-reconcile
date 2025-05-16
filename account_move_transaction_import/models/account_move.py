# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)
from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _reconcile_with_transactions(self):
        # This method could have multiple invoice in self, but only if it comes from
        # a same transaction
        to_reconcile = self.filtered(
            lambda rec: rec.transaction_ids
            and rec.amount_residual != 0.0
            and rec.state == "posted"
        )
        payment_lines = to_reconcile.transaction_ids.payment_aml_ids.filtered(
            lambda rec: not rec.reconciled and rec.move_id.state == "posted"
        )
        if not to_reconcile or not payment_lines:
            return
        account = payment_lines.account_id
        # should not be possible, do not raise because if the problem exists at this
        # stage, it is probably from before this call.
        if len(account) > 1:
            return
        to_reconcile_inv_line = to_reconcile.line_ids.filtered(
            lambda rec: not rec.reconciled and rec.account_id == account
        )
        (to_reconcile_inv_line | payment_lines).reconcile()

    def _post(self, soft=True):
        res = super()._post()
        # On invoice post, try to reconcile it with linked transaction having a posted
        # payment line
        invoices = self.filtered(
            lambda rec: rec.move_type
            in ("out_invoice", "out_refund", "in_invoice", "in_refund")
        )
        for invoice in invoices:
            invoice._reconcile_with_transactions()
        # On Statement credit card post, try to reconcile payment linked to transaction
        # with existing invoice
        for transaction in self.line_ids.transaction_id:
            transaction.invoice_ids._reconcile_with_transactions()
        return res
