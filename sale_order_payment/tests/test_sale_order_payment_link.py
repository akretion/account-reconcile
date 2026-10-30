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

    def _ship_part_of_sale_order(self, order, quantity):
        """Only a part of the sale order is shipped, so only this part of the
        order can be invoiced.

        The unit price is written again on purpose: changing the quantity
        triggers its computation from the pricelist.
        """
        line = order.order_line
        line.write({"product_uom_qty": quantity, "price_unit": line.price_unit})

    def _invoice_sale_order(self, order, price=None):
        """Generate the invoice of the sale order, optionally changing its
        amount to create a difference with the payments."""
        invoice = order._create_invoices()
        if price is not None:
            invoice.invoice_line_ids.price_unit = price
        invoice.action_post()
        return invoice

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

        self.assertIsReconciledWithPayment(invoice, order)

    def test_partial_invoice_reconciled_with_payment(self):
        """An invoice covering only a part of the sale order is partially
        reconciled with the payment of the order."""
        order = self._create_sale_order()
        self._register_payment(order)
        # Only 60% of the order is shipped, so the invoice covers a part of it
        # only.
        self._ship_part_of_sale_order(order, 0.6)
        invoice = self._invoice_sale_order(order)
        self.assertEqual(invoice.amount_total, 60.0)

        self.assertEqual(invoice.payment_state, "paid")
        self.assertEqual(invoice.amount_residual, 0.0)
        payment_line = order.payment_line_ids
        self.assertEqual(len(payment_line), 1)
        # The payment is only partially used: its remaining amount stays
        # available for the next invoice of the order.
        self.assertFalse(payment_line.reconciled)
        self.assertEqual(payment_line.amount_residual, -40.0)

    def test_invoices_reconciled_with_payment(self):
        """The payments of a sale order are reconciled with each invoice of the
        order, the last one reconciling them completely."""
        order = self._create_sale_order()
        self._register_payment(order)
        # First shipment: 60% of the order.
        self._ship_part_of_sale_order(order, 0.6)
        first_invoice = self._invoice_sale_order(order)
        self.assertEqual(first_invoice.amount_total, 60.0)
        payment_line = order.payment_line_ids
        self.assertFalse(payment_line.reconciled)

        # Second shipment: the rest of the order.
        self._ship_part_of_sale_order(order, 1.0)
        second_invoice = self._invoice_sale_order(order)
        self.assertEqual(second_invoice.amount_total, 40.0)

        self.assertIsReconciledWithPayment(first_invoice, order)
        self.assertIsReconciledWithPayment(second_invoice, order)

    def test_partial_invoice_reconciled_with_payment_in_foreign_currency(self):
        """The reconciliation is partial as well when the invoice is expressed
        in another currency than the company one."""
        currency = self._create_currency(0.9)
        order = self._create_sale_order(price=1000.0, currency=currency)
        self._register_payment(order)
        self._ship_part_of_sale_order(order, 0.6)
        invoice = self._invoice_sale_order(order)
        self.assertEqual(invoice.currency_id, currency)
        self.assertEqual(invoice.amount_total, 600.0)

        self.assertEqual(invoice.payment_state, "paid")
        payment_line = order.payment_line_ids
        self.assertFalse(payment_line.reconciled)
        self.assertEqual(payment_line.amount_residual_currency, -400.0)

    def test_partial_payment_reconciled_with_invoice(self):
        """The invoice is reconciled with the amount available on the payment
        of the order, the difference being left open on the invoice."""
        order = self._create_sale_order()
        self._register_payment(order, amount=50.0)
        invoice = self._invoice_sale_order(order)

        self.assertEqual(invoice.payment_state, "partial")
        self.assertEqual(invoice.amount_residual, 50.0)
        self.assertTrue(order.payment_line_ids.reconciled)

    def test_no_reconcile_without_payment(self):
        """Nothing is done when the sale order has no payment."""
        order = self._create_sale_order()
        invoice = self._invoice_sale_order(order)

        self.assertEqual(invoice.payment_state, "not_paid")
        self.assertEqual(invoice.amount_residual, 100.0)
