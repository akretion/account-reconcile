# Copyright 2026 Akretion (https://www.akretion.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from unittest.mock import patch

from odoo.tests import tagged
from odoo.tools import format_date

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
        # the emails are not sent for real during the tests
        mail_send_patch = patch.object(
            type(cls.env["mail.mail"]), "send", lambda mail, **kwargs: True
        )
        mail_send_patch.start()
        cls.addClassCleanup(mail_send_patch.stop)
        cls.company.account_reconcile_sale_order_mode = "payment"
        # The salesperson of the order receives the email notifying that the
        # order is paid: the users of the test database may have no email.
        cls.salesperson = cls.env["res.users"].create(
            {
                "name": "Salesperson",
                "login": "salesperson_sale_order_paid",
                "email": "salesperson@example.com",
            }
        )
        cls.sale_order.user_id = cls.salesperson
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
        # ... and the salesperson is notified by email that the order is paid.
        mail = self.env["mail.mail"].search(
            [
                ("model", "=", "sale.order"),
                ("res_id", "=", order.id),
            ]
        )
        self.assertEqual(len(mail), 1, "One email should be sent to the salesperson")
        # the recipient is set on the mail template (the salesperson by default)
        self.assertIn(order.user_id.email, mail.email_to)
        self.assertIn(order.name, mail.subject)
        self.assertIn(order.name, mail.body_html)
        # the statement line which registered the payment is described in the
        # email (with the date of the bank transaction)
        self.assertIn(
            format_date(self.env, self.bank_statement.line_ids.date), mail.body_html
        )

    def test_no_duplicate_paid_mail(self):
        """Test that the salesperson is not notified again when the order is
        already paid"""
        self._reconcile_sale_order(manual=True)
        order = self.sale_order
        mails = self.env["mail.mail"].search(
            [("model", "=", "sale.order"), ("res_id", "=", order.id)]
        )
        self.assertEqual(len(mails), 1)
        # a second registration of the payment doesn't send another email
        self.assertFalse(self.bank_statement.line_ids._send_sale_order_paid_mail(order))
        mails = self.env["mail.mail"].search(
            [("model", "=", "sale.order"), ("res_id", "=", order.id)]
        )
        self.assertEqual(len(mails), 1)

    def test_no_mail_when_the_journal_disables_the_notification(self):
        """The notification is skipped when the journal is configured so, for
        example for an automated import which reconciles the transactions."""
        self.bank_statement.journal_id.notify_sale_order_paid = False
        self._reconcile_sale_order()
        order = self.sale_order
        self.assertTrue(order.is_paid)
        mails = self.env["mail.mail"].search(
            [("model", "=", "sale.order"), ("res_id", "=", order.id)]
        )
        self.assertFalse(mails)

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
