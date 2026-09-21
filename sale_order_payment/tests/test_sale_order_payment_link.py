# Copyright 2026 Akretion (https://www.akretion.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import Command, fields
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestSaleOrderPaymentLink(AccountTestInvoicingCommon):
    """Check that the invoices generated from a sale order are reconciled
    automatically with the payments registered on this order."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.company_data["company"]
        cls.writeoff_account = cls.company_data["default_account_expense"]
        cls.company.write(
            {
                "sale_order_payment_writeoff_account_id": cls.writeoff_account.id,
                "sale_order_payment_writeoff_max_amount": 0.05,
            }
        )
        # Keep the amounts of the tests free of taxes and invoiced on the
        # ordered quantities.
        cls.product_a.taxes_id = False
        cls.product_a.invoice_policy = "order"

    def _create_sale_order(self, price=100.0, currency=False):
        pricelist = False
        if currency:
            pricelist = self.env["product.pricelist"].create(
                {"name": currency.name, "currency_id": currency.id}
            )
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner_a.id,
                "pricelist_id": pricelist.id if pricelist else False,
                "order_line": [
                    Command.create(
                        {
                            "product_id": self.product_a.id,
                            "product_uom_qty": 1.0,
                            "price_unit": price,
                        }
                    )
                ],
            }
        )
        order.action_confirm()
        return order

    def _register_payment(self, order, amount=None):
        """Register a payment on the sale order, as the bank statement
        reconciliation widget does."""
        amount = order.amount_total if amount is None else amount
        currency = order.currency_id
        balance = currency._convert(
            amount, self.company.currency_id, self.company, order.date_order
        )
        journal = self.company_data["default_journal_bank"]
        move = self.env["account.move"].create(
            {
                "move_type": "entry",
                "journal_id": journal.id,
                "date": order.date_order,
                "line_ids": [
                    Command.create(
                        {
                            "name": order.name,
                            "account_id": self.company_data[
                                "default_account_receivable"
                            ].id,
                            "partner_id": order.partner_id.id,
                            "currency_id": currency.id,
                            "amount_currency": -amount,
                            "balance": -balance,
                            "sale_order_id": order.id,
                        }
                    ),
                    Command.create(
                        {
                            "name": order.name,
                            "account_id": journal.default_account_id.id,
                            "partner_id": order.partner_id.id,
                            "debit": balance,
                        }
                    ),
                ],
            }
        )
        move.action_post()
        return move

    def _invoice_sale_order(self, order, price=None):
        """Generate the invoice of the sale order, optionally changing its
        amount to create a difference with the payments."""
        invoice = order._create_invoices()
        if price is not None:
            invoice.invoice_line_ids.price_unit = price
        invoice.action_post()
        return invoice

    def _get_writeoff_moves(self):
        return self.env["account.move"].search(
            [("move_type", "=", "entry"), ("ref", "like", "Payment write-off on")]
        )

    def _create_currency(self, rate):
        """Create a testing currency, with the given rate against the company
        currency (the rate of the company currency being 1)."""
        currency = self.env["res.currency"].create(
            {"name": "TST", "symbol": "T", "rounding": 0.01}
        )
        self.env["res.currency.rate"].create(
            {
                "currency_id": currency.id,
                "name": fields.Date.today(),
                "rate": rate,
            }
        )
        return currency

    def assertIsReconciledWithPayment(self, invoice, order):
        """Check that the invoice is fully paid and that its receivable is
        reconciled with the payment lines of the sale order."""
        self.assertEqual(invoice.payment_state, "paid")
        self.assertEqual(invoice.amount_residual, 0.0)
        receivable_lines = invoice.line_ids.filtered(
            lambda line: line.account_id.account_type == "asset_receivable"
        )
        self.assertTrue(receivable_lines)
        self.assertTrue(receivable_lines.reconciled)
        for payment_line in order.payment_line_ids:
            self.assertTrue(
                payment_line.reconciled,
                "The payment line should be reconciled with the invoice",
            )

    def test_payment_info(self):
        """The payment information of the sale order is computed from the
        journal items linked to the order."""
        order = self._create_sale_order()
        self.assertEqual(order.payment_line_count, 0)
        self.assertEqual(order.paid_amount, 0.0)
        self.assertEqual(order.amount_due, order.amount_total)
        self.assertFalse(order.is_paid)

        self._register_payment(order)

        self.assertEqual(order.payment_line_count, 1)
        self.assertEqual(order.paid_amount, order.amount_total)
        self.assertEqual(order.amount_due, 0.0)
        self.assertTrue(order.is_paid)

    def test_invoice_reconciled_with_payment(self):
        """The invoice generated from a paid sale order is reconciled with the
        payment."""
        order = self._create_sale_order()
        self._register_payment(order)
        invoice = self._invoice_sale_order(order)

        self.assertFalse(self._get_writeoff_moves())
        self.assertIsReconciledWithPayment(invoice, order)

    def test_invoice_reconciled_with_writeoff(self):
        """A small difference between the invoice and the payment is written
        off so that the invoice is reconciled anyway."""
        order = self._create_sale_order()
        self._register_payment(order)
        # The invoice is 1 cent below the payment.
        invoice = self._invoice_sale_order(order, price=99.99)

        writeoff_moves = self._get_writeoff_moves()
        self.assertEqual(len(writeoff_moves), 1)
        self.assertIn(order.name, writeoff_moves.ref)
        self.assertIn(invoice.name, writeoff_moves.ref)
        self.assertEqual(writeoff_moves.state, "posted")
        writeoff_lines = writeoff_moves.line_ids
        self.assertEqual(len(writeoff_lines), 2)
        # The customer paid 1 cent more than the invoice: the receivable is
        # debited and the counterpart credited on the write-off account.
        receivable_line = writeoff_lines.filtered(
            lambda line: line.account_id
            == self.company_data["default_account_receivable"]
        )
        self.assertEqual(receivable_line.debit, 0.01)
        self.assertEqual(receivable_line.partner_id, self.partner_a)
        counter_line = writeoff_lines - receivable_line
        self.assertEqual(counter_line.account_id, self.writeoff_account)
        self.assertEqual(counter_line.credit, 0.01)

        self.assertIsReconciledWithPayment(invoice, order)
        # The write-off entry must not be taken as a payment of the order.
        self.assertEqual(order.paid_amount, order.amount_total)
        self.assertTrue(order.is_paid)

    def test_invoice_reconciled_with_writeoff_in_foreign_currency(self):
        """The write-off is expressed in the currency of the invoice."""
        currency = self._create_currency(0.9)
        order = self._create_sale_order(price=1000.0, currency=currency)
        self._register_payment(order)
        # The invoice is 1 cent (in the invoice currency) below the payment.
        invoice = self._invoice_sale_order(order, price=999.99)
        self.assertEqual(invoice.currency_id, currency)

        writeoff_moves = self._get_writeoff_moves()
        self.assertEqual(len(writeoff_moves), 1)
        counter_line = writeoff_moves.line_ids.filtered(
            lambda line: line.account_id == self.writeoff_account
        )
        self.assertEqual(counter_line.currency_id, currency)
        self.assertEqual(counter_line.amount_currency, -0.01)
        self.assertEqual(counter_line.credit, 0.01)

        self.assertIsReconciledWithPayment(invoice, order)

    def test_invoice_reconciled_with_writeoff_rounded_in_company_currency(self):
        """The difference is written off even when it doesn't represent any
        amount in the company currency (low value coins)."""
        currency = self._create_currency(200)
        order = self._create_sale_order(price=1000.0, currency=currency)
        self._register_payment(order)
        invoice = self._invoice_sale_order(order, price=999.99)

        writeoff_moves = self._get_writeoff_moves()
        self.assertEqual(len(writeoff_moves), 1)
        counter_line = writeoff_moves.line_ids.filtered(
            lambda line: line.account_id == self.writeoff_account
        )
        self.assertEqual(counter_line.currency_id, currency)
        self.assertEqual(counter_line.amount_currency, -0.01)
        self.assertEqual(counter_line.credit, 0.0)

        self.assertIsReconciledWithPayment(invoice, order)

    def test_no_reconcile_when_difference_too_big(self):
        """When the difference between the invoice and the payments is too big
        to be written off, nothing is reconciled and a message is posted on the
        invoice."""
        order = self._create_sale_order()
        self._register_payment(order, amount=50.0)
        invoice = self._invoice_sale_order(order)

        self.assertFalse(self._get_writeoff_moves())
        self.assertEqual(invoice.payment_state, "not_paid")
        self.assertEqual(invoice.amount_residual, 100.0)
        self.assertFalse(order.payment_line_ids.reconciled)
        self.assertTrue(
            invoice.message_ids.filtered(
                lambda message: "Please reconcile this invoice manually"
                in (message.body or "")
            ),
            "A message should tell the difference couldn't be reconciled",
        )

    def test_no_writeoff_without_account(self):
        """The write-off is disabled when no account is configured."""
        self.company.sale_order_payment_writeoff_account_id = False
        order = self._create_sale_order()
        self._register_payment(order)
        invoice = self._invoice_sale_order(order, price=99.99)

        self.assertFalse(self._get_writeoff_moves())
        self.assertEqual(invoice.payment_state, "not_paid")
        self.assertFalse(order.payment_line_ids.reconciled)

    def test_no_reconcile_without_payment(self):
        """Nothing is done when the sale order has no payment."""
        order = self._create_sale_order()
        invoice = self._invoice_sale_order(order)

        self.assertEqual(invoice.payment_state, "not_paid")
        self.assertEqual(invoice.amount_residual, 100.0)
