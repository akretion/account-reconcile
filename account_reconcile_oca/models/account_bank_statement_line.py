# Copyright 2022 CreuBlanca
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.tools import float_is_zero


class AccountBankStatementLine(models.Model):

    _inherit = "account.bank.statement.line"

    reconcile_data_info = fields.Serialized(
        compute="_compute_reconcile_data_info",
        inverse="_inverse_reconcile_data_info",
        prefetch=False,
    )
    reconcile_data = fields.Serialized()
    manual_reference = fields.Char(store=False, default=False, prefetch=False)
    manual_account_id = fields.Many2one(
        "account.account",
        check_company=True,
        store=False,
        default=False,
        prefetch=False,
    )
    manual_name = fields.Char(store=False, default=False, prefetch=False)
    manual_amount = fields.Monetary(store=False, default=False, prefetch=False)
    add_account_move_line_id = fields.Many2one(
        "account.move.line",
        check_company=True,
        store=False,
        default=False,
        prefetch=False,
        domain=[
            ("parent_state", "=", "posted"),
            ("amount_residual", "!=", 0),
            ("account_id.reconcile", "=", True),
        ],
        context={
            "tree_view_ref": "account_reconcile_oca.account_move_line_tree_reconcile_view",
            "search_view_ref": "account_reconcile_oca.account_move_line_search_reconcile_view",
        },
    )
    reconcile_auxiliary_id = fields.Integer(
        store=False,
        default=1,
        prefetch=False,
    )

    def save(self):
        # TODO: Launch a refresh of data....
        return {"type": "ir.actions.act_window_close"}

    @api.model
    def action_new_line(self):
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "account_reconcile_oca.action_bank_statement_line_create"
        )
        action["context"] = self.env.context
        return action

    @api.onchange("add_account_move_line_id")
    def _onchange_add_account_move_line_id(self):
        if self.add_account_move_line_id:
            data = self.reconcile_data_info["data"]
            new_data = []
            is_new_line = True
            pending_amount = 0.0
            for line in data:
                if line["kind"] != "suspense":
                    pending_amount += line["amount"]
                if line.get("counterpart_line_id") == self.add_account_move_line_id.id:
                    is_new_line = False
                else:
                    new_data.append(line)
            if is_new_line:
                new_data.append(
                    self._get_reconcile_line(
                        self.add_account_move_line_id, "other", True, pending_amount
                    )
                )
            self.reconcile_data_info = {"data": self._recompute_suspense_line(new_data)}
            self.add_account_move_line_id = False

    def _recompute_suspense_line(self, data):
        total_amount = 0
        new_data = []
        suspense_line = False
        for line in data:
            if line["kind"] != "suspense":
                new_data.append(line)
                total_amount += line["amount"]
            else:
                suspense_line = line
        if not float_is_zero(
            total_amount, precision_digits=self.currency_id.decimal_places
        ):
            if suspense_line:
                suspense_line.update(
                    {
                        "amount": -total_amount,
                        "credit": total_amount if total_amount > 0 else 0.0,
                        "debit": -total_amount if total_amount < 0 else 0.0,
                    }
                )
            else:
                suspense_line = {
                    "reference": "reconcile_auxiliary;%s" % self.reconcile_auxiliary_id,
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
                self.reconcile_auxiliary_id += 1
            new_data.append(suspense_line)
        return new_data

    @api.onchange("manual_account_id", "manual_name", "manual_amount")
    def _onchange_manual_reconcile_vals(self):
        self.ensure_one()
        data = self.reconcile_data_info.get("data", [])
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
        data = self._recompute_suspense_line(data)
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

    def _get_reconcile_line(self, line, kind, is_counterpart=False, max_amount=False):

        amount = line.debit - line.credit
        if max_amount:
            if amount > max_amount > 0:
                amount = max_amount
            if amount < max_amount < 0:
                amount = max_amount
        if is_counterpart:
            amount = -amount
        vals = {
            "reference": "account.move.line;%s" % line.id,
            "id": line.id,
            "account_id": line.account_id.name_get()[0],
            "partner_id": line.partner_id and line.partner_id.name_get()[0] or False,
            "date": fields.Date.to_string(line.date),
            "name": line.name,
            "debit": amount if amount > 0 else 0.0,
            "credit": -amount if amount < 0 else 0.0,
            "amount": amount,
            "kind": kind,
        }
        if is_counterpart:
            vals["counterpart_line_id"] = line.id
        return vals

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
