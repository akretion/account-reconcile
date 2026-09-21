# Copyright 2026 Akretion (https://www.akretion.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import Command, models
from odoo.tools import format_amount


class AccountMove(models.Model):
    _inherit = "account.move"

    def _post(self, soft=True):
        posted_moves = super()._post(soft=soft)
        posted_moves._reconcile_sale_order_payments()
        return posted_moves

    def _reconcile_sale_order_payments(self):
        """Reconcile the receivable of the invoices with the payments that
        have been registered on the sale orders they are invoiced from."""
        for invoice in self.filtered(
            lambda move: move.state == "posted" and move.move_type == "out_invoice"
        ):
            orders = invoice.invoice_line_ids.sale_line_ids.order_id.filtered(
                "payment_line_ids"
            )
            for order in orders:
                invoice._reconcile_with_sale_order_payments(order)

    def _get_sale_order_payment_residuals(self, lines):
        """Return the residual of the given journal items as a tuple with:

        * the residual expressed in the company currency,
        * the residual expressed in the currency of the invoice when all the
          items share it, ``None`` otherwise. This second value is the one used
          by the reconciliation to match the items together, the first one
          being used to build the write-off entry.
        """
        self.ensure_one()
        balance_difference = self.company_currency_id.round(
            sum(lines.mapped("amount_residual"))
        )
        if all(line.currency_id == self.currency_id for line in lines):
            currency_difference = self.currency_id.round(
                sum(lines.mapped("amount_residual_currency"))
            )
        else:
            currency_difference = None
        return balance_difference, currency_difference

    def _reconcile_with_sale_order_payments(self, order):
        """Reconcile the receivable lines of this invoice with the payment
        lines of the given sale order.

        The reconciliation is possible only when both amounts match, small
        differences being written off (see
        ``_create_sale_order_payment_writeoff``). When the difference is too
        large, nothing is reconciled and a message is posted on the invoice so
        that the difference can be handled manually.

        :return: True when a reconciliation has been made
        """
        self.ensure_one()
        receivable_lines = self.line_ids.filtered(
            lambda line: line.account_id.account_type == "asset_receivable"
            and not line.reconciled
        )
        payment_lines = order.payment_line_ids.filtered(
            lambda line: line.parent_state == "posted"
            and not line.reconciled
            and line.account_id in receivable_lines.account_id
        )
        if not receivable_lines or not payment_lines:
            return False
        lines = receivable_lines + payment_lines
        balance_diff, currency_diff = self._get_sale_order_payment_residuals(lines)
        if currency_diff is None:
            difference, difference_currency = balance_diff, self.company_currency_id
        else:
            difference, difference_currency = currency_diff, self.currency_id
        writeoff_lines = self.env["account.move.line"]
        if not difference_currency.is_zero(difference):
            writeoff_lines = self._create_sale_order_payment_writeoff(
                order, lines, difference, balance_diff, currency_diff
            )
            if not writeoff_lines:
                self._notify_sale_order_payment_difference(
                    order, difference, difference_currency
                )
                return False
        (lines + writeoff_lines).reconcile()
        return True

    def _create_sale_order_payment_writeoff(
        self, order, lines, difference, balance_difference, currency_difference
    ):
        """Write off the difference remaining between the payments of a sale
        order and the receivable of this invoice.

        Nothing is done when the difference is not allowed to be written off
        (no write-off account configured on the company, amount above the
        maximum configured amount, journal items in different accounts or
        currencies).

        :return: the journal items of the write-off entry booked on the
            receivable account, so that they can be reconciled with the
            invoice.
        """
        self.ensure_one()
        company = self.company_id
        account = company.sale_order_payment_writeoff_account_id
        receivable_account = lines[:1].account_id
        if (
            not account
            or currency_difference is None
            or len(lines.account_id) != 1
            or not self._is_sale_order_payment_writeoff_allowed(difference)
        ):
            return self.env["account.move.line"]
        journal = self.env["account.journal"].search(
            [("type", "=", "general"), ("company_id", "=", company.id)], limit=1
        )
        if not journal:
            return self.env["account.move.line"]
        label = self.env._("Write-off on %(order)s", order=order.name)
        writeoff_move = self.env["account.move"].create(
            {
                "move_type": "entry",
                "journal_id": journal.id,
                "date": self.date,
                "ref": self.env._(
                    "Payment write-off on %(invoice)s (%(order)s)",
                    invoice=self.name,
                    order=order.name,
                ),
                "line_ids": [
                    Command.create(
                        self._prepare_sale_order_payment_writeoff_line_vals(
                            receivable_account,
                            -balance_difference,
                            -currency_difference,
                            self.currency_id,
                            label,
                        )
                    ),
                    Command.create(
                        self._prepare_sale_order_payment_writeoff_line_vals(
                            account,
                            balance_difference,
                            currency_difference,
                            self.currency_id,
                            label,
                        )
                    ),
                ],
            }
        )
        writeoff_move.action_post()
        return writeoff_move.line_ids.filtered(
            lambda line: line.account_id == receivable_account
        )

    def _is_sale_order_payment_writeoff_allowed(self, difference):
        """Tell whether a difference can be written off automatically."""
        self.ensure_one()
        company = self.company_id
        currency = self.currency_id
        max_amount = company.currency_id._convert(
            company.sale_order_payment_writeoff_max_amount,
            currency,
            company,
            self.date,
        )
        return currency.compare_amounts(abs(difference), max_amount) <= 0

    def _prepare_sale_order_payment_writeoff_line_vals(
        self, account, amount, amount_currency, currency, label
    ):
        """Prepare the values of a journal item of the write-off entry.

        :param amount: the amount expressed in the company currency
        :param amount_currency: the same amount expressed in the currency of
            the invoice (both are equal when the invoice is in the company
            currency)
        """
        self.ensure_one()
        return {
            "name": label,
            "account_id": account.id,
            "partner_id": self.commercial_partner_id.id,
            "currency_id": currency.id,
            "amount_currency": amount_currency,
            "debit": amount if amount > 0.0 else 0.0,
            "credit": -amount if amount < 0.0 else 0.0,
        }

    def _notify_sale_order_payment_difference(self, order, difference, currency):
        """Tell the users the payments of the sale order couldn't be
        reconciled automatically with this invoice."""
        self.ensure_one()
        self.message_post(
            body=self.env._(
                "The payments registered on the sale order %(order)s couldn't "
                "be reconciled automatically with this invoice: the difference "
                "between the invoice and the payments is %(difference)s. "
                "Please reconcile this invoice manually.",
                order=order.name,
                difference=format_amount(self.env, difference, currency),
            )
        )
