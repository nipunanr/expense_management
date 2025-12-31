# Copyright (c) 2024, Technical Team and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate, formatdate, cint, add_days, today


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
			"label": _("Expense ID"),
			"fieldname": "name",
			"fieldtype": "Link",
			"options": "Expense",
			"width": 120
		},
		{
			"label": _("Date"),
			"fieldname": "expense_date",
			"fieldtype": "Date",
			"width": 100
		},
		{
			"label": _("Description"),
			"fieldname": "description",
			"fieldtype": "Data",
			"width": 200
		},
		{
			"label": _("Expense Items"),
			"fieldname": "expense_items_count",
			"fieldtype": "Int",
			"width": 80
		},
		{
			"label": _("Top Expense Type"),
			"fieldname": "top_expense_account",
			"fieldtype": "Data",
			"width": 150
		},
		{
			"label": _("Payment Account"),
			"fieldname": "payment_account",
			"fieldtype": "Link",
			"options": "Account",
			"width": 150
		},
		{
			"label": _("Payment Mode"),
			"fieldname": "payment_mode",
			"fieldtype": "Data",
			"width": 100
		},
		{
			"label": _("Total Amount"),
			"fieldname": "total_amount",
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"label": _("Status"),
			"fieldname": "docstatus",
			"fieldtype": "Data",
			"width": 100
		},
		{
			"label": _("Created By"),
			"fieldname": "owner",
			"fieldtype": "Link",
			"options": "User",
			"width": 120
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
	
	# Main query with enhanced data
	query = """
		SELECT 
			e.name,
			e.expense_date,
			e.description,
			e.payment_account,
			e.payment_mode,
			e.total_amount,
			CASE 
				WHEN e.docstatus = 0 THEN 'Draft'
				WHEN e.docstatus = 1 THEN 'Submitted'
				WHEN e.docstatus = 2 THEN 'Cancelled'
			END as docstatus,
			e.owner,
			e.company,
			(SELECT COUNT(*) FROM `tabExpense Item` WHERE parent = e.name) as expense_items_count,
			(SELECT ei.expense_account FROM `tabExpense Item` ei 
			 WHERE ei.parent = e.name 
			 ORDER BY ei.amount DESC LIMIT 1) as top_expense_account
		FROM `tabExpense` e
		WHERE {conditions}
		ORDER BY e.expense_date DESC, e.creation DESC
	""".format(conditions=conditions)
	
	return frappe.db.sql(query, filters, as_dict=1)


def get_summary_data(filters):
	"""Generate dashboard summary cards"""
	conditions = get_conditions(filters)
	
	# Total expenses summary
	total_query = """
		SELECT 
			SUM(CASE WHEN e.docstatus = 1 THEN e.total_amount ELSE 0 END) as total_submitted,
			SUM(CASE WHEN e.docstatus = 0 THEN e.total_amount ELSE 0 END) as total_draft,
			SUM(CASE WHEN e.docstatus = 2 THEN e.total_amount ELSE 0 END) as total_cancelled,
			COUNT(CASE WHEN e.docstatus = 1 THEN 1 END) as count_submitted,
			COUNT(CASE WHEN e.docstatus = 0 THEN 1 END) as count_draft,
			COUNT(CASE WHEN e.docstatus = 2 THEN 1 END) as count_cancelled
		FROM `tabExpense` e
		WHERE {conditions}
	""".format(conditions=conditions)
	
	totals = frappe.db.sql(total_query, filters, as_dict=1)[0]
	
	# Average expense
	avg_expense = totals.total_submitted / totals.count_submitted if totals.count_submitted else 0
	
	summary = [
		{
			"value": flt(totals.total_submitted or 0, 2),
			"indicator": "Green" if totals.total_submitted else "Grey",
			"label": _("Total Submitted Amount"),
			"datatype": "Currency",
		},
		{
			"value": cint(totals.count_submitted or 0),
			"indicator": "Blue",
			"label": _("Submitted Expenses"),
			"datatype": "Int",
		},
		{
			"value": flt(avg_expense, 2),
			"indicator": "Orange" if avg_expense else "Grey",
			"label": _("Average Expense"),
			"datatype": "Currency",
		},
		{
			"value": cint(totals.count_draft or 0),
			"indicator": "Yellow" if totals.count_draft else "Grey",
			"label": _("Draft Expenses"),
			"datatype": "Int",
		}
	]
	
	# Add cancelled if any
	if totals.count_cancelled:
		summary.append({
			"value": cint(totals.count_cancelled),
			"indicator": "Red",
			"label": _("Cancelled Expenses"),
			"datatype": "Int",
		})
	
	return summary


def get_chart_data(filters):
	"""Generate chart data for expense trends"""
	conditions = get_conditions(filters)
	
	# Monthly trend data
	chart_query = """
		SELECT 
			DATE_FORMAT(e.expense_date, '%%Y-%%m') as month,
			SUM(CASE WHEN e.docstatus = 1 THEN e.total_amount ELSE 0 END) as amount,
			COUNT(CASE WHEN e.docstatus = 1 THEN 1 END) as count
		FROM `tabExpense` e
		WHERE e.docstatus = 1 AND {conditions}
		GROUP BY DATE_FORMAT(e.expense_date, '%%Y-%%m')
		ORDER BY month DESC
		LIMIT 12
	""".format(conditions=conditions)
	
	chart_data = frappe.db.sql(chart_query, filters, as_dict=1)
	chart_data.reverse()  # Show oldest to newest
	
	if not chart_data:
		return None
	
	# Prepare chart configuration
	labels = []
	amounts = []
	counts = []
	
	for row in chart_data:
		try:
			# Format month label
			month_date = getdate(row.month + "-01")
			labels.append(formatdate(month_date, "MMM yyyy"))
			amounts.append(flt(row.amount, 2))
			counts.append(cint(row.count))
		except:
			labels.append(row.month)
			amounts.append(flt(row.amount, 2))
			counts.append(cint(row.count))
	
	chart = {
		"data": {
			"labels": labels,
			"datasets": [
				{
					"name": "Total Amount",
					"type": "bar",
					"values": amounts
				},
				{
					"name": "Number of Expenses", 
					"type": "line",
					"values": counts
				}
			]
		},
		"type": "axis-mixed",
		"height": 300,
		"colors": ["#478778", "#FC766A"]
	}
	
	return chart


def get_conditions(filters):
	conditions = ["1=1"]
	
	if filters.get("company"):
		conditions.append("e.company = %(company)s")
	
	if filters.get("from_date"):
		conditions.append("e.expense_date >= %(from_date)s")
	
	if filters.get("to_date"):
		conditions.append("e.expense_date <= %(to_date)s")
	
	if filters.get("payment_account"):
		conditions.append("e.payment_account = %(payment_account)s")
	
	if filters.get("payment_mode"):
		conditions.append("e.payment_mode = %(payment_mode)s")
	
	if filters.get("status"):
		if filters.get("status") == "Draft":
			conditions.append("e.docstatus = 0")
		elif filters.get("status") == "Submitted":
			conditions.append("e.docstatus = 1")
		elif filters.get("status") == "Cancelled":
			conditions.append("e.docstatus = 2")
	
	if filters.get("owner"):
		conditions.append("e.owner = %(owner)s")
	
	return " AND ".join(conditions)