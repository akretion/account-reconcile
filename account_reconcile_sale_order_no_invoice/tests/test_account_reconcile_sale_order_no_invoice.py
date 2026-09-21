# Copyright 2026 Akretion (https://www.akretion.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.tests import tagged

from odoo.addons.account_reconcile_sale_order.tests.test_account_reconcile_sale_order import (  # noqa: E501
    TestAccountReconcileSaleOrder,
)


@tagged("post_install", "-at_install")
class TestSaleOrderPaymentReconcile(TestAccountReconcileSaleOrder):
    """Check the "payment" mode: a bank line reconciled against a sale order
    registers the payment on the order without invoicing it."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company.account_reconcile_sale_order_mode = "payment"
        # Make sure the order total only depends on the unit price set in the
        # parent setUpClass (4242), whatever taxes are configured on the demo
        # product, so the bank statement amount matches the order total.
        cls.sale_order.order_line.tax_id = False

    def _reconcile_sale_order(self, manual=False):
        line = self.bank_statement.line_ids
        if manual:
            line.clean_reconcile()
            line.add_sale_order_id = self.sale_order
            line._onchange_add_sale_order_id()
        else:
            line.payment_ref = self.sale_order.name
            rule_result = self.model._apply_rules(line, line.partner_id)
            self.assertTrue(rule_result, "No sale order found by the rule")
            self.assertEqual(rule_result["status"], "sale_order_matching")
            line.clean_reconcile()
        line.reconcile_bank_line()
        return line

    def _assert_payment_registered_without_invoice(self):
        order = self.sale_order
        # The sale order is not invoiced...
        self.assertEqual(order.invoice_status, "no")
        self.assertFalse(
            self.env["account.move"].search(
                [
                    ("move_type", "=", "out_invoice"),
                    ("line_ids.sale_order_id", "=", order.id),
                ]
            ),
            "An invoice was created while reconciling in payment mode",
        )
        # ... but a receivable payment journal item linked to the order
        # exists, labelled with the sale order name.
        payment_lines = self.env["account.move.line"].search(
            [("sale_order_id", "=", order.id)]
        )
        self.assertEqual(len(payment_lines), 1)
        payment_line = payment_lines
        self.assertEqual(payment_line.name, order.name)
        self.assertEqual(payment_line.credit, order.amount_total)
        self.assertEqual(
            payment_line.account_id,
            order.partner_id.property_account_receivable_id,
        )
        self.assertEqual(payment_line.move_id.state, "posted")
        # ... and the order is flagged as paid.
        self.assertEqual(order.paid_amount, order.amount_total)
        self.assertTrue(order.is_paid)
        self.assertEqual(order.amount_due, 0.0)
        self.assertEqual(order.payment_line_count, 1)
        # ... and an activity records on the order that it is paid.
        activity_type = self.env.ref(
            "account_reconcile_sale_order_no_invoice.activity_type_sale_order_paid"
        )
        paid_activities = order.activity_ids.filtered(
            lambda activity: activity.activity_type_id == activity_type
        )
        self.assertEqual(
            len(paid_activities), 1, "One paid activity should be scheduled"
        )
        self.assertNotEqual(paid_activities.state, "done")

    def test_no_duplicate_paid_activity(self):
        """Test that scheduling the paid activity twice doesn't duplicate it"""
        self._reconcile_sale_order(manual=True)
        # Simulate a second payment registration on the same order.
        self.bank_statement.line_ids._schedule_sale_order_paid_activity(self.sale_order)
        activity_type = self.env.ref(
            "account_reconcile_sale_order_no_invoice.activity_type_sale_order_paid"
        )
        paid_activities = self.sale_order.activity_ids.filtered(
            lambda activity: activity.activity_type_id == activity_type
        )
        self.assertEqual(len(paid_activities), 1)

    def test_rule_reconcile_payment_mode(self):
        """Test that the sale order matching rule registers the payment and
        does not invoice the order in payment mode"""
        self._reconcile_sale_order()
        self._assert_payment_registered_without_invoice()

    def test_manual_reconcile_payment_mode(self):
        """Test that manually selecting a sale order in the reconcile widget
        registers the payment and does not invoice the order in payment mode"""
        self._reconcile_sale_order(manual=True)
        self._assert_payment_registered_without_invoice()
