This module improves account_reconcile_sale_order to allow to add payments (account move line) on sale order from reconciliation interface instead of generating the invoice directly.

When a sale order is marked as paid that way, an email is sent (using the mail
template *Sale Order Paid: Notify the Salesperson*) so that the order can be
invoiced, the payment being reconciled with the invoice later on. The
recipients of the email are configured on the mail template (the salesperson of
the order by default).

The notification can be disabled on a journal with the option *Notify Paid Sale
Orders*: it is meant for the journals fed by an automated import which
reconciles the transactions automatically (for example a PayPal import).
