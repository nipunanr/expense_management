# Copyright (c) 2024, Technical Team and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ExpenseType(Document):
	def validate(self):
		"""Validate Expense Type"""
		if not self.expense_type_name:
			frappe.throw("Expense Type Name is required")
		
		# Validate default account if provided
		if self.default_account:
			account = frappe.get_doc("Account", self.default_account)
			if account.account_type not in ["Expense Account", "Cost of Goods Sold", "Fixed Asset", "Current Asset"]:
				frappe.throw(f"Default Account must be an Expense Account, Cost of Goods Sold, Fixed Asset, or Current Asset account")