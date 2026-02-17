# Copyright (c) 2024, Technical Team and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, getdate
from erpnext.accounts.general_ledger import make_gl_entries
from erpnext.accounts.utils import get_account_currency


class Expense(Document):
	def validate(self):
		"""Validate Expense before save"""
		self.set_currency()
		self.validate_expense_items()
		self.validate_payment_account()
		self.validate_currency()
		self.validate_expense_date()
		self.set_exchange_rate()
		self.calculate_total_amount()
	
	def set_currency(self):
		"""Set currency from payment account"""
		if self.payment_account:
			self.currency = get_account_currency(self.payment_account)
	
	def set_exchange_rate(self):
		"""Set exchange rate if currency is different from company currency"""
		if not self.currency:
			return
		
		company_currency = frappe.get_cached_value("Company", self.company, "default_currency")
		
		if self.currency == company_currency:
			self.exchange_rate = 1.0
		elif not self.exchange_rate or self.exchange_rate == 0:
			# Get exchange rate from system
			from erpnext.setup.utils import get_exchange_rate
			self.exchange_rate = get_exchange_rate(self.currency, company_currency, self.expense_date)
	
	def validate_currency(self):
		"""Validate that all accounts have the same currency"""
		if not self.payment_account:
			return
		
		payment_currency = get_account_currency(self.payment_account)
		
		for item in self.expense_items:
			if not item.expense_account:
				continue
			
			expense_currency = get_account_currency(item.expense_account)
			
			if expense_currency != payment_currency:
				frappe.throw(
					f"Row {item.idx}: Expense Account currency ({expense_currency}) must match "
					f"Payment Account currency ({payment_currency})"
				)
		
	def validate_expense_items(self):
		"""Validate expense items"""
		if not self.expense_items:
			frappe.throw("Please add at least one expense item")
		
		for item in self.expense_items:
			# Validate required fields
			if not item.expense_account:
				frappe.throw(f"Row {item.idx}: Expense Account is required")
			
			if not item.amount or flt(item.amount) <= 0:
				frappe.throw(f"Row {item.idx}: Amount must be greater than zero")
			
			# Validate expense account
			expense_account = frappe.get_doc("Account", item.expense_account)
			if expense_account.account_type not in ["Expense Account", "Cost of Goods Sold"]:
				frappe.throw(f"Row {item.idx}: Expense Account must be an Expense Account or Cost of Goods Sold account")
			
			# Validate company consistency
			if expense_account.company != self.company:
				frappe.throw(f"Row {item.idx}: Expense Account must belong to company {self.company}")
			
			# Set default description if not provided
			if not item.description and item.expense_type:
				expense_type_doc = frappe.get_doc("Expense Type", item.expense_type)
				item.description = expense_type_doc.name
			elif not item.description:
				item.description = expense_account.account_name or "Expense"
	
	def validate_payment_account(self):
		"""Validate payment account"""
		payment_account = frappe.get_doc("Account", self.payment_account)
		if payment_account.account_type not in ["Cash", "Bank"]:
			frappe.throw(f"Payment Account must be a Cash or Bank account")
		
		# Validate company consistency
		if payment_account.company != self.company:
			frappe.throw(f"Payment Account must belong to company {self.company}")
	
	def validate_expense_date(self):
		"""Validate expense date"""
		if getdate(self.expense_date) > getdate():
			frappe.throw("Expense Date cannot be in the future")
	
	def calculate_total_amount(self):
		"""Calculate total amount from expense items"""
		self.total_amount = sum(flt(item.amount) for item in self.expense_items)
	
	def calculate_total(self):
		"""Alias for calculate_total_amount for backward compatibility"""
		return self.calculate_total_amount()
	
	def on_submit(self):
		"""Create GL Entries on submission"""
		self.validate_for_submission()
		self.make_gl_entries()
		self.add_comment('Info', f'Expense submitted for amount {frappe.format_value(self.total_amount, "Currency")}')
	
	def before_cancel(self):
		"""Reverse GL Entries before cancellation"""
		self.ignore_linked_doctypes = ("GL Entry",)
		self.make_gl_entries(cancel=True)
	
	def on_cancel(self):
		"""Final actions on cancellation"""
		self.validate_for_cancellation()
		self.add_comment('Info', f'Expense cancelled for amount {frappe.format_value(self.total_amount, "Currency")}')
	
	def validate_for_submission(self):
		"""Additional validations before submission"""
		# Note: docstatus validation is handled by framework
		if not self.expense_items:
			frappe.throw("Cannot submit expense without expense items")
		
		if flt(self.total_amount) <= 0:
			frappe.throw("Cannot submit expense with zero or negative amount")
	
	def validate_for_cancellation(self):
		"""Additional validations before cancellation"""
		# Note: docstatus validation is handled by framework
		# Check if there are any dependent transactions
		# This can be extended to check for payment entries, journal entries etc.
		pass
		dependent_docs = self.get_dependent_documents()
		if dependent_docs:
			frappe.throw(f"Cannot cancel expense. Dependent documents exist: {', '.join(dependent_docs)}")
	
	def get_dependent_documents(self):
		"""Get list of dependent documents that prevent cancellation"""
		dependent_docs = []
		
		# Check for payment entries referencing this expense
		payment_entries = frappe.get_all("Payment Entry Reference", 
			filters={"reference_doctype": "Expense", "reference_name": self.name},
			fields=["parent"])
		
		if payment_entries:
			dependent_docs.extend([pe.parent for pe in payment_entries])
		
		# Check for journal entries referencing this expense
		journal_entries = frappe.get_all("Journal Entry Account", 
			filters={"reference_type": "Expense", "reference_name": self.name},
			fields=["parent"])
		
		if journal_entries:
			dependent_docs.extend([je.parent for je in journal_entries])
		
		return list(set(dependent_docs))  # Remove duplicates
	
	def make_gl_entries(self, cancel=False, adv_adj=False):
		"""Create General Ledger Entries"""
		try:
			gl_entries = self.get_gl_entries()
			
			if gl_entries:
				from erpnext.accounts.general_ledger import make_gl_entries
				make_gl_entries(gl_entries, cancel=cancel, adv_adj=adv_adj, merge_entries=False)
				
				if cancel:
					frappe.msgprint(f"GL Entries cancelled for Expense {self.name}")
				else:
					frappe.msgprint(f"GL Entries created for Expense {self.name}")
			else:
				frappe.throw("No GL Entries to process")
				
		except Exception as e:
			frappe.log_error(f"Error in GL Entries for Expense {self.name}: {str(e)}")
			frappe.throw(f"Failed to process GL Entries: {str(e)}")
	
	def get_gl_entries(self):
		"""Get GL Entries for this expense"""
		from erpnext.accounts.utils import get_account_currency
		
		gl_entries = []
		
		# Check if expense_items exists and has data
		if not hasattr(self, 'expense_items') or not self.expense_items:
			frappe.throw("No expense items found. Please add at least one expense item.")
		
		# Get company's default cost center and currency
		cost_center = frappe.get_cached_value("Company", self.company, "cost_center")
		company_currency = frappe.get_cached_value("Company", self.company, "default_currency")
		
		# Group expense items by account to consolidate GL entries
		account_wise_totals = {}
		
		for item in self.expense_items:
			# Handle both dict and object types for child table items
			if isinstance(item, dict):
				expense_account = item.get('expense_account')
				amount = item.get('amount', 0)
				idx = item.get('idx', 0)
			else:
				expense_account = getattr(item, 'expense_account', None)
				amount = getattr(item, 'amount', 0)
				idx = getattr(item, 'idx', 0)
			
			if not expense_account:
				frappe.throw(f"Row {idx}: Expense Account is required")
			
			if expense_account not in account_wise_totals:
				account_wise_totals[expense_account] = 0
			account_wise_totals[expense_account] += flt(amount)
		
		# Calculate amounts in company currency
		exchange_rate = flt(self.exchange_rate) if self.exchange_rate else 1.0
		
		# Create debit entries for each expense account
		for account, amount in account_wise_totals.items():
			amount_in_company_currency = flt(amount) * exchange_rate
			
			gl_entries.append(
				frappe._dict({
					"account": account,
					"party_type": None,
					"party": None,
					"debit": amount_in_company_currency,
					"credit": 0,
					"debit_in_account_currency": flt(amount),
					"credit_in_account_currency": 0,
					"account_currency": self.currency,
					"against": self.payment_account,
					"voucher_type": self.doctype,
					"voucher_no": self.name,
					"posting_date": self.expense_date,
					"company": self.company,
					"remarks": self.description or "Expense Entry",
					"cost_center": cost_center,
					"project": None,
					"finance_book": None
				})
			)
		
		# Create single credit entry for payment account
		total_in_company_currency = flt(self.total_amount) * exchange_rate
		
		gl_entries.append(
			frappe._dict({
				"account": self.payment_account,
				"party_type": None,
				"party": None,
				"debit": 0,
				"credit": total_in_company_currency,
				"debit_in_account_currency": 0,
				"credit_in_account_currency": flt(self.total_amount),
				"account_currency": self.currency,
				"against": ", ".join(account_wise_totals.keys()),
				"voucher_type": self.doctype,
				"voucher_no": self.name,
				"posting_date": self.expense_date,
				"company": self.company,
				"remarks": self.description or "Expense Payment",
				"cost_center": cost_center,
				"project": None,
				"finance_book": None
			})
		)
		
		return gl_entries
	
	@frappe.whitelist()
	def preview_gl_entries(self):
		"""Preview GL Entries before submission"""
		try:
			# Basic validations
			if not self.company:
				frappe.throw("Company is required")
			
			if not self.payment_account:
				frappe.throw("Payment Account is required")
			
			if not self.expense_date:
				frappe.throw("Expense Date is required")
			
			# Calculate total and get GL entries
			self.calculate_total()
			gl_entries = self.get_gl_entries()
			
			# Format for display
			formatted_entries = []
			for entry in gl_entries:
				formatted_entries.append({
					"account": entry.account,
					"debit": flt(entry.debit, 2),
					"credit": flt(entry.credit, 2),
					"against": entry.against,
					"remarks": entry.remarks
				})
			
			return formatted_entries
			
		except Exception as e:
			frappe.throw(f"Error generating GL entries preview: {str(e)}")
			return []

@frappe.whitelist()
def get_expense_account_from_type(expense_type):
	"""Get default expense account from expense type"""
	if not expense_type:
		return None
	
	expense_type_doc = frappe.get_doc("Expense Type", expense_type)
	return expense_type_doc.default_account

@frappe.whitelist()
def get_account_currency_for_expense(account):
	"""Get account currency - whitelisted method for client-side calls"""
	if not account:
		return None
	
	from erpnext.accounts.utils import get_account_currency
	return get_account_currency(account)

@frappe.whitelist()
def get_company_default_currency(company):
	"""Get company default currency - whitelisted method for client-side calls"""
	if not company:
		return None
	
	return frappe.get_cached_value("Company", company, "default_currency")