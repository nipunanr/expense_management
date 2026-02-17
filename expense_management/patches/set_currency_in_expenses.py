import frappe
from erpnext.accounts.utils import get_account_currency


def execute():
	"""Set currency for existing expenses based on payment account"""
	expenses = frappe.get_all("Expense", filters={"currency": ["is", "not set"]}, fields=["name", "payment_account", "company"])
	
	for expense in expenses:
		try:
			if expense.payment_account:
				currency = get_account_currency(expense.payment_account)
			else:
				# Fallback to company currency
				currency = frappe.get_cached_value("Company", expense.company, "default_currency")
			
			frappe.db.set_value("Expense", expense.name, {
				"currency": currency,
				"exchange_rate": 1.0
			}, update_modified=False)
			
		except Exception as e:
			frappe.log_error(f"Error setting currency for Expense {expense.name}: {str(e)}")
	
	frappe.db.commit()
	print(f"Updated {len(expenses)} expenses with currency")
