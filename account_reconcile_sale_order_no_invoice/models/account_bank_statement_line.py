# Copyright 2026 Akretion (https://www.akretion.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import models
from odoo.tools import format_amount


class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    def _get_reconcile_sale_order_mode(self):
        """Sale order reconciliation mode of this statement line's company."""
        self.ensure_one()
        return self.company_id.account_reconcile_sale_order_mode

    def _prepare_reconcile_line_data_sale_order_invoice(self, order):
        """In "payment" mode, don't create an invoice for the sale order."""
        if self._get_reconcile_sale_order_mode() == "payment":
            self._schedule_sale_order_paid_activity(order)
            return self.env["account.move.line"]
        return super()._prepare_reconcile_line_data_sale_order_invoice(order)

    def _schedule_sale_order_paid_activity(self, order):
        """Create an activity on the sale order to record that it is paid."""
        activity_type = self.env.ref(
            "account_reconcile_sale_order_no_invoice.activity_type_sale_order_paid"
        )
        if order.activity_ids.filtered(
            lambda activity: (
                activity.activity_type_id == activity_type and activity.state != "done"
            )
        ):
            return
        amount = format_amount(self.env, order.amount_total, order.currency_id)
        reference = self.payment_ref
        if not reference or reference == "/":
            reference = self.name
        order.activity_schedule(
            "account_reconcile_sale_order_no_invoice.activity_type_sale_order_paid",
            summary=f"Commande payée par lettrage bancaire {reference}",
            note=(
                f"<p>La commande <b>{order.name}</b> a été marquée comme payée "
                "lors du lettrage de la ligne bancaire "
                f"<a href='/web#model=account.bank.statement.line&amp;id={self.id}'>"
                f"{self.name}</a> du {self.date} (montant {amount}).</p>"
                "<p>Le paiement reste à lettrer avec la facture lorsque la "
                "commande sera facturée.</p>"
            ),
            user_id=order.user_id.id or self.env.uid,
        )

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
