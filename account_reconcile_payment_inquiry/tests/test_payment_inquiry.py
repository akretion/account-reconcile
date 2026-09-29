# Copyright 2026 Akretion France (https://www.akretion.com/)
# @author: Benoît Guillot <benoit.guillot@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest.mock import patch

from lxml import etree

from odoo import Command
from odoo.exceptions import AccessError, UserError
from odoo.tests import Form, tagged
from odoo.tools import mute_logger
from odoo.tools.safe_eval import safe_eval

from odoo.addons.account_reconcile_oca.tests.test_bank_account_reconcile import (
    TestAccountReconciliationCommon,
)


@tagged("post_install", "-at_install")
class TestPaymentInquiry(TestAccountReconciliationCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # the emails are not sent for real during the tests
        mail_send_patch = patch.object(
            type(cls.env["mail.mail"]), "send", lambda mail, **kwargs: True
        )
        mail_send_patch.start()
        cls.addClassCleanup(mail_send_patch.stop)
        cls.sales_admin_group = cls.env.ref(
            "account_reconcile_payment_inquiry.group_payment_inquiry"
        )
        # the recipients of the e-mail are configured on the mail template
        cls.env.ref(
            "account_reconcile_payment_inquiry.payment_inquiry_mail_template"
        ).email_to = "sales_administration@example.com"
        # user of the Sales Administration: it has NO accounting group
        cls.sales_admin_user = cls.env["res.users"].create(
            {
                "name": "Sales Administration",
                "login": "sales_administration_payment_inquiry",
                "email": "sales_administration@example.com",
                "groups_id": [
                    Command.set(
                        [cls.env.ref("base.group_user").id, cls.sales_admin_group.id]
                    )
                ],
            }
        )
        # accountant: it has the write access on the bank transactions
        cls.accountant_user = cls.env["res.users"].create(
            {
                "name": "Simple Accountant",
                "login": "simple_accountant_payment_inquiry",
                "email": "simple_accountant@example.com",
                "groups_id": [
                    Command.set(
                        [
                            cls.env.ref("base.group_user").id,
                            cls.env.ref("account.group_account_basic").id,
                        ]
                    )
                ],
            }
        )
        cls.bank_stmt = cls.acc_bank_stmt_model.create(
            {
                "journal_id": cls.bank_journal_euro.id,
                "date": "2026-07-15",
                "name": "payment inquiry test",
            }
        )

    def _create_bank_stmt_line(self, amount=100):
        return self.acc_bank_stmt_line_model.create(
            {
                "name": "unidentified payment",
                "journal_id": self.bank_journal_euro.id,
                "statement_id": self.bank_stmt.id,
                "amount": amount,
                "date": "2026-07-15",
                "payment_ref": "VIR RECU 1234",
            }
        )

    def test_payment_inquiry_ask(self):
        """The accountant flags the transaction from the widget."""
        line = self._create_bank_stmt_line()
        self.assertFalse(line.payment_inquiry_state)
        line.with_user(self.accountant_user).action_payment_inquiry_ask()
        self.assertEqual(line.payment_inquiry_state, "to_answer")
        self.assertEqual(line.payment_inquiry_user_id, self.accountant_user)
        self.assertTrue(line.payment_inquiry_date)
        self.assertFalse(line.payment_inquiry_note)

    def test_payment_inquiry_ask_sends_mail(self):
        """Asking for an identification sends an e-mail with the details of the
        bank transaction, to the recipients configured on the mail template."""
        line = self._create_bank_stmt_line()
        line.with_user(self.accountant_user).action_payment_inquiry_ask()
        mails = self.env["mail.mail"].search(
            [
                ("model", "=", "account.bank.statement.line"),
                ("res_id", "=", line.id),
            ]
        )
        self.assertEqual(len(mails), 1)
        # the recipients come from the mail template, the e-mail is queued
        self.assertEqual(mails.email_to, "sales_administration@example.com")
        self.assertEqual(mails.state, "outgoing")
        self.assertIn(line.payment_ref, mails.subject)
        # the details of the transaction are in the email
        self.assertIn(line.payment_ref, mails.body_html)
        self.assertIn(line.journal_id.name, mails.body_html)

    def test_payment_inquiry_technical_group(self):
        """The group is technical: it is not part of the rights of an app."""
        self.assertFalse(
            self.sales_admin_group.category_id,
            "The Payment Inquiry group must be a technical group: it must not "
            "be part of the access rights of an application.",
        )

    def test_payment_inquiry_menu_in_sales_orders_menu(self):
        """The menu is in the Orders menu of the Sales app, above the Sales
        Teams menu, and the Sales Administration user sees it."""
        menu = self.env.ref("account_reconcile_payment_inquiry.payment_inquiry_menu")
        orders_menu = self.env.ref("sale.sale_order_menu")
        self.assertEqual(menu.parent_id, orders_menu)
        self.assertEqual(menu.groups_id, self.sales_admin_group)
        sales_teams_menu = self.env.ref("sale.report_sales_team")
        self.assertLess(menu.sequence, sales_teams_menu.sequence)
        sales_admin_menus = (
            self.env["ir.ui.menu"]
            .with_user(self.sales_admin_user)
            .load_menus(debug=False)
        )
        self.assertIn(menu.id, sales_admin_menus)
        self.assertEqual(sales_admin_menus[menu.id]["parent_id"][0], orders_menu.id)
        self.assertEqual(
            sales_admin_menus[menu.id]["app_id"], self.env.ref("sale.sale_menu_root").id
        )

    @mute_logger("odoo.addons.mail.models.mail_mail")
    def test_payment_inquiry_filter_in_reconcile_view(self):
        """The filter which hides the transactions waiting for an answer is
        available in the reconciliation view, but not activated by default."""
        search_arch = self.acc_bank_stmt_line_model.get_view(view_type="search")["arch"]
        self.assertIn('name="payment_inquiry_not_pending"', search_arch)
        domain_str = etree.fromstring(search_arch).xpath(
            "//filter[@name='payment_inquiry_not_pending']/@domain"
        )[0]
        domain = safe_eval(domain_str)
        self.assertEqual(domain, [("payment_inquiry_state", "!=", "to_answer")])
        # the filter is not activated by default in the reconciliation views:
        # a transaction waiting for an answer is visible, with its banner
        for action_xmlid in (
            "account_reconcile_oca.action_bank_statement_line_reconcile",
            "account_reconcile_oca.action_bank_statement_line_reconcile_all",
        ):
            action = self.env.ref(action_xmlid)
            context = safe_eval(
                action.context, {"active_id": self.bank_journal_euro.id}
            )
            self.assertFalse(
                context.get("search_default_payment_inquiry_not_pending"),
                f"The filter must not be activated by default on {action_xmlid}",
            )
        # the filter keeps the transactions which are not waiting for an answer
        line = self._create_bank_stmt_line()
        other_line = self._create_bank_stmt_line(amount=200)
        line.with_user(self.accountant_user).action_payment_inquiry_ask()
        search_domain = [("id", "in", (line + other_line).ids)] + domain
        self.assertEqual(
            self.acc_bank_stmt_line_model.search(search_domain), other_line
        )
        # the transaction is back when the Sales Administration answers
        line.with_user(self.sales_admin_user).write({"payment_inquiry_note": "Answer"})
        line.with_user(self.sales_admin_user).action_payment_inquiry_answer()
        self.assertEqual(
            self.acc_bank_stmt_line_model.search(search_domain), line + other_line
        )

    @mute_logger("odoo.addons.mail.models.mail_mail")
    def test_payment_inquiry_ask_twice_resets_answer(self):
        """Asking again must not keep the answer of the previous inquiry."""
        line = self._create_bank_stmt_line()
        line.with_user(self.accountant_user).action_payment_inquiry_ask()
        line.with_user(self.sales_admin_user).write(
            {"payment_inquiry_note": "Customer X"}
        )
        line.with_user(self.sales_admin_user).action_payment_inquiry_answer()
        self.assertEqual(line.payment_inquiry_state, "answered")
        line.with_user(self.accountant_user).action_payment_inquiry_ask()
        self.assertEqual(line.payment_inquiry_state, "to_answer")
        self.assertFalse(line.payment_inquiry_note)
        self.assertFalse(line.payment_inquiry_answer_user_id)
        self.assertFalse(line.payment_inquiry_answer_date)

    @mute_logger("odoo.addons.mail.models.mail_mail")
    def test_payment_inquiry_answer_notifies_the_requester(self):
        """The Sales Administration answers: the requester gets the answer in a
        planned activity."""
        line = self._create_bank_stmt_line()
        line.with_user(self.accountant_user).action_payment_inquiry_ask()
        line.with_user(self.sales_admin_user).write(
            {"payment_inquiry_note": "Payment of invoice INV/2026/0012 (Deco Addict)"}
        )
        line.with_user(self.sales_admin_user).action_payment_inquiry_answer()
        self.assertEqual(line.payment_inquiry_state, "answered")
        self.assertEqual(line.payment_inquiry_answer_user_id, self.sales_admin_user)
        self.assertTrue(line.payment_inquiry_answer_date)
        activity = self.env["mail.activity"].search(
            [
                ("res_model", "=", "account.move"),
                ("res_id", "=", line.move_id.id),
                ("user_id", "=", self.accountant_user.id),
            ]
        )
        self.assertEqual(len(activity), 1)
        self.assertIn("VIR RECU 1234", activity.summary)
        self.assertIn("INV/2026/0012", activity.note)
        # the answer also lands in the chatter of the journal entry
        message = line.move_id.message_ids.filtered(lambda m: "INV/2026/0012" in m.body)
        self.assertTrue(message)

    def test_payment_inquiry_answer_requires_a_note(self):
        line = self._create_bank_stmt_line()
        line.with_user(self.accountant_user).action_payment_inquiry_ask()
        with self.assertRaises(UserError):
            line.with_user(self.sales_admin_user).action_payment_inquiry_answer()

    def test_payment_inquiry_restricted_to_the_answer(self):
        """The Sales Administration cannot modify the transaction itself."""
        line = self._create_bank_stmt_line()
        line.with_user(self.accountant_user).action_payment_inquiry_ask()
        with self.assertRaises(AccessError):
            line.with_user(self.sales_admin_user).write({"payment_ref": "hacked"})
        with self.assertRaises(AccessError):
            line.with_user(self.sales_admin_user).write({"amount": 12345})
        line.with_user(self.sales_admin_user).write({"payment_inquiry_note": "ok"})
        self.assertEqual(line.payment_inquiry_note, "ok")
        self.assertEqual(line.payment_ref, "VIR RECU 1234")
        # no create / unlink for the Sales Administration
        with self.assertRaises(AccessError):
            self.acc_bank_stmt_line_model.with_user(self.sales_admin_user).create(
                {
                    "journal_id": self.bank_journal_euro.id,
                    "amount": 10,
                    "date": "2026-07-15",
                }
            )
        with self.assertRaises(AccessError):
            line.with_user(self.sales_admin_user).unlink()
        # an accountant is not impacted by the restriction
        line.with_user(self.accountant_user).write({"payment_ref": "VIR RECU 1234 bis"})
        self.assertEqual(line.payment_ref, "VIR RECU 1234 bis")

    def test_payment_inquiry_menu(self):
        """The Sales Administration finds the flagged transactions in its menu."""
        line = self._create_bank_stmt_line()
        other_line = self._create_bank_stmt_line(amount=200)
        line.with_user(self.accountant_user).action_payment_inquiry_ask()
        # the transaction which is not flagged is not in the menu
        self.assertFalse(other_line.payment_inquiry_state)
        action = self.env.ref(
            "account_reconcile_payment_inquiry.payment_inquiry_action"
        )
        sales_admin_lines = (
            self.acc_bank_stmt_line_model.with_user(self.sales_admin_user)
            .search(safe_eval(action.domain))
            .read(
                [
                    "date",
                    "journal_id",
                    "payment_ref",
                    "partner_id",
                    "amount",
                    "currency_id",
                    "transaction_type",
                    "payment_inquiry_state",
                    "payment_inquiry_user_id",
                    "payment_inquiry_date",
                    "payment_inquiry_note",
                ]
            )
        )
        self.assertEqual({line["id"] for line in sales_admin_lines}, set(line.ids))
        # the views of the menu are readable by the Sales Administration
        search_arch = self.acc_bank_stmt_line_model.with_user(
            self.sales_admin_user
        ).get_view(
            view_id=self.env.ref(
                "account_statement_base.account_bank_statement_line_search"
            ).id,
            view_type="search",
        )["arch"]
        self.assertIn('name="payment_inquiry_to_answer"', search_arch)
        list_view = self.env.ref(
            "account_reconcile_payment_inquiry.payment_inquiry_view_list"
        )
        form_view = self.env.ref(
            "account_reconcile_payment_inquiry.payment_inquiry_view_form"
        )
        self.assertIn(
            "payment_inquiry_note",
            self.acc_bank_stmt_line_model.with_user(self.sales_admin_user).get_view(
                view_id=list_view.id, view_type="list"
            )["arch"],
        )
        self.assertIn(
            "action_payment_inquiry_answer",
            self.acc_bank_stmt_line_model.with_user(self.sales_admin_user).get_view(
                view_id=form_view.id, view_type="form"
            )["arch"],
        )

    @mute_logger("odoo.addons.mail.models.mail_mail")
    def test_payment_inquiry_widget_view(self):
        """The widget of the accountant shows the button and the answer."""
        line = self._create_bank_stmt_line()
        reconcile_view = self.env.ref(
            "account_reconcile_oca.bank_statement_line_form_reconcile_view"
        )
        with Form(
            line.with_user(self.accountant_user), view=reconcile_view
        ) as line_form:
            # the button is available: the record is loaded with its fields
            self.assertEqual(line_form.payment_inquiry_state, False)
        line.with_user(self.accountant_user).action_payment_inquiry_ask()
        line.with_user(self.sales_admin_user).write({"payment_inquiry_note": "Answer"})
        line.with_user(self.sales_admin_user).action_payment_inquiry_answer()
        arch = self.acc_bank_stmt_line_model.with_user(self.accountant_user).get_view(
            view_id=reconcile_view.id, view_type="form"
        )["arch"]
        self.assertIn('name="action_payment_inquiry_ask"', arch)
        self.assertIn('name="payment_inquiry_note"', arch)
        # a request waiting for an answer can be followed up and the
        # transaction displays a banner during that time
        self.assertIn('string="Ask for Identification"', arch)
        self.assertIn('string="Ask for Identification Again"', arch)
        self.assertIn(
            "The Sales Administration has been asked to identify this payment "
            "and has not answered yet.",
            arch,
        )
