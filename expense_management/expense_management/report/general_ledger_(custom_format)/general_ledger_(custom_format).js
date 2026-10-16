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

const GL_RD_STYLE = `
.gl-rd { color: var(--text-color); font-size: var(--text-base); }
.gl-rd a { color: inherit; text-decoration: underline; text-decoration-color: var(--border-color); text-underline-offset: 3px; }
.gl-rd a:hover { text-decoration-color: currentColor; }
.gl-rd .num { font-variant-numeric: tabular-nums; text-align: right; white-space: nowrap; }

.gl-rd-line { display: grid; grid-template-columns: 1fr auto; gap: 4px 24px; align-items: start;
	padding: 16px 18px; border-radius: var(--radius-5); background: var(--subtle-fg); margin-bottom: 20px; }
.gl-rd-line__account { font-size: var(--text-lg); font-weight: 600; line-height: 1.35; }
.gl-rd-line__party { margin-top: 2px; }
.gl-rd-line__desc { margin-top: 6px; color: var(--text-muted); max-width: 70ch; }
.gl-rd-line__amount { text-align: right; }
.gl-rd-line__value { font-size: 24px; font-weight: 600; font-variant-numeric: tabular-nums; line-height: 1.2; white-space: nowrap; }
.gl-rd-line__meta { display: flex; gap: 6px; justify-content: flex-end; margin-bottom: 6px; }

.gl-rd-tag { display: inline-block; padding: 1px 8px; border-radius: var(--radius-full); font-size: var(--text-sm); font-weight: 500; line-height: 20px; }
.gl-rd-tag[data-color="blue"] { background: var(--bg-blue); color: var(--text-on-blue); }
.gl-rd-tag[data-color="orange"] { background: var(--bg-orange); color: var(--text-on-orange); }
.gl-rd-tag[data-color="green"] { background: var(--bg-green); color: var(--text-on-green); }
.gl-rd-tag[data-color="red"] { background: var(--bg-red); color: var(--text-on-red); }
.gl-rd-tag[data-color="gray"] { background: var(--bg-gray); color: var(--text-on-gray); }

.gl-rd-groups { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 8px 40px; margin-bottom: 8px; }
.gl-rd-group h5, .gl-rd-tables h5 { font-size: var(--text-base); font-weight: 600; margin: 0 0 8px; color: var(--text-color); }
.gl-rd-group { margin-bottom: 16px; }
.gl-rd-dl { display: grid; grid-template-columns: minmax(120px, 40%) 1fr; margin: 0; }
.gl-rd-dl dt, .gl-rd-dl dd { padding: 6px 0; border-bottom: 1px solid var(--border-color); margin: 0; }
.gl-rd-dl dt { color: var(--text-muted); font-weight: 400; padding-right: 12px; }
.gl-rd-dl dd { overflow-wrap: anywhere; }
.gl-rd-dl dd.num { text-align: left; }
.gl-rd-notes { white-space: pre-line; max-width: 80ch; color: var(--text-color); margin: 0 0 20px; }

.gl-rd-tabs { display: flex; gap: 20px; box-shadow: inset 0 -1px 0 var(--border-color); overflow-x: auto; overflow-y: hidden; scrollbar-width: thin; }
.gl-rd-tab { background: none; border: 0; padding: 10px 0 9px; color: var(--text-light); white-space: nowrap;
	border-bottom: 2px solid transparent; display: inline-flex; align-items: center; gap: 6px; }
.gl-rd-tab:hover { color: var(--text-color); }
.gl-rd-tab[aria-selected="true"] { color: var(--text-color); border-bottom-color: var(--text-color); font-weight: 500; }
.gl-rd-tab:focus-visible { outline: 2px solid var(--text-color); outline-offset: 2px; border-radius: var(--radius-1); }
.gl-rd-count { font-size: var(--text-xs); color: var(--text-muted); background: var(--subtle-fg); border-radius: var(--radius-full); padding: 0 6px; line-height: 18px; }

.gl-rd-panel { max-height: 46vh; overflow: auto; border: 1px solid var(--border-color); border-top: 0; border-radius: 0 0 var(--radius-4) var(--radius-4); }
.gl-rd-table { width: 100%; border-collapse: separate; border-spacing: 0; font-size: var(--text-sm); }
.gl-rd-table th { position: sticky; top: 0; z-index: 1; background: var(--subtle-accent); color: var(--text-muted);
	font-weight: 500; text-align: left; padding: 8px 12px; border-bottom: 1px solid var(--border-color); white-space: nowrap; }
.gl-rd-table td { padding: 8px 12px; border-bottom: 1px solid var(--border-color); vertical-align: top; }
.gl-rd-table tbody tr:last-child td { border-bottom: 0; }
.gl-rd-table tr.is-line td { background: var(--bg-blue); }
.gl-rd-table tr.is-line td:first-child { box-shadow: inset 3px 0 0 var(--text-on-blue); }
.gl-rd-table tfoot td { position: sticky; bottom: 0; background: var(--subtle-accent); font-weight: 600; border-top: 1px solid var(--border-color); border-bottom: 0; }
.gl-rd-legend { display: flex; align-items: center; gap: 6px; margin-top: 8px; font-size: var(--text-sm); color: var(--text-muted); }
.gl-rd-legend i { width: 10px; height: 10px; border-radius: 2px; background: var(--bg-blue); box-shadow: inset 2px 0 0 var(--text-on-blue); display: inline-block; }
.gl-rd-more { padding: 8px 12px; font-size: var(--text-sm); color: var(--text-muted); }

@media (max-width: 640px) {
	.gl-rd-line { grid-template-columns: 1fr; }
	.gl-rd-line__amount { text-align: left; order: -1; }
	.gl-rd-line__meta { justify-content: flex-start; }
	.gl-rd-dl { grid-template-columns: 1fr; }
	.gl-rd-dl dt { border-bottom: 0; padding-bottom: 0; }
}
`;

function render_gl_row_detail(d, row) {
	if (!document.getElementById("gl-rd-style")) {
		$(`<style id="gl-rd-style">${GL_RD_STYLE}</style>`).appendTo("head");
	}

	const esc = (v) => frappe.utils.escape_html(v == null ? "" : String(v));
	const url = (doctype, name) => `/app/${frappe.router.slug(doctype)}/${encodeURIComponent(name)}`;
	const link = (doctype, name, label) => `<a href="${url(doctype, name)}" target="_blank" rel="noopener">${esc(label || name)}</a>`;
	const render_cell = (c) => (c.links && c.links.length ? c.links.map((l) => link(l[0], l[1], l[2])).join(", ") : esc(c.v));
	const NUMERIC = ["Currency", "Float", "Int", "Percent"];
	const LONG_TEXT = ["Small Text", "Text", "Long Text", "Text Editor", "HTML Editor", "Markdown Editor"];

	// 1. The ledger line that was clicked
	const is_debit = !!row.debit;
	const amount = row.debit || row.credit;
	const status = d.status
		? `<span class="gl-rd-tag" data-color="${esc(d.status.color)}">${esc(d.status.label)}</span>`
		: "";
	const line_html = `
		<section class="gl-rd-line" aria-label="${__("Ledger line")}">
			<div>
				<div class="gl-rd-line__account">${esc(row.account)}</div>
				${row.party ? `<div class="gl-rd-line__party">${esc(row.party)}</div>` : ""}
				${row.description ? `<div class="gl-rd-line__desc">${esc(row.description)}</div>` : ""}
			</div>
			<div class="gl-rd-line__amount">
				<div class="gl-rd-line__meta">
					${amount ? `<span class="gl-rd-tag" data-color="${is_debit ? "blue" : "orange"}">${is_debit ? __("Debit") : __("Credit")}</span>` : ""}
					${status}
				</div>
				${amount ? `<div class="gl-rd-line__value">${esc(format_currency(amount, row.currency))}</div>` : ""}
			</div>
		</section>`;

	// 2. Voucher fields: details / amounts / shipment, long text as notes
	const groups = { details: [], amounts: [], shipment: [], notes: [] };
	d.fields.forEach((f) => {
		if (f.group === "shipment") groups.shipment.push(f);
		else if (LONG_TEXT.includes(f.fieldtype)) {
			// already shown in the ledger line
			if ((f.v || "").trim() !== (row.description || "").trim()) groups.notes.push(f);
		}
		else if (NUMERIC.includes(f.fieldtype)) groups.amounts.push(f);
		else groups.details.push(f);
	});
	const dl = (title, list, numeric) =>
		list.length
			? `<div class="gl-rd-group"><h5>${title}</h5><dl class="gl-rd-dl">
				${list.map((f) => `<dt>${esc(f.label)}</dt><dd class="${numeric ? "num" : ""}">${render_cell(f)}</dd>`).join("")}
			</dl></div>`
			: "";
	const groups_html = `<div class="gl-rd-groups">
		${dl(__("Details"), groups.details)}
		${dl(__("Shipment"), groups.shipment)}
		${dl(__("Amounts"), groups.amounts, true)}
	</div>`;
	const notes_html = groups.notes
		.map((f) => `<div class="gl-rd-group"><h5>${esc(f.label)}</h5><p class="gl-rd-notes">${esc(f.v)}</p></div>`)
		.join("");

	// 3. Child tables + ledger entries, one tab each
	let tables_html = "";
	if (d.tables.length) {
		const tabs = d.tables
			.map(
				(t, i) => `<button type="button" class="gl-rd-tab" role="tab" id="gl-rd-tab-${i}"
					aria-controls="gl-rd-panel-${i}" aria-selected="${i === 0}" tabindex="${i === 0 ? 0 : -1}" data-index="${i}">
					${esc(t.title)} <span class="gl-rd-count">${t.total_rows}</span></button>`
			)
			.join("");
		const panels = d.tables
			.map((t, i) => {
				const n = (j) => (t.numeric && t.numeric[j] ? ` class="num"` : "");
				const head = t.columns.map((c, j) => `<th scope="col"${n(j)}>${esc(c)}</th>`).join("");
				const body = t.rows
					.map(
						(cells, r) => `<tr class="${t.highlight && t.highlight[r] ? "is-line" : ""}">
							${cells.map((c, j) => `<td${n(j)}>${render_cell(c)}</td>`).join("")}</tr>`
					)
					.join("");
				const foot = t.totals ? `<tfoot><tr>${t.totals.map((c, j) => `<td${n(j)}>${render_cell(c)}</td>`).join("")}</tr></tfoot>` : "";
				const more = t.total_rows > t.rows.length
					? `<div class="gl-rd-more">${__("Showing the first {0} of {1} rows. Open the document to see all.", [t.rows.length, t.total_rows])}</div>`
					: "";
				return `<div class="gl-rd-panel" role="tabpanel" id="gl-rd-panel-${i}" aria-labelledby="gl-rd-tab-${i}" ${i === 0 ? "" : "hidden"}>
					<table class="gl-rd-table"><thead><tr>${head}</tr></thead><tbody>${body}</tbody>${foot}</table>${more}</div>`;
			})
			.join("");
		const any_highlight = d.tables.some((t) => (t.highlight || []).some(Boolean));
		tables_html = `<div class="gl-rd-tables">
			<div class="gl-rd-tabs" role="tablist">${tabs}</div>${panels}
			${any_highlight ? `<div class="gl-rd-legend"><i></i>${__("Lines posted to {0}", [esc(row.account)])}</div>` : ""}
		</div>`;
	}

	const dialog = new frappe.ui.Dialog({
		title: d.title,
		size: "extra-large",
		fields: [{ fieldtype: "HTML", fieldname: "detail" }],
		primary_action_label: __("Open {0}", [__(d.voucher_type)]),
		primary_action: () => window.open(url(d.voucher_type, d.voucher_no), "_blank"),
	});
	const $body = dialog.fields_dict.detail.$wrapper;
	$body.html(`<div class="gl-rd">${line_html}${groups_html}${notes_html}${tables_html}</div>`);

	// tabs: click + arrow keys
	const $tabs = $body.find(".gl-rd-tab");
	const select_tab = (i) => {
		$tabs.each((j, el) => {
			$(el).attr({ "aria-selected": j === i, tabindex: j === i ? 0 : -1 });
		});
		$body.find(".gl-rd-panel").each((j, el) => {
			el.hidden = j !== i;
		});
	};
	$tabs.on("click", (e) => select_tab(+$(e.currentTarget).attr("data-index")));
	$tabs.on("keydown", (e) => {
		if (!["ArrowLeft", "ArrowRight"].includes(e.key)) return;
		const i = (+$(e.currentTarget).attr("data-index") + (e.key === "ArrowRight" ? 1 : -1) + $tabs.length) % $tabs.length;
		select_tab(i);
		$tabs.eq(i).trigger("focus");
	});

	dialog.show();
}
