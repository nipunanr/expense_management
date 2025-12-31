# Copyright (c) 2024, Technical Team and contributors
# For license information, please see license.txt

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def after_install():
	"""Setup after app installation"""
	create_expense_types()
	frappe.db.commit()
	print("Expense Management app installed successfully!")


def create_expense_types():
	"""Create default expense types"""
	expense_types = [
		{
			"expense_type_name": "Office Supplies",
			"description": "Office supplies and stationery expenses",
			"is_active": 1
		},
		{
			"expense_type_name": "Travel & Transportation",
			"description": "Travel, transportation and vehicle expenses", 
			"is_active": 1
		},
		{
			"expense_type_name": "Meals & Entertainment",
			"description": "Business meals, entertainment and hospitality expenses",
			"is_active": 1
		},
		{
			"expense_type_name": "Communication",
			"description": "Telephone, internet and communication expenses",
			"is_active": 1
		},
		{
			"expense_type_name": "Utilities",
			"description": "Electricity, water and utility expenses",
			"is_active": 1
		},
		{
			"expense_type_name": "Professional Services",
			"description": "Legal, consulting and professional service expenses",
			"is_active": 1
		},
		{
			"expense_type_name": "Training & Education",
			"description": "Employee training and education expenses",
			"is_active": 1
		},
		{
			"expense_type_name": "Marketing & Advertising",
			"description": "Marketing, advertising and promotional expenses",
			"is_active": 1
		},
		{
			"expense_type_name": "Insurance",
			"description": "Insurance premiums and coverage expenses",
			"is_active": 1
		},
		{
			"expense_type_name": "Maintenance & Repairs",
			"description": "Equipment maintenance and repair expenses",
			"is_active": 1
		}
	]
	
	for expense_type_data in expense_types:
		if not frappe.db.exists("Expense Type", expense_type_data["expense_type_name"]):
			expense_type = frappe.get_doc({
				"doctype": "Expense Type",
				**expense_type_data
			})
			expense_type.insert()
			print(f"Created Expense Type: {expense_type_data['expense_type_name']}")
		else:
			print(f"Expense Type already exists: {expense_type_data['expense_type_name']}")