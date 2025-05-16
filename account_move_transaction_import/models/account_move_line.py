# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)
from odoo import fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    transaction_id = fields.Many2one("payment.transaction")
