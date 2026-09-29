# Copyright 2026 Akretion France (https://www.akretion.com/)
# @author: Benoît Guillot <benoit.guillot@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from markupsafe import Markup, escape

from odoo import _, fields, models
from odoo.exceptions import AccessError, UserError


class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    payment_inquiry_state = fields.Selection(
        selection=[
            ("to_answer", "To Answer"),
            ("answered", "Answered"),
        ],
        string="Payment Inquiry",
        readonly=True,
        copy=False,
        help="Use the button 'Ask for Identification' of the bank reconciliation "
        "widget to ask the Sales Administration to identify this payment. The "
        "state remains 'To Answer' until the Sales Administration writes what "
        "the payment corresponds to.",
    )
    payment_inquiry_user_id = fields.Many2one(
        comodel_name="res.users",
        string="Inquiry Asked By",
        readonly=True,
        copy=False,
        help="User who asked for the identification of this payment.",
    )
    payment_inquiry_date = fields.Datetime(
        string="Inquiry Asked On",
        readonly=True,
        copy=False,
    )
    payment_inquiry_note = fields.Text(
        string="Inquiry Answer",
        copy=False,
        help="What this payment corresponds to, written by the Sales "
        "Administration.",
    )
    payment_inquiry_answer_user_id = fields.Many2one(
        comodel_name="res.users",
        string="Inquiry Answered By",
        readonly=True,
        copy=False,
    )
    payment_inquiry_answer_date = fields.Datetime(
        string="Inquiry Answered On",
        readonly=True,
        copy=False,
    )

    def _payment_inquiry_writable_fields(self):
        """Fields the users of the Payment Inquiry group are allowed to modify.

        Those users are not accountants: the write access they get on bank
        transactions coming from the 'Ask for Identification' feature must not
        let them modify the transactions themselves.
        """
        return {
            "payment_inquiry_state",
            "payment_inquiry_user_id",
            "payment_inquiry_date",
            "payment_inquiry_note",
            "payment_inquiry_answer_user_id",
            "payment_inquiry_answer_date",
        }

    def write(self, vals):
        if (
            not self.env.su
            and self.env.user.has_group(
                "account_reconcile_payment_inquiry.group_payment_inquiry"
            )
            and not self.env.user.has_group("account.group_account_basic")
        ):
            unauthorized = set(vals) - self._payment_inquiry_writable_fields()
            if unauthorized:
                raise AccessError(
                    _(
                        "You can only answer payment inquiries: you are not "
                        "allowed to modify the other information of this bank "
                        "transaction (%(fields)s).",
                        fields=", ".join(sorted(unauthorized)),
                    )
                )
        return super().write(vals)

    def action_payment_inquiry_ask(self):
        """Ask the Sales Administration to identify the payment.

        Called by the button 'Ask for Identification' of the bank
        reconciliation widget.
        """
        for line in self:
            line.write(
                {
                    "payment_inquiry_state": "to_answer",
                    "payment_inquiry_user_id": self.env.user.id,
                    "payment_inquiry_date": fields.Datetime.now(),
                    # a new inquiry means the previous answer is obsolete
                    "payment_inquiry_note": False,
                    "payment_inquiry_answer_user_id": False,
                    "payment_inquiry_answer_date": False,
                }
            )
        return True

    def action_payment_inquiry_answer(self):
        """Write what the payment corresponds to and notify the user who asked.

        Called by the button 'Answer and Notify' of the menu Payment Inquiries.
        """
        self.ensure_one()
        if not self.payment_inquiry_note:
            raise UserError(
                _("Please write what this payment corresponds to before answering.")
            )
        if not self.payment_inquiry_user_id:
            raise UserError(_("There is no user to notify for this payment inquiry."))
        self.write(
            {
                "payment_inquiry_state": "answered",
                "payment_inquiry_answer_user_id": self.env.user.id,
                "payment_inquiry_answer_date": fields.Datetime.now(),
            }
        )
        self._payment_inquiry_notify_requester()
        return True

    def _payment_inquiry_notify_requester(self):
        """Notify the user who asked for the identification.

        The notification is a planned activity (and a message in the chatter)
        on the journal entry of the transaction; it is created with sudo()
        because the Sales Administration is not supposed to have access to the
        accounting entries: the activity only carries information for its
        assignee.
        """
        self.ensure_one()
        requester = self.payment_inquiry_user_id
        note = self.payment_inquiry_note or ""
        label = self.payment_ref or self.name or ""
        move = self.move_id.sudo()
        activity = move.activity_schedule(
            act_type_xmlid="mail.mail_activity_data_todo",
            summary=_("Payment identification: %(label)s", label=label),
            note=note,
            user_id=requester.id,
            date_deadline=fields.Date.context_today(self),
        )
        move.message_post(
            body=Markup("<p>%s</p><blockquote>%s</blockquote>")
            % (
                escape(
                    _(
                        "Payment identified by %(user)s - the user who asked for "
                        "the identification receives an activity.",
                        user=self.env.user.name,
                    )
                ),
                escape(note),
            )
        )
        return activity
