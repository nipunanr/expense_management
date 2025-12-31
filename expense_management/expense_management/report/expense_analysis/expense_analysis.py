# Copyright (c) 2024, Technical Team and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, cint


def execute(filters=None):
	if not filters:
		filters = {}
	
	columns = get_columns()
	data = get_data(filters)
	chart = get_chart_data(filters)
	summary = get_summary_data(filters)
	
	return columns, data, None, chart, summary


def get_columns():
	return [
		{
			"label": _("Expense Account"),
			"fieldname": "expense_account",
			"fieldtype": "Link",
			"options": "Account",
			"width": 200
		},
		{
			"label": _("Expense Type"),
			"fieldname": "expense_type",
			"fieldtype": "Link",
			"options": "Expense Type",
			"width": 150
		},
		{
			"label": _("Count"),
			"fieldname": "count",
			"fieldtype": "Int",
			"width": 80
		},
		{
			"label": _("Total Amount"),
			"fieldname": "total_amount",
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"label": _("Average Amount"),
			"fieldname": "avg_amount",
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"label": _("Percentage"),
			"fieldname": "percentage",
			"fieldtype": "Percent",
			"width": 100
		},
		{
			"label": _("Company"),
			"fieldname": "company",
			"fieldtype": "Link",
			"options": "Company",
			"width": 120
		}
	]


def get_data(filters):
	conditions = get_conditions(filters)
	
	# Query to get expense analysis by account/type
	query = """
		SELECT 
			ei.expense_account,
			ei.expense_type,
			COUNT(*) as count,
			SUM(ei.amount) as total_amount,
			AVG(ei.amount) as avg_amount,
			e.company
		FROM `tabExpense Item` ei
		INNER JOIN `tabExpense` e ON ei.parent = e.name
		WHERE e.docstatus = 1 {conditions}
		GROUP BY ei.expense_account, ei.expense_type, e.company
		ORDER BY total_amount DESC
	""".format(conditions=conditions)
	
	data = frappe.db.sql(query, filters, as_dict=1)
	
	# Calculate percentages
	total_overall = sum(row.total_amount for row in data)
	for row in data:
		row.percentage = (row.total_amount / total_overall * 100) if total_overall else 0
		row.avg_amount = flt(row.avg_amount, 2)
		row.total_amount = flt(row.total_amount, 2)
	
	return data


def get_conditions(filters):
	conditions = []
	
	if filters.get("company"):
		conditions.append("AND e.company = %(company)s")
	
	if filters.get("from_date"):
		conditions.append("AND e.expense_date >= %(from_date)s")
	
	if filters.get("to_date"):
		conditions.append("AND e.expense_date <= %(to_date)s")
	
	if filters.get("expense_account"):
		conditions.append("AND ei.expense_account = %(expense_account)s")
	
	if filters.get("expense_type"):
		conditions.append("AND ei.expense_type = %(expense_type)s")
	
	return " ".join(conditions)


def get_summary_data(filters):
	"""Generate summary statistics"""
	conditions = get_conditions(filters)
	
	summary_query = """
		SELECT 
			COUNT(DISTINCT ei.expense_account) as unique_accounts,
			COUNT(DISTINCT ei.expense_type) as unique_types,
			COUNT(*) as total_line_items,
			SUM(ei.amount) as total_amount,
			AVG(ei.amount) as avg_amount,
			MAX(ei.amount) as max_amount,
			MIN(ei.amount) as min_amount
		FROM `tabExpense Item` ei
		INNER JOIN `tabExpense` e ON ei.parent = e.name
		WHERE e.docstatus = 1 {conditions}
	""".format(conditions=conditions)
	
	summary_data = frappe.db.sql(summary_query, filters, as_dict=1)[0]
	
	return [
		{
			"value": flt(summary_data.total_amount or 0, 2),
			"indicator": "Green",
			"label": _("Total Amount"),
			"datatype": "Currency",
		},
		{
			"value": cint(summary_data.total_line_items or 0),
			"indicator": "Blue",
			"label": _("Total Line Items"),
			"datatype": "Int",
		},
		{
			"value": flt(summary_data.avg_amount or 0, 2),
			"indicator": "Orange",
			"label": _("Average Amount"),
			"datatype": "Currency",
		},
		{
			"value": cint(summary_data.unique_accounts or 0),
			"indicator": "Purple",
			"label": _("Unique Accounts"),
			"datatype": "Int",
		},
		{
			"value": cint(summary_data.unique_types or 0),
			"indicator": "Yellow",
			"label": _("Expense Types"),
			"datatype": "Int",
		}
	]


def get_chart_data(filters):
	"""Generate pie chart for expense distribution"""
	conditions = get_conditions(filters)
	
	chart_query = """
		SELECT 
			ei.expense_type,
			SUM(ei.amount) as total_amount
		FROM `tabExpense Item` ei
		INNER JOIN `tabExpense` e ON ei.parent = e.name
		WHERE e.docstatus = 1 {conditions}
		GROUP BY ei.expense_type
		ORDER BY total_amount DESC
		LIMIT 10
	""".format(conditions=conditions)
	
	chart_data = frappe.db.sql(chart_query, filters, as_dict=1)
	
	if not chart_data:
		return None
	
	labels = [row.expense_type for row in chart_data]
	values = [flt(row.total_amount, 2) for row in chart_data]
	
	chart = {
		"data": {
			"labels": labels,
			"datasets": [
				{
					"name": "Amount",
					"values": values
				}
			]
		},
		"type": "pie",
		"height": 300,
		"colors": ["#5e64ff", "#743ee2", "#ff5858", "#ffa00a", "#28a745", "#17a2b8", "#ffc107", "#6c757d", "#e83e8c", "#fd7e14"]
	}
	
	return chart