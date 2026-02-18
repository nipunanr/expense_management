// Copyright (c) 2024, Technical Team and contributors
// For license information, please see license.txt

frappe.query_reports["Expense Analysis"] = {
	"filters": [
		{
			"fieldname": "company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company"),
			"reqd": 0
		},
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.add_months(frappe.datetime.get_today(), -3),
			"reqd": 1
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"reqd": 1
		},
		{
			"fieldname": "expense_account",
			"label": __("Expense Account"),
			"fieldtype": "Link",
			"options": "Account",
			"get_query": function() {
				return {
					"filters": {
						"account_type": ["in", ["Expense Account", "Cost of Goods Sold", "Fixed Asset", "Receivable"]],
						"is_group": 0,
						"company": frappe.query_report.get_filter_value('company')
					}
				};
			}
		},
		{
			"fieldname": "expense_type",
			"label": __("Expense Type"),
			"fieldtype": "Link",
			"options": "Expense Type"
		}
	],
	
	"formatter": function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		
		if (column.fieldname == "percentage") {
			if (data && data.percentage) {
				let color = data.percentage > 20 ? "red" : data.percentage > 10 ? "orange" : "green";
				value = `<span style="color: ${color}; font-weight: bold;">${value}</span>`;
			}
		}
		
		if (column.fieldname == "total_amount" && data && data.total_amount) {
			value = `<strong>${value}</strong>`;
		}
		
		return value;
	},
	
	"onload": function(report) {
		// Add custom buttons
		report.page.add_inner_button(__("Expense Summary"), function() {
			frappe.set_route("query-report", "Expense Summary");
		});
		
		report.page.add_inner_button(__("Create Expense"), function() {
			frappe.new_doc("Expense");
		});
		
		report.page.add_inner_button(__("Manage Types"), function() {
			frappe.set_route("List", "Expense Type");
		});
	}
};