# Copyright 2011-2019 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)
{
    "name": "Journal Entry Transaction Completion",
    "version": "14.0.1.0.0",
    "author": "Akretion,Odoo Community Association (OCA)",
    "maintainers": ["florian-dacosta"],
    "category": "Finance",
    "complexity": "easy",
    "depends": ["account_move_base_import", "payment"],
    "website": "https://github.com/OCA/account-reconcile",
    "data": [
        "data/account_move_completion_rule.xml",
        "views/payment_acquirer.xml",
        "views/account_move_line.xml",
    ],
    "installable": True,
    "auto_install": True,
    "license": "AGPL-3",
}
