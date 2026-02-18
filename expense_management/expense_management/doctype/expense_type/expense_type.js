// Copyright (c) 2024, Technical Team and contributors
// For license information, please see license.txt

frappe.ui.form.on('Expense Type', {
	refresh: function(frm) {
		// Filter default_account to show only allowed account types
		frm.set_query("default_account", function() {
			return {
				filters: {
					account_type: ["in", ["Expense Account", "Cost of Goods Sold", "Fixed Asset", "Current Asset"]],
					is_group: 0,
					disabled: 0
				}
			};
		});
	}
});
