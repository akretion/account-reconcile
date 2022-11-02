# Copyright 2022 CreuBlanca
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    def action_open_reconcile(self):
        # Open reconciliation view for bank statements belonging to this journal
        self.ensure_one()
        bank_stmt = self.env["account.bank.statement"].search(
            [("journal_id", "in", self.ids)]
        )
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "account_reconcile_oca.action_bank_statement_line_reconcile"
        )
        action["domain"] = [
            ("statement_id", "in", bank_stmt.ids),
            ("is_reconciled", "=", False),
        ]
        action["context"] = self.env.context.copy()
        action["context"]["default_journal_id"] = self.id
        return action

    def action_open_reconcile_to_check(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "account_reconcile_oca.action_bank_statement_line_reconcile"
        )
        action["domain"] = [("id", "=", self.to_check_ids().ids)]
        return action
