# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright 2012 Camptocamp SA (Guewen Baconnier)
#    Copyright (C) 2010   Sébastien Beau
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

{
    "name" : "Easy Reconcile",
    "version" : "1.0",
    "depends" : ["account", "base_scheduler_creator"
                ],
    "author" : "Sébastien Beau",
    "description": """A new view to reconcile easily your account
""",
    "website" : "http://www.akretion.com/",
    "category" : "Customer Modules",
    "init_xml" : [],
    "demo_xml" : [],
    "update_xml" : ["easy_reconcile.xml"],
    'license': 'AGPL-3',
    "auto_install": False,
    "installable": True,

}
