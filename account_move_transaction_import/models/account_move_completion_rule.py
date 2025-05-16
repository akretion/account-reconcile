# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)
from odoo import fields, models


class AccountMoveCompletionRule(models.Model):
    _inherit = "account.move.completion.rule"

    function_to_call = fields.Selection(
        selection_add=[
            (
                "get_from_name_and_payment_transaction",
                "From line name (based on payment transaction name)",
            ),
        ]
    )

    def get_from_name_and_payment_transaction(self, line):
        """Match the partner based on the Transaction number and the name
        the accounting entry.
        """
        res = {}
        if not line.name:
            return res
        transaction = self.env["payment.transaction"].search(
            [("reference", "=", line.name)]
        )
        # transaction reference has a unique constraint, we should never get more than 1
        # transaction here.
        if transaction.partner_id:
            return {
                "partner_id": transaction.partner_id.commercial_partner_id.id,
                "transaction_id": transaction.id,
            }
        return res
