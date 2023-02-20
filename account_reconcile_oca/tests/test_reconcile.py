import time

import odoo.tests

from odoo.addons.account.tests.common import TestAccountReconciliationCommon


@odoo.tests.tagged("post_install", "-at_install")
class TestReconciliationWidget(TestAccountReconciliationCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.acc_bank_stmt_model = cls.env["account.bank.statement"]
        cls.acc_bank_stmt_line_model = cls.env["account.bank.statement.line"]
        cls.bank_journal_usd.suspense_account_id = (
            cls.company.account_journal_suspense_account_id
        )
        cls.bank_journal_euro.suspense_account_id = (
            cls.company.account_journal_suspense_account_id
        )

    def test_filter_partner(self):
        inv1 = self.create_invoice(currency_id=self.currency_euro_id)
        inv2 = self.create_invoice(currency_id=self.currency_euro_id)
        partner = inv1.partner_id

        receivable1 = inv1.line_ids.filtered(
            lambda l: l.account_id.account_type == "asset_receivable"
        )
        self.assertTrue(receivable1)
        receivable2 = inv2.line_ids.filtered(
            lambda l: l.account_id.account_type == "asset_receivable"
        )
        self.assertTrue(receivable2)

        bank_stmt = self.acc_bank_stmt_model.create(
            {
                "company_id": self.env.ref("base.main_company").id,
                "journal_id": self.bank_journal_euro.id,
                "date": time.strftime("%Y-07-15"),
                "name": "test",
            }
        )

        bank_stmt_line = self.acc_bank_stmt_line_model.create(
            {
                "name": "testLine",
                "journal_id": self.bank_journal_euro.id,
                "statement_id": bank_stmt.id,
                "amount": 100,
                "date": time.strftime("%Y-07-15"),
            }
        )

        # Without a partner set, No default data

        bkstmt_data = bank_stmt_line.reconcile_data_info
        mv_lines_ids = bkstmt_data["counterparts"]
        self.assertNotIn(receivable1.id, mv_lines_ids)
        self.assertNotIn(receivable2.id, mv_lines_ids)

        # This is like input a partner in the widget

        bank_stmt_line.partner_id = partner
        bank_stmt_line.flush_recordset()
        bank_stmt_line.invalidate_recordset()
        bkstmt_data = bank_stmt_line.reconcile_data_info
        mv_lines_ids = bkstmt_data["counterparts"]

        self.assertIn(receivable1.id, mv_lines_ids)
        self.assertIn(receivable2.id, mv_lines_ids)

        # With a partner set, type the invoice reference in the filter
        bank_stmt_line.payment_ref = inv1.payment_reference
        bank_stmt_line.flush_recordset()
        bank_stmt_line.invalidate_recordset()
        bkstmt_data = bank_stmt_line.reconcile_data_info
        mv_lines_ids = bkstmt_data["counterparts"]

        self.assertIn(receivable1.id, mv_lines_ids)
        self.assertNotIn(receivable2.id, mv_lines_ids)

    def test_partner_name_with_parent(self):
        parent_partner = self.env["res.partner"].create(
            {
                "name": "test",
            }
        )
        child_partner = self.env["res.partner"].create(
            {
                "name": "test",
                "parent_id": parent_partner.id,
                "type": "delivery",
            }
        )
        self.create_invoice_partner(
            currency_id=self.currency_euro_id, partner_id=child_partner.id
        )

        bank_stmt = self.acc_bank_stmt_model.create(
            {
                "company_id": self.env.ref("base.main_company").id,
                "journal_id": self.bank_journal_euro.id,
                "date": time.strftime("%Y-07-15"),
                "name": "test",
            }
        )

        bank_stmt_line = self.acc_bank_stmt_line_model.create(
            {
                "name": "testLine",
                "statement_id": bank_stmt.id,
                "journal_id": self.bank_journal_euro.id,
                "amount": 100,
                "date": time.strftime("%Y-07-15"),
                "payment_ref": "test",
                "partner_name": "test",
            }
        )

        bkstmt_data = bank_stmt_line.reconcile_data_info
        self.assertEqual(len(bkstmt_data["counterparts"]), 1)
        self.assertEqual(
            self.env["account.move.line"]
            .browse(bkstmt_data["counterparts"])
            .partner_id,
            parent_partner,
        )
