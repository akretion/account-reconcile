# Copyright 2011-2019 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import odoo
from odoo import fields

from odoo.addons.account.tests.common import TestAccountReconciliationCommon


@odoo.tests.tagged("post_install", "-at_install")
class TestCompleteTransaction(TestAccountReconciliationCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        acquirer = cls.env.ref("payment.payment_acquirer_transfer")
        acquirer.write({"payment_creation_mode": "statement_import"})
        cls.transaction = cls.env["payment.transaction"].create(
            {
                "reference": "123456789",
                "partner_id": cls.partner_agrolait_id,
                "acquirer_id": acquirer.id,
                "amount": 50.0,
                "currency_id": cls.env.ref("base.USD").id,
            }
        )
        rule = cls.env.ref(
            "account_move_transaction_import.account_move_completion_rule_transaction"
        )
        # create journal with profile
        cls.bank_journal = cls.company_data["default_journal_bank"]
        cls.bank_journal.write(
            {"used_for_completion": True, "rule_ids": [(4, rule.id, False)]}
        )
        cls.account_receivable = cls.company_data["default_account_receivable"]
        cls.account_bank = cls.env["account.account"].search(
            [
                (
                    "user_type_id",
                    "=",
                    cls.env.ref("account.data_account_type_liquidity").id,
                ),
            ],
            limit=1,
        )
        cls.move = cls.env["account.move"].create(
            {"name": "Test move", "journal_id": cls.bank_journal.id}
        )
        cls.env["account.move.line"].create(
            [
                {
                    "name": "123456789",
                    "account_id": cls.account_receivable.id,
                    "move_id": cls.move.id,
                    "credit": 50,
                },
                {
                    "name": "counter part",
                    "account_id": cls.account_bank.id,
                    "move_id": cls.move.id,
                    "debit": 50,
                },
            ]
        )
        cls.receivable_aml = cls.move.line_ids.filtered(
            lambda line: line.account_id == cls.account_receivable
        )
        cls.invoice = cls._create_invoice(
            cls, date_invoice=fields.Date.today(), auto_validate=False
        )

    def test_completion_from_transaction(self):
        self.assertFalse(self.receivable_aml.partner_id)
        self.move.button_auto_completion()
        self.assertEqual(
            self.receivable_aml.partner_id.id,
            self.partner_agrolait_id,
        )
        self.assertEqual(
            self.receivable_aml.transaction_id,
            self.transaction,
        )

    def test_reconcile_invoice_with_existing_payment_transaction(self):
        # create the payment linked to transaction
        self.move.button_auto_completion()
        self.move.action_post()

        # link the invoice to transaction and validate
        self.invoice.write({"transaction_ids": [(6, 0, self.transaction.ids)]})
        self.invoice.action_post()
        self.assertEqual(self.invoice.payment_state, "paid")

    def test_reconcile_payment_transaction_with_existing_invoice(self):
        self.invoice.write({"transaction_ids": [(6, 0, self.transaction.ids)]})
        self.invoice.action_post()
        # create the payment linked to transaction
        self.move.button_auto_completion()
        self.move.action_post()
        self.assertEqual(self.invoice.payment_state, "paid")
