# Copyright 2026 Akretion (https://www.akretion.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class AccountReconcileModel(models.Model):
    _inherit = "account.reconcile.model"

    sale_order_matching_transaction_id = fields.Boolean(
        string="Match transaction IDs",
        help="Compare the reference of the statement line with the Transaction ID "
        "of the sales orders and offer the matching sales order as reconciliation "
        "counterpart.",
    )

    def _get_candidates_sale_order_best_match(
        self, bank_statement_line, partner, excluded_ids
    ):
        """Look for a sales order by transaction ID before the other criteria.

        A transaction ID identifies the payment of a single sales order; when
        the option is activated on the rule, the reference of the statement line
        is compared to the transaction ID of the sales orders (case insensitive
        exact match).
        """
        self.ensure_one()
        if self.sale_order_matching_transaction_id:
            candidate = self._get_sale_order_by_transaction_id(
                bank_statement_line, partner, excluded_ids
            )
            if candidate:
                return candidate
        return super()._get_candidates_sale_order_best_match(
            bank_statement_line, partner, excluded_ids
        )

    def _get_sale_order_by_transaction_id(
        self, bank_statement_line, partner, excluded_ids
    ):
        """Return the first sales order whose transaction ID matches the
        reference of the statement line.

        The reference is compared as a whole first. Then, when *Match tokens* is
        activated, each significant word of the reference (long enough according
        to *Minimum token length*) is compared to the transaction ID as well, as
        the transaction ID may be part of a longer label. The tokens are
        compared exactly first, then partially, like the name of the sales
        orders is matched.
        """

        def search(value, operator="=ilike"):
            return self.env["sale.order"].search(
                self._get_sale_orders_for_bank_statement_line_domain(
                    bank_statement_line,
                    partner,
                    excluded_ids=excluded_ids,
                    extra_domain=[("transaction_id", operator, value)],
                ),
                limit=1,
            )

        ref = bank_statement_line.payment_ref or ""
        if not ref:
            return self.env["sale.order"]
        candidate = search(ref)
        if candidate or not self.sale_order_matching_token_match:
            return candidate
        tokens = [
            token
            for token in ref.split()
            if len(token) >= self.sale_order_matching_token_length
        ]
        for operator in ("=ilike", "ilike"):
            for token in tokens:
                candidate = search(token, operator)
                if candidate:
                    return candidate
        return self.env["sale.order"]
