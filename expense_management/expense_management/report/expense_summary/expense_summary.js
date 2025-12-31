// Copyright (c) 2024, Technical Team and contributors
// For license information, please see license.txt

frappe.query_reports["Expense Summary"] = {
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
			"fieldname": "payment_account",
			"label": __("Payment Account"),
			"fieldtype": "Link",
			"options": "Account",
			"get_query": function() {
				return {
					"filters": {
						"account_type": ["in", ["Bank", "Cash"]],
						"is_group": 0,
						"company": frappe.query_report.get_filter_value('company')
					}
				};
			}
		},
		{
			"fieldname": "payment_mode",
			"label": __("Payment Mode"),
			"fieldtype": "Select",
			"options": "\nCash\nBank Transfer\nCredit Card\nDebit Card\nCheque\nOnline Payment\nOther"
		},
		{
			"fieldname": "status",
			"label": __("Status"),
			"fieldtype": "Select",
			"options": "\nDraft\nSubmitted\nCancelled"
		},
		{
			"fieldname": "owner",
			"label": __("Created By"),
			"fieldtype": "Link",
			"options": "User"
		}
	],
	
	"formatter": function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		
		if (column.fieldname == "docstatus") {
			if (value == "Submitted") {
				value = `<span class="indicator-pill green">${value}</span>`;
			} else if (value == "Draft") {
				value = `<span class="indicator-pill yellow">${value}</span>`;
			} else if (value == "Cancelled") {
				value = `<span class="indicator-pill red">${value}</span>`;
			}
		}
		
		if (column.fieldname == "total_amount" && data && data.total_amount) {
			value = `<strong>${value}</strong>`;
		}
		
		return value;
	},
	
	"onload": function(report) {
		// Add custom buttons
		report.page.add_inner_button(__("Create Expense"), function() {
			frappe.new_doc("Expense");
		});
		
		report.page.add_inner_button(__("Expense Types"), function() {
			frappe.set_route("List", "Expense Type");
		});
		
		// Add export options
		report.page.add_menu_item(__("Export Data"), function() {
			frappe.utils.csvDownload(
				frappe.query_report.get_filter_values(),
				report.data
			);
		});
	},
	
	"after_datatable_render": function(datatable_obj) {
		// Add click handler for expense links
		$(datatable_obj.wrapper).on('click', '.dt-cell--col-0', function() {
			let expense_id = $(this).text().trim();
			if (expense_id && expense_id !== "Expense ID") {
				frappe.set_route("Form", "Expense", expense_id);
			}
		});
	},
	
	"get_datatable_options": function(options) {
		return Object.assign(options, {
			checkboxColumn: true,
			events: {
				onCheckRow: function(data) {
					// Handle row selection for bulk operations
					console.log("Selected rows:", data);
				}
			}
		});
	}
};