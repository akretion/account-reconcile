# Copyright 2026 Akretion (https://www.akretion.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    sale_order_payment_writeoff_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Sale Order Payment Write-off Account",
        domain="[('account_type', 'not in', ('asset_receivable', 'liability_payable')),"
        "('deprecated', '=', False)]",
        help="Account used to write off the difference that may remain between "
        "the payments registered on a sale order and the receivable of the "
        "invoices generated from this order.\n"
        "Leave it empty to disable the automatic write-off: the invoice is "
        "then left open so that it can be reconciled manually.",
    )
    sale_order_payment_writeoff_max_amount = fields.Monetary(
        string="Max Sale Order Payment Write-off Amount",
        currency_field="currency_id",
        default=0.05,
        help="Maximum difference, in the company currency, that can be written "
        "off automatically when reconciling the payments of a sale order with "
        "the invoice generated from this order. Above this amount, the "
        "reconciliation is left to the accountant.",
    )
