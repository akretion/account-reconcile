{
    "name": "Account Reconcile Payment Inquiry",
    "summary": "Ask the Sales Administration to identify unidentified payments",
    "version": "18.0.1.0.0",
    "category": "Accounting",
    "license": "AGPL-3",
    "author": "Akretion,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/account-reconcile",
    "development_status": "Beta",
    "depends": [
        "account_reconcile_oca",
        "mail",
        "sale_management",
    ],
    "data": [
        "security/payment_inquiry_security.xml",
        "security/ir.model.access.csv",
        "views/account_bank_statement_line.xml",
        "views/payment_inquiry_views.xml",
    ],
    "installable": True,
}
