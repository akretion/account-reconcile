# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)


from odoo import api, fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    transaction_id = fields.Char(
        compute="_compute_transaction_id",
        store=True,
        readonly=False,
        copy=False,
        index="btree",
        help="Transaction id from the financial institute",
    )

    @api.depends("move_id.transaction_id")
    def _compute_transaction_id(self):
        for aml in self.filtered(lambda line: line.display_type == "payment_term"):
            aml.transaction_id = aml.move_id.transaction_id
