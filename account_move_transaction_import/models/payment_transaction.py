# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)
from odoo import fields, models


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    payment_aml_ids = fields.One2many("account.move.line", "transaction_id")

    def _create_payment(self, add_payment_vals=None):
        if self.acquirer_id.payment_creation_mode == "statement_import":
            return
        return super()._create_payment(add_payment_vals=add_payment_vals)
