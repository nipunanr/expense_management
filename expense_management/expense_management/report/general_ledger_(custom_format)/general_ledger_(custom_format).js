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

		if (data && data.voucher_type && data.voucher_no && column.fieldname === "description") {
			value = `<span title="${__("Click the row to view details")}"
				style="cursor: pointer; text-decoration: underline dotted;">${value}</span>`;
		}

		return value;
	},
	after_datatable_render: function (datatable) {
		// Clicking any transaction row opens the voucher detail (fields, child tables, ledger entries)
		$(datatable.bodyScrollable)
			.off("click.gl-row-detail")
			.on("click.gl-row-detail", ".dt-row", function (e) {
				if ($(e.target).closest("a, input, button").length) return;
				const row_index = $(this).attr("data-row-index");
				const row = row_index != null ? datatable.datamanager.getData(row_index) : null;
				if (row && row.voucher_type && row.voucher_no) {
					show_gl_row_detail(row);
				}
			});
	},
};

function show_gl_row_detail(row) {
	frappe.call({
		method: "expense_management.gl_row_detail.get_gl_row_detail",
		args: {
			voucher_type: row.voucher_type,
			voucher_no: row.voucher_no,
			account: row.account,
			debit: row.debit || 0,
			credit: row.credit || 0,
		},
		freeze: true,
		callback: (r) => r.message && render_gl_row_detail(r.message, row),
	});
}

function render_gl_row_detail(d, row) {
	const esc = (v) => frappe.utils.escape_html(v == null ? "" : String(v));
	const link = (doctype, name, label) =>
		`<a href="/app/${frappe.router.slug(doctype)}/${encodeURIComponent(name)}" target="_blank">${esc(label || name)}</a>`;
	const render_cell = (c) =>
		c.links && c.links.length ? c.links.map((l) => link(l[0], l[1], l[2])).join(", ") : esc(c.v);

	const amount = row.debit
		? `${__("Dr")} ${format_currency(row.debit, row.currency)}`
		: row.credit
		? `${__("Cr")} ${format_currency(row.credit, row.currency)}`
		: "";
	const ledger_line = `<div style="margin-bottom: 12px; padding: 8px 12px; border-radius: 6px; background: var(--subtle-fg);">
		<span class="text-muted">${__("Ledger line")}:</span> <b>${esc(row.account)}</b>
		${amount ? ` &nbsp;·&nbsp; <b>${esc(amount)}</b>` : ""}
		${row.party ? ` &nbsp;·&nbsp; ${esc(row.party)}` : ""}
		${row.description ? `<div class="small text-muted" style="margin-top: 2px;">${esc(row.description)}</div>` : ""}
	</div>`;

	const fields_html = d.fields
		.map(
			(f) => `<div class="col-sm-4" style="margin-bottom: 8px;">
				<div class="text-muted small">${esc(f.label)}</div><div>${render_cell(f)}</div></div>`
		)
		.join("");

	const num = (t, j) => (t.numeric && t.numeric[j] ? ` class="text-right" style="white-space: nowrap;"` : "");
	const tables_html = d.tables
		.map((t) => {
			const has_highlight = t.highlight && t.highlight.some(Boolean);
			const body = t.rows
				.map(
					(cells, i) => `<tr style="${has_highlight && t.highlight[i] ? "background: var(--yellow-highlight-bg, #fff7d6); font-weight: 600;" : ""}">
						${cells.map((c, j) => `<td${num(t, j)}>${render_cell(c)}</td>`).join("")}</tr>`
				)
				.join("");
			const more =
				t.total_rows > t.rows.length
					? `<div class="small text-muted">${__("Showing {0} of {1} rows", [t.rows.length, t.total_rows])}</div>`
					: "";
			return `<div style="margin-top: 14px;">
				<div style="font-weight: 600; margin-bottom: 6px;">${esc(t.title)}</div>
				<div class="table-responsive"><table class="table table-bordered table-sm" style="margin-bottom: 4px;">
					<thead><tr>${t.columns.map((c, j) => `<th${num(t, j)}>${esc(c)}</th>`).join("")}</tr></thead>
					<tbody>${body}</tbody>
				</table></div>${more}</div>`;
		})
		.join("");

	const dialog = new frappe.ui.Dialog({
		title: d.title,
		size: "extra-large",
		fields: [{ fieldtype: "HTML", fieldname: "detail" }],
		primary_action_label: __("Open {0}", [__(d.voucher_type)]),
		primary_action: () => {
			window.open(`/app/${frappe.router.slug(d.voucher_type)}/${encodeURIComponent(d.voucher_no)}`, "_blank");
		},
	});
	dialog.fields_dict.detail.$wrapper.html(`
		${ledger_line}
		<div class="row">${fields_html}</div>
		${tables_html}
		<div class="small text-muted" style="margin-top: 8px;">${__("Highlighted rows relate to this ledger line.")}</div>
	`);
	dialog.show();
}
