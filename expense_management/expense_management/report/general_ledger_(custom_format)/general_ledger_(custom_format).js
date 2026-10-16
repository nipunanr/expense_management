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

		if (data && data.issue_detail && column.fieldname === "description") {
			value = `<span class="gl-issue-detail-link" title="${__("Click to view issue details")}"
				style="cursor: pointer; text-decoration: underline dotted;">${value}</span>`;
		}

		return value;
	},
	after_datatable_render: function (datatable) {
		// Clicking a Material Issue row opens the full shipment / item / supplier detail
		$(datatable.bodyScrollable)
			.off("click.gl-issue-detail")
			.on("click.gl-issue-detail", ".dt-row", function (e) {
				if ($(e.target).closest("a").length) return;
				const row_index = $(this).attr("data-row-index");
				const row = row_index != null ? datatable.datamanager.getData(row_index) : null;
				if (row && row.issue_detail) {
					show_gl_issue_detail(row);
				}
			});
	},
};

function show_gl_issue_detail(row) {
	const d = row.issue_detail;
	const esc = (v) => frappe.utils.escape_html(v == null ? "" : String(v));
	const link = (doctype, name) =>
		name ? `<a href="/app/${frappe.router.slug(doctype)}/${encodeURIComponent(name)}" target="_blank">${esc(name)}</a>` : "";

	const fields = [
		[__("Stock Entry"), link("Stock Entry", d.stock_entry)],
		[__("Stock Entry Type"), esc(d.stock_entry_type)],
		[__("Purpose of Issue"), esc(d.purpose_of_issue)],
		[__("Reference No"), esc(d.reference_no)],
		[__("Shipment (Customer Order)"), link("Customer Order", d.customer_order)],
		[__("Customer"), d.customer ? `${link("Customer", d.customer)}${d.customer_name && d.customer_name !== d.customer ? " - " + esc(d.customer_name) : ""}` : ""],
		[__("Customer Batch"), esc(d.customer_batch)],
		[__("Invoice No"), esc(d.invoice_no)],
		[__("Packing Plan"), link("Packing Plan", d.packing_plan)],
		[__("Work Order"), link("Work Order", d.work_order)],
		[__("Remarks"), esc(d.remarks)],
	].filter(([, v]) => v);

	const header_html = fields
		.map(
			([label, v]) => `<div class="col-sm-6" style="margin-bottom: 8px;">
				<div class="text-muted small">${label}</div><div>${v}</div></div>`
		)
		.join("");

	const has_other_rows = d.items.some((it) => !it.in_row);
	const items_html = d.items
		.map((it) => {
			const suppliers = (it.suppliers || [])
				.map((s, i) => link("Supplier", s) + (it.supplier_names[i] && it.supplier_names[i] !== s ? ` - ${esc(it.supplier_names[i])}` : ""))
				.join("<br>");
			const batches = (it.batches || []).map((b) => link("Batch", b)).join("<br>");
			return `<tr style="${has_other_rows && !it.in_row ? "opacity: 0.55;" : ""}">
				<td>${link("Item", it.item_code)}${it.item_name && it.item_name !== it.item_code ? `<div class="small text-muted">${esc(it.item_name)}</div>` : ""}</td>
				<td class="text-right">${esc(format_number(it.qty, null, Number.isInteger(it.qty) ? 0 : 3))} ${esc(it.uom)}</td>
				<td>${batches}</td>
				<td>${suppliers || `<span class="text-muted">${__("Not found")}</span>`}</td>
				<td>${esc(it.warehouse)}</td>
				<td>${esc(it.expense_account)}</td>
			</tr>`;
		})
		.join("");

	const dialog = new frappe.ui.Dialog({
		title: __("Material Issue {0}", [d.stock_entry]),
		size: "extra-large",
		fields: [{ fieldtype: "HTML", fieldname: "detail" }],
	});
	dialog.fields_dict.detail.$wrapper.html(`
		<div class="row">${header_html}</div>
		<div class="table-responsive" style="margin-top: 8px;">
			<table class="table table-bordered table-sm">
				<thead><tr>
					<th>${__("Item")}</th><th class="text-right">${__("Qty")}</th><th>${__("Batch")}</th>
					<th>${__("Supplier")}</th><th>${__("Source Warehouse")}</th><th>${__("Expense Account")}</th>
				</tr></thead>
				<tbody>${items_html}</tbody>
			</table>
		</div>
		${has_other_rows ? `<div class="small text-muted">${__("Faded items are posted to another account of this voucher, not to {0}.", [esc(d.account)])}</div>` : ""}
	`);
	dialog.show();
}
