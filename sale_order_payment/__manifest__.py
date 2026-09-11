# Copyright 2026 Akretion (https://www.akretion.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    "name": "Sale Order Payment",
    "summary": "Link sale orders to their payment journal items",
    "version": "18.0.1.0.0",
    "development_status": "Beta",
    "category": "Sales",
    "website": "https://github.com/OCA/account-reconcile",
    "author": "Akretion,Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "external_dependencies": {"python": [], "bin": []},
    "depends": [
        "sale",
        "account",
    ],
    "data": [
        "views/sale_order_views.xml",
        "views/account_move_line_views.xml",
    ],
    "demo": [],
    "installable": True,
    "auto_install": False,
}
