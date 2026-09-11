# Copyright 2026 Akretion (https://www.akretion.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models
from odoo.tools import float_compare


class SaleOrder(models.Model):
    _inherit = "sale.order"

    payment_line_ids = fields.One2many(
        "account.move.line",
        "sale_order_id",
        string="Payment Journal Items",
        help="Journal items of the payment entries linked to this sale order. "
        "Typically the receivable counterpart items created when the customer "
        "payment is reconciled against the order.",
    )
    payment_line_count = fields.Integer(
        string="Payment Entries",
        compute="_compute_payment_info",
    )
    paid_amount = fields.Monetary(
        compute="_compute_payment_info",
        currency_field="currency_id",
        help="Total amount of the payment journal items linked to this sale "
        "order (posted or draft entries, cancelled entries excluded).",
    )
    amount_due = fields.Monetary(
        compute="_compute_payment_info",
        currency_field="currency_id",
        help="Remaining amount to pay on this sale order.",
    )
    is_paid = fields.Boolean(
        string="Paid",
        compute="_compute_payment_info",
        help="True when the paid amount covers the total amount of the sale order.",
    )

    @api.depends(
        "amount_total",
        "payment_line_ids.debit",
        "payment_line_ids.credit",
        "payment_line_ids.move_id.state",
    )
    def _compute_payment_info(self):
        for order in self:
            lines = order.payment_line_ids.filtered(
                lambda line: line.move_id.state != "cancel"
            )
            # A received payment is booked as a credit on the receivable
            # account, so the paid amount is the credit part of the linked
            # journal items.
            paid_amount = sum(lines.mapped("credit")) - sum(lines.mapped("debit"))
            order.payment_line_count = len(lines)
            order.paid_amount = paid_amount
            rounding = order.currency_id.rounding
            if (
                float_compare(
                    paid_amount, order.amount_total, precision_rounding=rounding
                )
                >= 0
            ):
                order.is_paid = True
                order.amount_due = 0.0
            else:
                order.is_paid = False
                order.amount_due = order.currency_id.round(
                    order.amount_total - paid_amount
                )

    def action_view_payment_lines(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "account.action_move_journal_line"
        )
        action.update({"domain": [("sale_order_id", "=", self.id)]})
        return action
