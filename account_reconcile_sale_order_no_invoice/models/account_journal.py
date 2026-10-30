# Copyright 2026 Akretion (https://www.akretion.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    notify_sale_order_paid = fields.Boolean(
        string="Notify Paid Sale Orders",
        default=True,
        help="If enabled, an e-mail is sent (with the mail template 'Sale Order "
        "Paid: Notify the Salesperson') when a sale order is marked as paid by "
        "the bank reconciliation of a transaction of this journal. Disable it "
        "for the journals fed by an automated import which reconciles the "
        "transactions automatically (for example a PayPal import).",
    )
