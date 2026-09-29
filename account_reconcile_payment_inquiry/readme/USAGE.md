To use this module, you need to:

* give the technical **Payment Inquiry** group to the Sales Administration
  users,
* set the recipients of the e-mail of the request on the mail template
  **Payment Inquiry: Ask for Identification** (*Settings > Technical > E-mail >
  Templates*),
* in the bank reconciliation widget, click on **Ask for Identification** on a
  transaction which cannot be reconciled: the transaction is flagged, it
  records which user asked for the identification, a banner indicates that an
  answer is expected and the Sales Administration receives an email with the
  details of the transaction,
* if the Sales Administration doesn't answer, click on **Ask for
  Identification Again** on the transaction to follow up on the request,
* the flagged transaction is available in the **Payment Inquiries** menu
  (Sales > Orders) of the Sales Administration users, where they write what
  the payment corresponds to and click on **Answer and Notify**,
* the user who asked for the identification receives the answer in a planned
  activity (To-Do type) on the journal entry of the transaction; the answer is
  then displayed on the transaction in the bank reconciliation widget,
* the transactions waiting for an answer can be hidden from the bank
  reconciliation view with the filter **Hide Payment Inquiries To Answer** of
  its search bar.

The users of the *Payment Inquiry* group can only modify the payment inquiry
fields on the bank transactions: they cannot modify the other information of
the transactions.
