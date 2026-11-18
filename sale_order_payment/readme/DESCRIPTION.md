This module adds link between sale orders and account move lines of payment.
It also reconciles automatically the invoices with the payments registered on
the sale order they come from. An invoice covering only a part of the sale
order is partially reconciled with the corresponding part of the payment, the
rest of the payment staying available for the other invoices of the order.

When the sale order is fully invoiced, the reconciliation is only done if the
amount paid on the order matches the amount invoiced: a difference between the
payment and the invoiced amount is not reconciled automatically.

The paid amount of the sale order is displayed below its total amount.

Two filters of the sale orders list point out the payments and the refunds which
are not reconciled yet (*Unallocated Payment*, *Unallocated Refund*): the money
received or refunded on the order still has to be assigned to an invoice or to a
credit note.
