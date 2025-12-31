// Copyright (c) 2024, Technical Team and contributors
// For license information, please see license.txt

frappe.ui.form.on('Expense Item', {
	expense_type: function(frm, cdt, cdn) {
		// Auto-fill expense account when expense type is selected
		let row = locals[cdt][cdn];
		if (row.expense_type && frm.doc.company) {
			frappe.call({
				method: 'expense_management.expense_management.doctype.expense.expense.get_expense_account_from_type',
				args: {
					expense_type: row.expense_type
				},
				callback: function(r) {
					if (r.message) {
						frappe.model.set_value(cdt, cdn, 'expense_account', r.message);
					}
				}
			});
		}
	}
});