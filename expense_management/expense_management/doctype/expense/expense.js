// Copyright (c) 2024, Technical Team and contributors
// For license information, please see license.js

frappe.ui.form.on('Expense', {

	refresh: function (frm) {

		/* ------------------------------------------------------------
		 * Payment Account Filter (Cash / Bank only)
		 * ------------------------------------------------------------ */
		frm.set_query("payment_account", function () {
			return {
				filters: {
					company: frm.doc.company,
					account_type: ["in", ["Cash", "Bank"]],
					is_group: 0,
					disabled: 0
				}
			};
		});

		/* ------------------------------------------------------------
		 * ✅ FIXED: Expense Account Filter for Child Table
		 * ------------------------------------------------------------ */
		frm.set_query("expense_account", "expense_items", function () {
			return {
				filters: {
					company: frm.doc.company,
					account_type: "Expense Account",
					is_group: 0,
					disabled: 0
				}
			};
		});

		/* ------------------------------------------------------------
		 * Enable Add / Delete Rows in Child Table
		 * ------------------------------------------------------------ */
		frm.set_df_property('expense_items', 'cannot_add_rows', false);
		frm.set_df_property('expense_items', 'cannot_delete_rows', false);

		if (frm.fields_dict.expense_items?.grid) {
			frm.fields_dict.expense_items.grid.refresh();
		}

		/* ------------------------------------------------------------
		 * Preview GL Button (Draft Only)
		 * ------------------------------------------------------------ */
		if (frm.doc.docstatus === 0) {
			frm.add_custom_button(__('Preview GL Entries'), function () {
				preview_gl_entries(frm);
			});
		}
	},

	company: function (frm) {
		// Clear payment account when company changes
		frm.set_value('payment_account', '');
	}
});


/* =====================================================================
 * Child Table: Expense Item
 * ===================================================================== */

frappe.ui.form.on('Expense Item', {

	expense_type: function (frm, cdt, cdn) {
		let row = locals[cdt][cdn];

		if (!row.expense_type) return;

		frappe.call({
			method: 'expense_management.expense_management.doctype.expense.expense.get_expense_account_from_type',
			args: {
				expense_type: row.expense_type
			},
			callback: function (r) {
				if (r.message) {
					frappe.model.set_value(cdt, cdn, 'expense_account', r.message);

					if (!row.description) {
						frappe.model.set_value(cdt, cdn, 'description', row.expense_type);
					}
				}
			}
		});
	},

	expense_account: function (frm, cdt, cdn) {
		let row = locals[cdt][cdn];

		if (row.expense_account && !row.description) {
			frappe.call({
				method: 'frappe.client.get_value',
				args: {
					doctype: 'Account',
					filters: { name: row.expense_account },
					fieldname: 'account_name'
				},
				callback: function (r) {
					if (r.message?.account_name) {
						frappe.model.set_value(cdt, cdn, 'description', r.message.account_name);
					}
				}
			});
		}
	},

	amount: function (frm) {
		calculate_total(frm);
	},

	expense_items_remove: function (frm) {
		calculate_total(frm);
	}
});


/* =====================================================================
 * Utility Functions
 * ===================================================================== */

function calculate_total(frm) {
	let total = 0;

	(frm.doc.expense_items || []).forEach(item => {
		total += flt(item.amount);
	});

	frm.set_value('total_amount', total);
}


/* =====================================================================
 * GL Preview Logic
 * ===================================================================== */

function preview_gl_entries(frm) {

	if (!frm.doc.expense_items || frm.doc.expense_items.length === 0) {
		frappe.msgprint(__('Please add at least one expense item.'));
		return;
	}

	if (!frm.doc.payment_account) {
		frappe.msgprint(__('Please select a payment account.'));
		return;
	}

	frappe.call({
		method: 'preview_gl_entries',
		doc: frm.doc,
		callback: function (r) {
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
		fields: [{
			fieldtype: 'HTML',
			fieldname: 'gl_entries_html'
		}]
	});

	let html = `
		<table class="table table-bordered">
			<thead>
				<tr>
					<th>Account</th>
					<th>Debit</th>
					<th>Credit</th>
					<th>Against</th>
					<th>Remarks</th>
				</tr>
			</thead>
			<tbody>
	`;

	gl_entries.forEach(e => {
		html += `
			<tr>
				<td>${e.account}</td>
				<td>${format_currency(e.debit)}</td>
				<td>${format_currency(e.credit)}</td>
				<td>${e.against}</td>
				<td>${e.remarks || ''}</td>
			</tr>
		`;
	});

	html += `</tbody></table>`;

	d.fields_dict.gl_entries_html.$wrapper.html(html);
	d.show();
}
