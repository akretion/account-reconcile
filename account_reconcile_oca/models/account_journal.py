# Copyright 2022 CreuBlanca
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    def action_open_reconcile_to_check(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "account_reconcile_oca.action_bank_statement_line_reconcile"
        )
        action["domain"] = [("id", "=", self.to_check_ids().ids)]
        return action
