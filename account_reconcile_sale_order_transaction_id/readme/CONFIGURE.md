To configure this module, you need to:

1. Go to Invoicing/Configuration/Reconciliation Models
2. Create a model of type *Rule to match sales orders*
3. Activate *Match transaction IDs* if the sales orders must be matched from
   the transaction ID of the reference of the statement lines
4. Activate *Match tokens* (and adjust *Minimum token length*) if the
   transaction ID is part of a longer reference; each significant word of the
   reference is then compared to the transaction ID
