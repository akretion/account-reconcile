# -*- coding: utf-8 -*-
# © 2011-2018 Camptocamp SA
# © 2019 Akretion
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import fields
from odoo.tests.common import TransactionCase


class TestTransactionid(TransactionCase):

    def setUp(self):
        super(TestTransactionid, self).setUp()
        self.journal = self.env['account.journal'].search(
            [('type', '=', 'bank')], limit=1)
        self.invoice = self.env['account.invoice'].create({
            'company_id': self.env.ref('base.main_company').id,
            'currency_id': self.env.ref('base.EUR').id,
            'partner_id': self.env.ref('base.res_partner_2').id,
            'journal_id': self.journal.id,
            'transaction_id': 'XXX77Z',
        })
        self.completion_rule = self.ref(
            'account_move_transactionid_import.'
            'bank_statement_completion_rule_trans_id_invoice')
        self.journal.write({
            'used_for_completion': True,
            'rule_ids': [(6, 0, [self.completion_rule])]
        })
        self.move = self.env['account.move'].create({
            "date": fields.Date.today(),
            "journal_id": self.journal.id
        })
        self.account = self.env['account.account'].search(
            [('user_type_id.type', '=', 'liquidity')], limit=1)

    def test_invoice_open(self):
        self.env['account.invoice.line'].create({
            'invoice_id': self.invoice.id,
            'product_id': self.env.ref('product.product_product_3').id,
            'uom_id': self.env.ref('product.product_uom_unit').id,
            'quantity': 1.0,
            'price_unit': 450.0,
            'name': '[PCSC234] PC Assemble SC234',
            'account_id': self.account.id,
        })
        self.invoice.action_invoice_open()
        self.assertEqual('open', self.invoice.state)

    def test_completion_invoice_transactionid(self):
        self.move_line = self.env['account.move.line'].create({
            'name': 'Test autocompletion on invoice with transac ID',
            'account_id': self.account.id,
            'move_id': self.move.id,
            'transaction_ref': 'XXX77Z',
            'date_maturity': fields.Date.today(),
            'credit': 0.0,
        })
        self.move_line.with_context(check_move_validity=False).write({
            'credit': 450.0,
        })
        self.move.button_auto_completion()
        self.assertEqual('Agrolait', self.move_line.partner_id.name)
