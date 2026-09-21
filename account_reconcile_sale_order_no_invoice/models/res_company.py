# Copyright 2026 Akretion (https://www.akretion.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    # Behaviour switch between the two modes supported by this module:
    #  * "invoice": original OCA account_reconcile_sale_order behaviour: at
    #    reconciliation the sale order is fully invoiced (requires an
    #    "invoice on ordered quantities" policy to make sense) and the created
    #    invoice is reconciled with the payment.
    #  * "payment": no invoice is created. The receivable counterpart journal
    #    item of the payment entry is created and left open (it will be
    #    reconciled against the invoice later on, when the order is invoiced),
    #    linked to the sale order which is flagged as paid.
    # Default is "invoice" to keep the exact OCA behaviour when the module is
    # installed; set it to "payment" on companies which don't invoice sale
    # orders at reconciliation time.
    account_reconcile_sale_order_mode = fields.Selection(
        selection=[
            ("payment", "Register the payment on the sale order"),
            ("invoice", "Invoice the sale order at reconciliation"),
        ],
        string="Reconcile sale orders",
        default="invoice",
        required=True,
        help="Behaviour when a bank statement line is reconciled against a "
        'sale order (selected manually in the "Sales orders" tab or matched '
        "automatically by a sale_order_matching rule).\n"
        "- Register the payment on the sale order: no invoice is created, a "
        "receivable counterpart journal item labelled with the sale order "
        "name is created and linked to the order, which is marked as paid.\n"
        "- Invoice the sale order at reconciliation: the sale order is "
        "invoiced and the created invoice is reconciled with the payment "
        "(OCA account_reconcile_sale_order behaviour).",
    )
