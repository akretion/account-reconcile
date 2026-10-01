# Copyright 2026 Akretion (https://www.akretion.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import models
from odoo.osv.expression import is_leaf


class AccountReconcileModel(models.Model):
    _inherit = "account.reconcile.model"

    def _get_sale_orders_for_bank_statement_line_domain(
        self,
        bank_statement_line,
        partner=None,
        excluded_ids=None,
        amount=None,
        extra_domain=None,
    ):
        domain = super()._get_sale_orders_for_bank_statement_line_domain(
            bank_statement_line,
            partner,
            excluded_ids=excluded_ids,
            amount=amount,
            extra_domain=extra_domain,
        )
        # in payment mode, we want to consider all sale orders even if already invoiced.
        if self.company_id.account_reconcile_sale_order_mode == "payment":
            return [
                leaf
                for leaf in domain
                if not (is_leaf(leaf) and leaf[0] == "invoice_status")
            ]
        else:
            return domain
