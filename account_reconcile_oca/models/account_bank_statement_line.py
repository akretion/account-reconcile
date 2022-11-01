# Copyright 2022 CreuBlanca
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.tools import float_is_zero


class AccountBankStatementLine(models.Model):

    _inherit = "account.bank.statement.line"

    reconcile_data_info = fields.Serialized(
        compute="_compute_reconcile_data_info", inverse="_inverse_reconcile_data_info"
    )
    reconcile_data = fields.Serialized()
    manual_reference = fields.Char(store=False, default=False)
    manual_account_id = fields.Many2one(
        "account.account", check_company=True, store=False, default=False
    )
    manual_name = fields.Char(store=False, default=False)
    manual_amount = fields.Monetary(store=False, default=False)
    reconcile_auxiliary_id = fields.Integer(store=False, default=1)

    @api.onchange("manual_account_id", "manual_name", "manual_amount")
    def _onchange_manual_reconcile_vals(self):
        self.ensure_one()
        data = self.reconcile_data_info["data"]
        total_amount = 0.0
        suspense_line = None
        for line in data:
            if line["reference"] == self.manual_reference:
                line.update(
                    {
                        "name": self.manual_name,
                        "account_id": self.manual_account_id.name_get()[0],
                        "amount": self.manual_amount,
                        "credit": -self.manual_amount
                        if self.manual_amount < 0
                        else 0.0,
                        "debit": self.manual_amount if self.manual_amount > 0 else 0.0,
                        "kind": line["kind"] if line["kind"] != "suspense" else "other",
                    }
                )
            if line["kind"] == "suspense":
                suspense_line = line
            total_amount += line["amount"]
        if not float_is_zero(
            total_amount, precision_digits=self.currency_id.decimal_places
        ):
            if suspense_line:
                suspense_amount = suspense_line["amount"] - total_amount
                suspense_line.update(
                    {
                        "amount": -suspense_amount,
                        "credit": -suspense_amount if suspense_amount < 0 else 0.0,
                        "debit": suspense_amount if suspense_amount > 0 else 0.0,
                    }
                )
            else:
                data.append(
                    {
                        "reference": "reconcile_auxiliary;%s"
                        % self.reconcile_auxiliary_id,
                        "id": False,
                        "account_id": self.journal_id.suspense_account_id.name_get()[0],
                        "partner_id": self.partner_id
                        and self.partner_id.name_get()[0]
                        or False,
                        "date": fields.Date.to_string(self.date),
                        "name": self.name,
                        "amount": -total_amount,
                        "credit": total_amount if total_amount > 0 else 0.0,
                        "debit": -total_amount if total_amount < 0 else 0.0,
                        "kind": "suspense",
                    }
                )
                self.reconcile_auxiliary_id += 1
        self.reconcile_data_info = {"data": data}

    @api.depends("reconcile_data")
    def _compute_reconcile_data_info(self):
        for record in self:
            if record.reconcile_data:
                record.reconcile_data_info = record.reconcile_data
            else:
                record.reconcile_data_info = record._default_reconcile_data()

    def _inverse_reconcile_data_info(self):
        for record in self:
            record.reconcile_data = record.reconcile_data_info

    def _default_reconcile_data(self):
        liquidity_lines, suspense_lines, other_lines = self._seek_for_lines()
        return {
            "data": [
                self._get_reconcile_line(line, "liquidity") for line in liquidity_lines
            ]
            + [self._get_reconcile_line(line, "other") for line in other_lines]
            + [self._get_reconcile_line(line, "suspense") for line in suspense_lines]
        }

    def clean_reconcile(self):
        self.reconcile_data_info = self._default_reconcile_data()
        self.reconcile_data = {}

    def _get_reconcile_line(self, line, kind):
        return {
            "reference": "account.move.line;%s" % line.id,
            "id": line.id,
            "account_id": line.account_id.name_get()[0],
            "partner_id": line.partner_id and line.partner_id.name_get()[0] or False,
            "date": fields.Date.to_string(line.date),
            "name": line.name,
            "debit": line.debit,
            "credit": line.credit,
            "amount": line.debit - line.credit,
            "kind": kind,
        }

    def reconcile_bank_line(self):
        self.ensure_one()
        self.reconcile_data = self.reconcile_data_info
        _liquidity_lines, suspense_lines, other_lines = self._seek_for_lines()
        lines_to_remove = [(2, line.id) for line in suspense_lines + other_lines]

        # Cleanup previous lines.
        move = self.move_id
        container = {"records": move, "self": move}
        with move._check_balanced(container):
            move.with_context(
                skip_account_move_synchronization=True, force_delete=True
            ).write(
                {
                    "line_ids": lines_to_remove,
                }
            )
            for line_vals in self.reconcile_data_info["data"]:
                if line_vals["kind"] == "liquidity":
                    continue
                line = (
                    self.env["account.move.line"]
                    .with_context(check_move_validity=False)
                    .create(self._reconcile_move_line_vals(line_vals))
                )
                if line_vals.get("counterpart_line_id"):
                    (
                        self.env["account.move.line"].browse(
                            line_vals.get("counterpart_line_id")
                        )
                        + line
                    ).reconcile()

    def _reconcile_move_line_vals(self, line):
        return {
            "move_id": self.move_id.id,
            "account_id": line["account_id"][0],
            "partner_id": line["partner_id"] and line["partner_id"][0],
            "credit": line["credit"],
            "debit": line["debit"],
        }
