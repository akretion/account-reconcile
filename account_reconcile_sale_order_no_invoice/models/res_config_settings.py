# Copyright 2026 Akretion (https://www.akretion.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    account_reconcile_sale_order_mode = fields.Selection(
        related="company_id.account_reconcile_sale_order_mode",
        readonly=False,
    )
