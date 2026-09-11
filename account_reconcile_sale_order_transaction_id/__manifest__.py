# Copyright 2026 Akretion (https://www.akretion.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    "name": "Reconcile sale orders by transaction ID",
    "summary": "Match sale orders from their transaction ID during bank reconciliation",
    "version": "18.0.1.0.0",
    "development_status": "Beta",
    "category": "Accounting",
    "website": "https://github.com/OCA/account-reconcile",
    "author": "Akretion,Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "depends": [
        "account_reconcile_sale_order",
        "base_transaction_id",
    ],
    "data": [
        "data/account_reconcile_model.xml",
        "views/account_reconcile_model.xml",
    ],
    "demo": [],
    "installable": True,
    "auto_install": False,
}
