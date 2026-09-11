# Copyright 2026 Akretion (https://www.akretion.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    "name": "Sale Order Payment Reconciliation",
    "summary": "Pay sale orders from the OCA bank reconciliation, "
    "with or without invoicing",
    "version": "18.0.1.0.0",
    "development_status": "Beta",
    "category": "Accounting",
    "website": "https://github.com/OCA/account-reconcile",
    "author": "Akretion,Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "depends": [
        "account_reconcile_sale_order",
        "sale_order_payment",
        "mail",
    ],
    "data": [
        "data/account_reconcile_model.xml",
        "data/mail_activity_data.xml",
        "views/res_config_settings_views.xml",
    ],
    "demo": [],
    "installable": True,
    "auto_install": False,
}
