// Copyright (c) 2026, MISL Holdings (Pvt) Ltd and contributors
// For license information, please see license.txt

frappe.query_reports["General Ledger (Custom Format)"] = frappe.query_reports["General Ledger"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1,
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
			reqd: 1,
			width: "60px",
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
			width: "60px",
		},
		{
			fieldname: "account",
			label: __("Account"),
			fieldtype: "MultiSelectList",
			options: "Account",
			get_data: function (txt) {
				return frappe.db.get_link_options("Account", txt, {
					company: frappe.query_report.get_filter_value("company"),
				});
			},
		},
		{
			fieldname: "voucher_no",
			label: __("Voucher No"),
			fieldtype: "Data",
		},
		{
			fieldname: "against_voucher_no",
			label: __("Against Voucher No"),
			fieldtype: "Data",
		},
		{
			fieldname: "party_type",
			label: __("Party Type"),
			fieldtype: "Autocomplete",
			options: Object.keys((frappe.boot && frappe.boot.party_account_types) || {}),
			on_change: function () {
				frappe.query_report.set_filter_value("party", []);
			},
		},
		{
			fieldname: "party",
			label: __("Party"),
			fieldtype: "MultiSelectList",
			options: "party_type",
			depends_on: "party_type",
			get_data: function (txt) {
				if (!frappe.query_report.filters) return;
				let party_type = frappe.query_report.get_filter_value("party_type");
				if (!party_type) return;
				return frappe.db.get_link_options(party_type, txt);
			},
		},
		{
			fieldname: "presentation_currency",
			label: __("Currency"),
			fieldtype: "Select",
			options: erpnext.get_presentation_currency_list ? erpnext.get_presentation_currency_list() : [],
		},
	],
	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (
			(column.fieldname === "debit" || column.fieldname === "credit") &&
			(data[column.fieldname] === 0 || !data[column.fieldname])
		) {
			return "";
		}

		let is_summary_row =
			data &&
			((data.party && (data.party.indexOf("Total") !== -1 || data.party.indexOf("Opening") !== -1 || data.party.indexOf("Closing") !== -1)) ||
				(data.description && (data.description.indexOf("Total") !== -1 || data.description.indexOf("Opening") !== -1 || data.description.indexOf("Closing") !== -1)));

		if (is_summary_row) {
			value = $(`<span>${value}</span>`);
			var $value = $(value).css("font-weight", "bold");
			value = $value.wrap("<p></p>").parent().html();
		}

		return value;
	},
};
