# Copyright 2026 Akretion (https://www.akretion.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    sale_order_payment_writeoff_account_id = fields.Many2one(
        related="company_id.sale_order_payment_writeoff_account_id",
        readonly=False,
        domain="[('account_type', 'not in', ('asset_receivable', 'liability_payable')),"
        "('deprecated', '=', False)]",
    )
    sale_order_payment_writeoff_max_amount = fields.Monetary(
        related="company_id.sale_order_payment_writeoff_max_amount",
        readonly=False,
        currency_field="currency_id",
    )
