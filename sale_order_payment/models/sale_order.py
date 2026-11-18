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
        store=True,
    )
    paid_amount = fields.Monetary(
        compute="_compute_payment_info",
        currency_field="currency_id",
        store=True,
        tracking=True,
        help="Total amount of the payment journal items linked to this sale "
        "order (posted or draft entries, cancelled entries excluded).",
    )
    amount_due = fields.Monetary(
        compute="_compute_payment_info",
        currency_field="currency_id",
        store=True,
        help="Remaining amount to pay on this sale order.",
    )
    is_paid = fields.Boolean(
        string="Paid",
        compute="_compute_payment_info",
        store=True,
        help="True when the paid amount covers the total amount of the sale order.",
    )
    has_unallocated_payment = fields.Boolean(
        string="Unallocated Payment",
        compute="_compute_payment_info",
        store=True,
        help="True when a customer payment of the sale order is not reconciled "
        "with an invoice of the order.",
    )
    has_unallocated_refund = fields.Boolean(
        string="Unallocated Refund",
        compute="_compute_payment_info",
        store=True,
        help="True when a refund of the sale order is not reconciled with a "
        "credit note of the order.",
    )

    @api.depends(
        "amount_total",
        "payment_line_ids.debit",
        "payment_line_ids.credit",
        "payment_line_ids.balance",
        "payment_line_ids.reconciled",
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
            # A customer payment is booked as a credit on the receivable account
            # and a refund as a debit: a line is allocated once reconciled with
            # an invoice (payment) or with a credit note (refund).
            company_rounding = order.company_id.currency_id.rounding
            unreconciled_lines = lines.filtered(lambda line: not line.reconciled)
            order.has_unallocated_payment = any(
                float_compare(line.balance, 0.0, precision_rounding=company_rounding)
                < 0
                for line in unreconciled_lines
            )
            order.has_unallocated_refund = any(
                float_compare(line.balance, 0.0, precision_rounding=company_rounding)
                > 0
                for line in unreconciled_lines
            )
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

    def _payment_matches_invoiced_amount(self):
        """Return True when the posted payments of the order match the amount
        invoiced for this order.

        Both amounts are compared in the company currency: the invoices are
        taken with their signed total and the payment journal items with their
        balance.
        """
        self.ensure_one()
        invoiced_amount = sum(
            self.invoice_ids.filtered(lambda move: move.state == "posted").mapped(
                "amount_total_signed"
            )
        )
        payment_lines = self.payment_line_ids.filtered(
            lambda line: line.parent_state == "posted"
        )
        paid_amount = sum(payment_lines.mapped("credit")) - sum(
            payment_lines.mapped("debit")
        )
        return (
            float_compare(
                paid_amount,
                invoiced_amount,
                precision_rounding=self.company_id.currency_id.rounding,
            )
            == 0
        )

    def action_view_payment_lines(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "account.action_account_moves_all"
        )
        action.update({"domain": [("sale_order_id", "=", self.id)]})
        return action
