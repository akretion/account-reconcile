This module adds link between sale orders and account move lines of payment.
It also reconciles automatically the invoices with the payments registered on
the sale order they come from. An invoice covering only a part of the sale
order is partially reconciled with the corresponding part of the payment, the
rest of the payment staying available for the other invoices of the order.

When the sale order is fully invoiced, the reconciliation is only done if the
amount paid on the order matches the amount invoiced: a difference between the
payment and the invoiced amount is not reconciled automatically, because it
reveals an inconsistency (a wrong amount on the payment for example) which
must be fixed manually.
