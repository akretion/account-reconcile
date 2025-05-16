# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)
from odoo import fields, models


class PaymentAcquirer(models.Model):
    _inherit = "payment.acquirer"

    payment_creation_mode = fields.Selection(
        [
            ("statement_import", "Statement Import"),
            ("transaction_done", "Transaction Done"),
        ],
        default="transaction_done",
        help="Set how the payment related to this acquirer are created in Odoo :\n"
        "Transacton Done : it is the default mode, a payment will be generated when the"
        "state of the transaction is done \n"
        "Statement Import: no payment will be automatically generated during the "
        "transaction workflow. Odoo expects the payment to be imported with "
        "the credit card statement of the acquirer.",
    )
