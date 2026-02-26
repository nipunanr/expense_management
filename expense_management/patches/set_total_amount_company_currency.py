import frappe
from frappe.utils import flt


def execute():
	"""Set total_amount_company_currency for existing expenses"""
	expenses = frappe.get_all(
		"Expense", 
		filters={"docstatus": ["<", 2]},  # Include draft and submitted expenses, exclude cancelled
		fields=["name", "company", "currency", "exchange_rate", "total_amount"]
	)
	
	print(f"Processing {len(expenses)} expense records...")
	
	updated_count = 0
	for expense in expenses:
		try:
			company_currency = frappe.get_cached_value("Company", expense.company, "default_currency")
			
			# Calculate total_amount_company_currency
			if expense.currency == company_currency:
				# If currency is same as company currency, directly use total_amount
				total_amount_company_currency = flt(expense.total_amount)
			else:
				# Use exchange rate to convert to company currency
				exchange_rate = flt(expense.exchange_rate) if expense.exchange_rate else 1.0
				total_amount_company_currency = flt(expense.total_amount) * exchange_rate
			
			# Update the record
			frappe.db.set_value(
				"Expense", 
				expense.name, 
				"total_amount_company_currency", 
				total_amount_company_currency,
				update_modified=False
			)
			
			updated_count += 1
			
		except Exception as e:
			frappe.log_error(
				f"Error setting total_amount_company_currency for Expense {expense.name}: {str(e)}",
				"Expense Patch Error"
			)
			print(f"Error processing Expense {expense.name}: {str(e)}")
	
	frappe.db.commit()
	print(f"Successfully updated {updated_count} out of {len(expenses)} expenses with total_amount_company_currency")
