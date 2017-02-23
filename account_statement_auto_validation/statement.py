# -*- coding: utf-8 -*-
###############################################################################
#
#   account_statement_auto_validation for OpenERP
#   Copyright (C) 2013-TODAY Akretion <http://www.akretion.com>.
#   @author Sébastien BEAU <sebastien.beau@akretion.com>
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as
#   published by the Free Software Foundation, either version 3 of the
#   License, or (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################

from openerp.osv import osv, fields
import logging
_logger = logging.getLogger(__name__)
import sys
import traceback



class account_statement_profile(osv.Model):
    _inherit = "account.statement.profile"

    _columns = {
       'launch_auto_validation': fields.boolean("Launch Auto Validation after import",
               help="Tic that box to automatically launch the validation on each imported\
               file using this profile."),
    }

    def statement_import(self, cr, uid, ids, profile_id, file_stream, ftype="csv", context=None):
        statement_ids = super(account_statement_profile, self).statement_import(cr, uid, ids, profile_id, file_stream, ftype=ftype, context=context)
        prof = self.browse(cr, uid, profile_id, context=context)
        if prof.launch_auto_validation:
            bk_line_obj = self.pool['account.bank.statement.line']
            uncompleted_lines = bk_line_obj.search(cr, uid, [
                                        ('statement_id', 'in', statement_ids),
                                        ('already_completed', '=', False),
                                        ], context=context)
            if not uncompleted_lines:
                cr.execute('SAVEPOINT validate_bank_statement')
                try:
                    self.pool['account.bank.statement'].button_confirm_bank(cr, uid, statement_ids, context)
                except Exception, exc:
                    error_type, error_value, trbk = sys.exc_info()
                    st = "Error: %s\nDescription: %s\nTraceback:" % (error_type.__name__, error_value)
                    st += ''.join(traceback.format_tb(trbk, 30))
                    _logger.error('fail to validate bank statement : %s, error: %s'%(statement_ids, st))
                    cr.execute('ROLLBACK TO SAVEPOINT validate_bank_statement')
                else:
                    cr.execute('RELEASE SAVEPOINT validate_bank_statement')
        return statement_ids


