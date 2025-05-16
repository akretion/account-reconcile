Payment Transaction in Odoo from credit card Payment Acquirer do generates accounting entries (by generating a Payment) when processed.
Sometimes we do need to import the credit card statement but then the accounting entries would be duplicated.
Some of the reason to import the credit card statement : 
- Generating a counterpart of multiple payments in order to ease the bank statement reconciliation
- Make sure all payment are registered in the accounting. (If you do some refund or payment operation outside Odoo you will still have it in your odoo accounting)

This module allows to disable the automatic creation of payment when the transaction is processed (option on the Payment Acquirer).
It adds a completion rule allowing to complete the information of the imported line with the transaction information and link the imported payment with the odoo payment transaction.
It tries to automatically reconcile invoices if linked to a transaction with an imported payment
