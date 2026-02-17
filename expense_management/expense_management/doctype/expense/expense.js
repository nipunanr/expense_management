// Copyright (c) 2024, Technical Team and contributors
// For license information, please see license.js

frappe.ui.form.on('Expense', {

	refresh: function (frm) {

		/* ------------------------------------------------------------
		 * Payment Account Filter (Cash / Bank only)
		 * ------------------------------------------------------------ */
		frm.set_query("payment_account", function () {
			let filters = {
				company: frm.doc.company,
				account_type: ["in", ["Cash", "Bank"]],
				is_group: 0,
				disabled: 0
			};
			
			return { filters: filters };
		});

		/* ------------------------------------------------------------
		 * ✅ FIXED: Expense Account Filter for Child Table
		 * ------------------------------------------------------------ */
		frm.set_query("expense_account", "expense_items", function () {
			let filters = {
				company: frm.doc.company,
				root_type: "Expense",
				is_group: 0,
				disabled: 0
			};
			
			// Add currency filter if currency is set
			if (frm.doc.currency) {
				filters.account_currency = frm.doc.currency;
			}
			
			return { filters: filters };
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
		
		/* ------------------------------------------------------------
		 * View Accounting Ledger Button (Submitted/Cancelled)
		 * ------------------------------------------------------------ */
		if (frm.doc.docstatus === 1 || frm.doc.docstatus === 2) {
			frm.add_custom_button(__('Accounting Ledger'), function () {
				frappe.route_options = {
					voucher_no: frm.doc.name,
					from_date: frm.doc.expense_date,
					to_date: frm.doc.expense_date,
					company: frm.doc.company,
					group_by: "Group by Voucher (Consolidated)",
					show_cancelled_entries: frm.doc.docstatus === 2
				};
				frappe.set_route("query-report", "General Ledger");
			}, __('View'));
		}
		
		/* ------------------------------------------------------------
		 * Toggle Exchange Rate Field Visibility
		 * ------------------------------------------------------------ */
		toggle_exchange_rate_field(frm);
	},

	company: function (frm) {
		// Clear payment account when company changes
		frm.set_value('payment_account', '');
		frm.set_value('currency', '');
		toggle_exchange_rate_field(frm);
	},
	
	payment_account: function(frm) {
		// Set currency from payment account
		if (frm.doc.payment_account && frm.doc.company) {
			frappe.call({
				method: 'expense_management.expense_management.doctype.expense.expense.get_account_currency_for_expense',
				args: {
					account: frm.doc.payment_account
				},
				callback: function(r) {
					if (r.message) {
						frm.set_value('currency', r.message);
						
						// Update expense account filter to match currency
						frm.fields_dict.expense_items.grid.update_docfield_property(
							'expense_account',
							'get_query',
							function() {
								return {
									filters: {
										company: frm.doc.company,
										root_type: "Expense",
										is_group: 0,
										disabled: 0,
										account_currency: frm.doc.currency
									}
								};
							}
						);
						
						// Set exchange rate
						set_exchange_rate(frm);
						toggle_exchange_rate_field(frm);
					}
				}
			});
		}
	},
	
	currency: function(frm) {
		set_exchange_rate(frm);
		toggle_exchange_rate_field(frm);
	},
	
	expense_date: function(frm) {
		if (frm.doc.currency) {
			set_exchange_rate(frm);
		}
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
					// Check if account currency matches form currency
					if (frm.doc.currency) {
						frappe.call({
							method: 'expense_management.expense_management.doctype.expense.expense.get_account_currency_for_expense',
							args: {
								account: r.message
							},
							callback: function (curr_r) {
								if (curr_r.message && curr_r.message === frm.doc.currency) {
									// Currency matches, set the account
									frappe.model.set_value(cdt, cdn, 'expense_account', r.message);

									if (!row.description) {
										frappe.model.set_value(cdt, cdn, 'description', row.expense_type);
									}
								} else {
									// Currency doesn't match
									frappe.model.set_value(cdt, cdn, 'expense_account', '');
									frappe.msgprint({
										title: __('Currency Mismatch'),
										indicator: 'orange',
										message: __('The default account for {0} has currency {1}, but the payment account uses {2}. Please select a matching expense account.', 
											[row.expense_type, curr_r.message || 'Unknown', frm.doc.currency])
									});
								}
							}
						});
					} else {
						// No currency set yet, just set the account
						frappe.model.set_value(cdt, cdn, 'expense_account', r.message);

						if (!row.description) {
							frappe.model.set_value(cdt, cdn, 'description', row.expense_type);
						}
					}
				}
			}
		});
	},

	expense_account: function (frm, cdt, cdn) {
		let row = locals[cdt][cdn];

		if (!row.expense_account) return;

		// Validate currency match
		if (frm.doc.currency) {
			frappe.call({
				method: 'expense_management.expense_management.doctype.expense.expense.get_account_currency_for_expense',
				args: {
					account: row.expense_account
				},
				callback: function (r) {
					if (r.message && r.message !== frm.doc.currency) {
						// Currency doesn't match - clear the field
						frappe.model.set_value(cdt, cdn, 'expense_account', '');
						frappe.msgprint({
							title: __('Currency Mismatch'),
							indicator: 'red',
							message: __('Selected account has currency {0}, but payment account uses {1}. Please select an account with matching currency.', 
								[r.message, frm.doc.currency])
						});
						return;
					}
				}
			});
		}

		// Auto-set description from account name if not provided
		if (!row.description) {
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

function set_exchange_rate(frm) {
	if (!frm.doc.currency || !frm.doc.company) {
		return;
	}
	
	frappe.call({
		method: 'expense_management.expense_management.doctype.expense.expense.get_company_default_currency',
		args: {
			company: frm.doc.company
		},
		callback: function(r) {
			if (r.message) {
				let company_currency = r.message;
				
				if (frm.doc.currency === company_currency) {
					frm.set_value('exchange_rate', 1.0);
				} else if (!frm.doc.exchange_rate || frm.doc.exchange_rate === 0) {
					// Get exchange rate
					frappe.call({
						method: 'erpnext.setup.utils.get_exchange_rate',
						args: {
							from_currency: frm.doc.currency,
							to_currency: company_currency,
							transaction_date: frm.doc.expense_date || frappe.datetime.get_today()
						},
						callback: function(r) {
							if (r.message) {
								frm.set_value('exchange_rate', r.message);
							}
						}
					});
				}
			}
		}
	});
}

function toggle_exchange_rate_field(frm) {
	if (!frm.doc.currency || !frm.doc.company) {
		frm.set_df_property('exchange_rate', 'hidden', 1);
		return;
	}
	
	frappe.call({
		method: 'expense_management.expense_management.doctype.expense.expense.get_company_default_currency',
		args: {
			company: frm.doc.company
		},
		callback: function(r) {
			if (r.message) {
				let company_currency = r.message;
				// Show exchange rate field only if currency differs from company currency
				let should_hide = (frm.doc.currency === company_currency);
				frm.set_df_property('exchange_rate', 'hidden', should_hide ? 1 : 0);
			}
		}
	});
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
