// Copyright (c) 2024, Technical Team and contributors
// For license information, please see license.js

frappe.ui.form.on('Expense', {
	refresh: function(frm) {
		// Add custom buttons
		if (frm.doc.docstatus === 0) {
			frm.add_custom_button(__('Preview GL Entries'), function() {
				preview_gl_entries(frm);
			});
		}
		
		// Filter payment account based on company
		frm.set_query("payment_account", function() {
			return {
				filters: {
					"company": frm.doc.company,
					"account_type": ["in", ["Cash", "Bank"]],
					"is_group": 0
				}
			};
		});
		
		// Configure expense_items as editable grid - enable add/delete
		frm.set_df_property('expense_items', 'cannot_add_rows', false);
		frm.set_df_property('expense_items', 'cannot_delete_rows', false);
		
		// Refresh grid to apply changes
		if (frm.fields_dict['expense_items'] && frm.fields_dict['expense_items'].grid) {
			frm.fields_dict['expense_items'].grid.refresh();
		}
	},
	
	company: function(frm) {
		// Clear payment account when company changes
		if (frm.doc.company) {
			frm.set_value('payment_account', '');
		}
	}
});

// Child table events for Expense Item
frappe.ui.form.on('Expense Item', {
	expense_type: function(frm, cdt, cdn) {
		// Auto-fill expense account when expense type is selected
		let row = locals[cdt][cdn];
		if (row.expense_type) {
			frappe.call({
				method: 'expense_management.expense_management.doctype.expense.expense.get_expense_account_from_type',
				args: {
					expense_type: row.expense_type
				},
				callback: function(r) {
					if (r.message) {
						frappe.model.set_value(cdt, cdn, 'expense_account', r.message);
						// Auto-set description if not provided
						if (!row.description) {
							frappe.model.set_value(cdt, cdn, 'description', row.expense_type);
						}
					}
				}
			});
		}
	},
	
	expense_account: function(frm, cdt, cdn) {
		// Filter expense accounts based on company and auto-set description
		let row = locals[cdt][cdn];
		frm.set_query("expense_account", "expense_items", function() {
			return {
				filters: {
					"company": frm.doc.company,
					"account_type": ["in", ["Expense Account", "Cost of Goods Sold"]],
					"is_group": 0,
					"disabled": 0
				}
			};
		});
		
		// Auto-set description from account name if not provided
		if (row.expense_account && !row.description) {
			frappe.call({
				method: 'frappe.client.get_value',
				args: {
					doctype: 'Account',
					fieldname: 'account_name',
					filters: { name: row.expense_account }
				},
				callback: function(r) {
					if (r.message && r.message.account_name) {
						frappe.model.set_value(cdt, cdn, 'description', r.message.account_name);
					}
				}
			});
		}
	},
	
	amount: function(frm, cdt, cdn) {
		// Calculate total when amount changes
		calculate_total(frm);
	},
	
	expense_items_remove: function(frm, cdt, cdn) {
		// Recalculate total when row is removed
		calculate_total(frm);
	}
});

function calculate_total(frm) {
	let total = 0;
	frm.doc.expense_items.forEach(function(item) {
		total += flt(item.amount);
	});
	frm.set_value('total_amount', total);
}

function preview_gl_entries(frm) {
	if (!frm.doc.expense_items || frm.doc.expense_items.length === 0) {
		frappe.msgprint(__('Please add at least one expense item before previewing GL Entries'));
		return;
	}
	
	if (!frm.doc.payment_account) {
		frappe.msgprint(__('Please select a payment account before previewing GL Entries'));
		return;
	}
	
	frappe.call({
		method: 'preview_gl_entries',
		doc: frm.doc,
		callback: function(r) {
			if (r.message) {
				show_gl_entries_dialog(r.message);
			}
		}
	});
}

function show_gl_entries_dialog(gl_entries) {
	let d = new frappe.ui.Dialog({
		title: __('Preview GL Entries'),
		size: 'large',
		fields: [
			{
				fieldtype: 'HTML',
				fieldname: 'gl_entries_html'
			}
		]
	});
	
	let html = '<table class="table table-bordered">';
	html += '<thead><tr>';
	html += '<th>Account</th>';
	html += '<th>Debit</th>';
	html += '<th>Credit</th>';
	html += '<th>Against</th>';
	html += '<th>Remarks</th>';
	html += '</tr></thead><tbody>';
	
	gl_entries.forEach(entry => {
		html += '<tr>';
		html += `<td>${entry.account}</td>`;
		html += `<td>${format_currency(entry.debit)}</td>`;
		html += `<td>${format_currency(entry.credit)}</td>`;
		html += `<td>${entry.against}</td>`;
		html += `<td>${entry.remarks}</td>`;
		html += '</tr>';
	});
	
	html += '</tbody></table>';
	
	d.fields_dict.gl_entries_html.$wrapper.html(html);
	d.show();
}