# Copyright (c) 2026, MISL Holdings (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ExpenseManagementSettings(Document):
	pass


def is_override_gl_enabled():
	try:
		if not getattr(frappe, "db", None):
			return False
		if not frappe.db.exists("DocType", "Expense Management Settings"):
			return False
		return bool(
			frappe.db.get_single_value(
				"Expense Management Settings",
				"is_override_general_ledger_with_custom_format",
			)
		)
	except Exception:
		return False
