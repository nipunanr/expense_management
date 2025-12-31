# Copyright (c) 2024, Technical Team and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ExpenseItem(Document):
	# this is a child doctype, the permissions are controlled by the parent doctype
	pass