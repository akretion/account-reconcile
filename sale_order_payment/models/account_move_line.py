# Copyright 2026 Akretion (https://www.akretion.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    sale_order_id = fields.Many2one(
        "sale.order",
        string="Sale Order",
        index=True,
        ondelete="restrict",
        domain="[('company_id', '=', company_id)]",
    )
