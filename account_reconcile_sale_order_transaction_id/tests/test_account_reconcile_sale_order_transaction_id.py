# Copyright 2026 Akretion (https://www.akretion.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.tests import tagged

from odoo.addons.account_reconcile_model_oca.tests.common import (
    TestAccountReconciliationCommon,
)


@tagged("post_install", "-at_install")
class TestAccountReconcileSaleOrderTransactionId(TestAccountReconciliationCommon):
    """Check the matching of sale orders from the transaction ID, and the
    propagation of that transaction ID on the counterpart journal item."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.rule = cls.env.ref(
            "account_reconcile_sale_order_transaction_id."
            "account_reconcile_model_so_transaction_id"
        )
        cls.rule.sudo().company_id = cls.company
        cls.transaction_id = "TXN42424242"
        cls.amount = 4242.0
        cls.sale_order = cls.env["sale.order"].create(
            {
                "partner_id": cls.partner_agrolait.id,
                "transaction_id": cls.transaction_id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "name": "Order line",
                            "product_id": cls.product.id,
                            "price_unit": cls.amount,
                        },
                    )
                ],
            }
        )
        # Tax free total, so the amount of the statement line matches the total
        # of the sale order whatever taxes are configured on the product.
        cls.sale_order.order_line.tax_id = False
        cls.bank_statement = cls.env["account.bank.statement"].create(
            {
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "bank payment",
                            "amount": cls.amount,
                            "payment_ref": "/",
                            "partner_id": cls.partner_agrolait.id,
                        },
                    )
                ],
                "journal_id": cls.bank_journal_euro.id,
            }
        )

    def _statement_line(self):
        return self.bank_statement.line_ids

    def test_rule_match_transaction_id(self):
        """The rule finds the sale order from the transaction ID"""
        line = self._statement_line()
        # The reference of the statement line is the transaction ID, not the
        # name of the sale order.
        line.payment_ref = self.transaction_id
        rule_result = self.rule._apply_rules(line, line.partner_id)
        self.assertTrue(rule_result, "No sale order found by the rule")
        self.assertEqual(rule_result["status"], "sale_order_matching")
        self.assertEqual(rule_result["amls"], self.sale_order)

    def test_rule_no_match_when_option_disabled(self):
        """Without the option, the transaction ID is not used for the match"""
        self.rule.sale_order_matching_transaction_id = False
        line = self._statement_line()
        line.payment_ref = self.transaction_id
        self.assertFalse(self.rule._apply_rules(line, line.partner_id))

    def test_rule_match_transaction_id_in_label_with_token_match(self):
        """With the token option, the transaction ID is found inside a longer
        reference"""
        line = self._statement_line()
        line.payment_ref = f"Payment for {self.transaction_id}"
        # Without the token option, the whole reference is compared.
        self.assertFalse(self.rule._apply_rules(line, line.partner_id))
        # With the token option, each significant word is compared as well.
        self.rule.sale_order_matching_token_match = True
        rule_result = self.rule._apply_rules(line, line.partner_id)
        self.assertTrue(rule_result, "No sale order found by the rule")
        self.assertEqual(rule_result["amls"], self.sale_order)

    def test_transaction_id_set_on_counterpart(self):
        """The counterpart journal item created for the sale order holds the
        transaction ID of the sale order"""
        line = self._statement_line()
        line.payment_ref = self.transaction_id
        line.clean_reconcile()
        sale_order_lines = [
            line_data
            for line_data in line.reconcile_data_info["data"]
            if line_data.get("sale_order_id") == self.sale_order.id
        ]
        self.assertEqual(len(sale_order_lines), 1, "Sale order not proposed")
        line.reconcile_bank_line()
        counterpart_lines = self.env["account.move.line"].search(
            [
                ("transaction_id", "=", self.transaction_id),
                ("move_id.move_type", "=", "entry"),
            ]
        )
        self.assertEqual(
            len(counterpart_lines), 1, "No counterpart found for the transaction ID"
        )
        self.assertEqual(
            counterpart_lines.account_id,
            self.sale_order.partner_id.property_account_receivable_id,
        )
        self.assertEqual(counterpart_lines.credit, self.sale_order.amount_total)
