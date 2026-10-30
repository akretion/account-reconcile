# Copyright 2026 Akretion (https://www.akretion.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import models


class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    def _get_reconcile_sale_order_mode(self):
        """Sale order reconciliation mode of this statement line's company."""
        self.ensure_one()
        return self.company_id.account_reconcile_sale_order_mode

    def _prepare_reconcile_line_data_sale_order_invoice(self, order):
        """In "payment" mode, don't create an invoice for the sale order."""
        if self._get_reconcile_sale_order_mode() == "payment":
            self._send_sale_order_paid_mail(order)
            return self.env["account.move.line"]
        return super()._prepare_reconcile_line_data_sale_order_invoice(order)

    def _send_sale_order_paid_mail(self, order):
        """Notify by email that the sale order is paid.

        The email is sent when the sale order is marked as paid while
        reconciling a bank statement line ("payment" mode): the salesperson
        has to know that the order is paid to invoice it, the payment being
        reconciled with the invoice later on.

        The recipients are configured on the mail template, the email being
        queued: it is sent by the 'Mail: Email Queue Manager' scheduled action.
        The journal of the bank transaction can disable the notification, for
        example when it is fed by an automated import which reconciles the
        transactions automatically.
        """
        self.ensure_one()
        if not self.journal_id.notify_sale_order_paid:
            return False
        if order.is_paid:
            # The salesperson has already been notified: the order was paid by
            # a previous reconciliation.
            return False
        # The payment reference of the statement line is "/" when the line has
        # been created manually: use its label instead.
        reference = self.payment_ref
        if not reference or reference == "/":
            reference = self.name
        # The statement line and its reference are given to the template to
        # describe which bank transaction paid the sale order.
        self.env.ref(
            "account_reconcile_sale_order_no_invoice.sale_order_paid_mail_template"
        ).with_context(
            sale_order_paid_statement_line=self,
            sale_order_paid_reference=reference,
        ).send_mail(order.id)
        return True

    def _reconcile_move_line_vals(self, line, move_id=False):
        vals = super()._reconcile_move_line_vals(line, move_id=move_id)
        # Propagate the sale order link on the journal item created for a
        # reconcile data line coming from a sale order.
        if line.get("sale_order_id"):
            vals["sale_order_id"] = line["sale_order_id"]
            # Make sure the journal item is labelled with the sale order name:
            # this label is what makes the open receivable item easy to find
            # and reconcile with the invoice when the order is invoiced later.
            sale_order = self.env["sale.order"].browse(line["sale_order_id"])
            if not line.get("name"):
                vals["name"] = sale_order.name
        return vals

    def _get_reconcile_line_for_sale_order(
        self, sale_order, kind, reconcile_auxiliary_id
    ):
        res = super()._get_reconcile_line_for_sale_order(
            sale_order, kind, reconcile_auxiliary_id
        )
        # in case of refund, we just want to attach the amount on the sale order...
        if self._get_reconcile_sale_order_mode() == "payment" and self.amount < 0.0:
            res["amount"] = -self.amount
            res["credit"] = 0.0
            res["debit"] = -self.amount
            res["currency_amount"] = -self.amount
        return res
