# Copyright (c) 2024, Technical Team and contributors
# For license information, please see license.txt

import unittest
import frappe
from frappe.utils import today, flt


class TestExpense(unittest.TestCase):
	def setUp(self):
		# Create test expense type
		if not frappe.db.exists("Expense Type", "Test Expense"):
			expense_type = frappe.get_doc({
				"doctype": "Expense Type",
				"expense_type_name": "Test Expense",
				"description": "Test expense type for unit testing",
				"is_active": 1
			})
			expense_type.insert()
	
	def test_expense_creation(self):
		"""Test basic expense creation"""
		expense = frappe.get_doc({
			"doctype": "Expense",
			"naming_series": "EXP-.YYYY.-",
			"expense_date": today(),
			"company": frappe.defaults.get_defaults().company,
			"description": "Test expense for office supplies",
			"payment_account": self.get_cash_account(),
			"payment_mode": "Cash",
			"remarks": "Test remarks",
			"expense_items": [
				{
					"expense_type": "Test Expense",
					"expense_account": self.get_expense_account(),
					"description": "Office supplies",
					"amount": 500
				},
				{
					"expense_type": "Test Expense",
					"expense_account": self.get_expense_account(),
					"description": "Stationery",
					"amount": 500
				}
			]
		})
		
		expense.insert()
		self.assertTrue(expense.name)
		self.assertEqual(expense.docstatus, 0)
		self.assertEqual(flt(expense.total_amount), 1000)
	
	def test_gl_entries_preview(self):
		"""Test GL entries preview functionality"""
		expense = self.create_test_expense()
		gl_entries = expense.preview_gl_entries()
		
		self.assertEqual(len(gl_entries), 2)  # One debit, one credit
		
		# Check total debits and credits
		total_debit = sum(flt(entry.get("debit", 0)) for entry in gl_entries)
		total_credit = sum(flt(entry.get("credit", 0)) for entry in gl_entries)
		
		self.assertEqual(total_debit, 1000)
		self.assertEqual(total_credit, 1000)
	
	def test_expense_submission(self):
		"""Test expense submission and GL entry creation"""
		expense = self.create_test_expense()
		expense.submit()
		
		# Check if GL entries are created
		gl_entries = frappe.get_all("GL Entry", 
			filters={"voucher_no": expense.name, "voucher_type": "Expense"},
			fields=["account", "debit", "credit"]
		)
		
		self.assertEqual(len(gl_entries), 2)
		
		# Check total debits and credits
		total_debit = sum(flt(entry.debit) for entry in gl_entries)
		total_credit = sum(flt(entry.credit) for entry in gl_entries)
		
		self.assertEqual(total_debit, 1000)
		self.assertEqual(total_credit, 1000)
	
	def create_test_expense(self):
		"""Create a test expense document"""
		expense = frappe.get_doc({
			"doctype": "Expense",
			"naming_series": "EXP-.YYYY.-",
			"expense_date": today(),
			"company": frappe.defaults.get_defaults().company,
			"description": "Test expense for office supplies",
			"payment_account": self.get_cash_account(),
			"payment_mode": "Cash",
			"expense_items": [
				{
					"expense_type": "Test Expense",
					"expense_account": self.get_expense_account(),
					"description": "Office supplies",
					"amount": 600
				},
				{
					"expense_type": "Test Expense", 
					"expense_account": self.get_expense_account(),
					"description": "Stationery",
					"amount": 400
				}
			]
		})
		expense.insert()
		return expense
	
	def get_expense_account(self):
		"""Get a test expense account"""
		company = frappe.defaults.get_defaults().company
		account = frappe.get_all("Account", 
			filters={
				"company": company,
				"account_type": "Expense Account",
				"is_group": 0
			},
			limit=1
		)
		return account[0].name if account else None
	
	def get_cash_account(self):
		"""Get a test cash account"""
		company = frappe.defaults.get_defaults().company
		account = frappe.get_all("Account", 
			filters={
				"company": company,
				"account_type": "Cash",
				"is_group": 0
			},
			limit=1
		)
		return account[0].name if account else None