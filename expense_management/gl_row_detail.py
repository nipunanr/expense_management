# Copyright (c) 2026, MISL Holdings (Pvt) Ltd and contributors
# For license information, please see license.txt

"""Row-click detail for the General Ledger (Custom Format) report."""

import importlib

import frappe
from frappe import _
from frappe.utils import cstr, flt, fmt_money, strip_html_tags
from frappe.utils.formatters import format_value

MAX_TABLE_ROWS = 200

# fieldnames missing on a site (other apps / versions) are skipped
VOUCHER_CONFIG = {
	"Purchase Invoice": {
		"fields": [
			"supplier", "supplier_name", "posting_date", "bill_no", "bill_date", "due_date", "currency",
			"grand_total", "outstanding_amount", "status", "is_return", "return_against", "update_stock", "remarks",
		],
		"tables": [
			("items", ["item_code", "item_name", "qty", "uom", "rate", "amount", "expense_account",
				"warehouse", "purchase_order", "purchase_receipt", "batch_no"]),
			("taxes", ["charge_type", "account_head", "description", "tax_amount", "total"]),
			("advances", ["reference_type", "reference_name", "advance_amount", "allocated_amount"]),
			("payment_schedule", ["due_date", "payment_amount", "outstanding", "paid_amount"]),
		],
	},
	"Sales Invoice": {
		"fields": [
			"customer", "customer_name", "posting_date", "po_no", "po_date", "due_date", "currency",
			"grand_total", "outstanding_amount", "status", "is_return", "return_against", "remarks",
		],
		"tables": [
			("items", ["item_code", "item_name", "qty", "uom", "rate", "amount", "income_account",
				"sales_order", "delivery_note", "batch_no"]),
			("taxes", ["charge_type", "account_head", "description", "tax_amount", "total"]),
			("advances", ["reference_type", "reference_name", "advance_amount", "allocated_amount"]),
			("payment_schedule", ["due_date", "payment_amount", "outstanding", "paid_amount"]),
		],
	},
	"Payment Entry": {
		"fields": [
			"payment_type", "party_type", "party", "party_name", "posting_date", "mode_of_payment",
			"paid_from", "paid_to", "paid_amount", "received_amount", "reference_no", "reference_date",
			"bank_account", "status", "remarks",
		],
		"tables": [
			("references", ["reference_doctype", "reference_name", "due_date", "total_amount",
				"outstanding_amount", "allocated_amount"]),
			("deductions", ["account", "cost_center", "amount", "description"]),
			("taxes", ["charge_type", "account_head", "description", "tax_amount"]),
		],
	},
	"Journal Entry": {
		"fields": [
			"voucher_type", "posting_date", "cheque_no", "cheque_date", "bill_no", "bill_date",
			"total_debit", "total_credit", "user_remark", "remark",
		],
		"tables": [
			("accounts", ["account", "party_type", "party", "debit_in_account_currency",
				"credit_in_account_currency", "reference_type", "reference_name", "cost_center", "user_remark"]),
		],
	},
	"Expense": {
		"fields": [
			"description", "expense_date", "payment_mode", "payment_account", "currency", "exchange_rate",
			"total_amount", "total_amount_company_currency", "remarks",
		],
		"tables": [("expense_items", ["expense_type", "expense_account", "description", "amount"])],
	},
	"Expense Claim": {
		"fields": [
			"employee", "employee_name", "department", "posting_date", "expense_approver", "approval_status",
			"total_claimed_amount", "total_sanctioned_amount", "total_amount_reimbursed", "status", "remark",
		],
		"tables": [
			("expenses", ["expense_date", "expense_type", "description", "amount", "sanctioned_amount",
				"default_account"]),
			("taxes", ["account_head", "description", "tax_amount"]),
		],
	},
	"Purchase Receipt": {
		"fields": [
			"supplier", "supplier_name", "posting_date", "supplier_delivery_note", "currency", "grand_total",
			"status", "is_return", "return_against", "remarks",
		],
		"tables": [
			("items", ["item_code", "item_name", "qty", "uom", "rate", "amount", "warehouse",
				"purchase_order", "batch_no", "expense_account"]),
			("taxes", ["charge_type", "account_head", "description", "tax_amount"]),
		],
	},
	"Delivery Note": {
		"fields": [
			"customer", "customer_name", "posting_date", "po_no", "currency", "grand_total", "status",
			"is_return", "return_against", "remarks",
		],
		"tables": [
			("items", ["item_code", "item_name", "qty", "uom", "rate", "amount", "warehouse",
				"against_sales_order", "batch_no", "expense_account"]),
		],
	},
	"Stock Entry": {
		"fields": [
			"stock_entry_type", "purpose", "posting_date", "work_order", "bom_no", "from_warehouse",
			"to_warehouse", "custom_purpose_of_issue", "custom_reference_no", "custom_customer",
			"custom_packing_plan", "total_outgoing_value", "total_incoming_value", "remarks",
		],
		"tables": [
			("items", ["item_code", "item_name", "qty", "uom", "s_warehouse", "t_warehouse", "batch_no",
				"basic_rate", "amount", "expense_account", "is_finished_item"]),
			("additional_costs", ["expense_account", "description", "amount"]),
		],
	},
	"Stock Reconciliation": {
		"fields": ["purpose", "posting_date", "expense_account", "difference_amount"],
		"tables": [
			("items", ["item_code", "item_name", "warehouse", "batch_no", "current_qty", "qty",
				"valuation_rate", "amount_difference"]),
		],
	},
}

KEEP_ZERO_FIELDS = ("outstanding_amount",)
NUMERIC_FIELDTYPES = ("Currency", "Float", "Int", "Percent")
ACCOUNT_FIELDS = ("account", "expense_account", "income_account", "account_head", "default_account")
SKIP_FIELDTYPES = ("Section Break", "Column Break", "Tab Break", "HTML", "Table", "Table MultiSelect",
	"Button", "Image", "Attach Image", "Fold", "Heading")


def get_report_module():
	return importlib.import_module(
		"expense_management.expense_management.report.general_ledger_(custom_format).general_ledger_(custom_format)"
	)


@frappe.whitelist()
def get_gl_row_detail(voucher_type, voucher_no, account=None, debit=None, credit=None):
	if not voucher_type or not voucher_no or not frappe.db.exists(voucher_type, voucher_no):
		frappe.throw(_("{0} {1} not found").format(_(voucher_type or ""), voucher_no or ""))

	doc = frappe.get_doc(voucher_type, voucher_no)
	doc.check_permission("read")

	config = VOUCHER_CONFIG.get(voucher_type) or get_default_config(doc.meta)
	fieldnames = config["fields"]
	if voucher_type == "Stock Entry" and doc.stock_entry_type != "Material Issue":
		# these custom fields only show (and default to "Waste") on the plain Material Issue type
		fieldnames = [f for f in fieldnames if f not in ("custom_purpose_of_issue", "custom_reference_no")]
	fieldnames = [fn for fn in fieldnames if not is_redundant_field(doc, fn)]
	fields = [f for f in (get_field(doc, fn) for fn in fieldnames) if f]
	tables = [get_table(doc, fn, cols, account) for fn, cols in config.get("tables", [])]

	if voucher_type == "Stock Entry" and doc.purpose == "Material Issue":
		row = frappe._dict(account=account, debit=flt(debit), credit=flt(credit))
		set_stock_issue_detail(doc, row, fields, tables)

	tables.append(get_gl_entries_table(doc, account))

	return {
		"voucher_type": voucher_type,
		"voucher_no": voucher_no,
		"title": f"{_(voucher_type)} {voucher_no}",
		"account": account,
		"docstatus": doc.docstatus,
		"status": get_status(doc),
		"fields": fields,
		"tables": [t for t in tables if t and t["rows"]],
	}


STATUS_COLORS = {
	"green": ("Submitted", "Paid", "Completed", "Approved", "Reconciled", "Delivered", "Received", "To Bill"),
	"orange": ("Draft", "Unpaid", "Partly Paid", "Pending", "To Receive and Bill", "To Deliver and Bill",
		"Partly Paid and Discounted", "Unpaid and Discounted"),
	"red": ("Cancelled", "Overdue", "Overdue and Discounted", "Rejected", "Return", "Debit Note Issued",
		"Credit Note Issued"),
}


def get_status(doc):
	status = doc.get("status") if doc.meta.has_field("status") else None
	status = status or {0: "Draft", 1: "Submitted", 2: "Cancelled"}.get(doc.docstatus)
	color = next((c for c, values in STATUS_COLORS.items() if status in values), "gray")
	return {"label": _(status), "color": color} if status else None


def is_redundant_field(doc, fieldname):
	"""Fields that repeat something already shown, or only state the default."""
	value = doc.get(fieldname)
	if fieldname == "status":
		return True  # shown as the status badge
	if fieldname == "purpose" and value == doc.get("stock_entry_type"):
		return True
	if fieldname in ("exchange_rate", "conversion_rate") and flt(value) == 1:
		return True
	if fieldname == "currency" and doc.get("company"):
		return value == frappe.get_cached_value("Company", doc.company, "default_currency")
	if fieldname == "supplier_name" and value == doc.get("supplier"):
		return True
	if fieldname == "customer_name" and value == doc.get("customer"):
		return True
	if fieldname == "party_name" and value == doc.get("party"):
		return True
	if fieldname == "employee_name" and value == doc.get("employee"):
		return True
	if fieldname == "total_amount_company_currency" and flt(value) == flt(doc.get("total_amount")):
		return True
	return False


def get_default_config(meta):
	"""Unknown voucher types: fields shown in the list view / standard filters + remarks."""
	fields = [
		df.fieldname
		for df in meta.fields
		if (df.in_list_view or df.in_standard_filter or df.bold) and df.fieldtype not in SKIP_FIELDTYPES
	]
	for fn in ("posting_date", "remarks", "user_remark", "description"):
		if meta.has_field(fn) and fn not in fields:
			fields.append(fn)
	return {"fields": fields, "tables": []}


def cell(value, df=None, doc=None, links=None):
	"""A display value plus optional links: {"v": text, "links": [[doctype, name, label], ...]}."""
	if links is None and df and value:
		if df.fieldtype == "Link" and df.options:
			links = [[df.options, value, value]]
		elif df.fieldtype == "Dynamic Link" and doc and doc.get(df.options):
			links = [[doc.get(df.options), value, value]]

	if df and value not in (None, ""):
		text = format_value(value, df, doc)
		if df.fieldtype in ("Text Editor", "Small Text", "Text", "Long Text", "HTML Editor", "Markdown Editor"):
			text = strip_html_tags(cstr(text)).strip()
	else:
		text = cstr(value)

	return {"v": cstr(text), "links": links or []}


def get_field(doc, fieldname):
	df = doc.meta.get_field(fieldname)
	if not df:
		return None
	value = doc.get(fieldname)
	if value in (None, "") or (df.fieldtype == "Check" and not value):
		return None
	if df.fieldtype in NUMERIC_FIELDTYPES and not flt(value) and fieldname not in KEEP_ZERO_FIELDS:
		return None
	return {"label": _(df.label), "fieldtype": df.fieldtype, **cell(value, df, doc)}


def get_table(doc, table_fieldname, columns, account=None):
	table_df = doc.meta.get_field(table_fieldname)
	rows = doc.get(table_fieldname) or []
	if not table_df or not rows:
		return None

	child_meta = frappe.get_meta(table_df.options)
	dfs = [child_meta.get_field(c) for c in columns if child_meta.has_field(c)]
	# drop columns that are empty on every row
	dfs = [df for df in dfs if any(r.get(df.fieldname) not in (None, "", 0) for r in rows)]
	if not dfs:
		return None

	return {
		"title": _(table_df.label),
		"columns": [_(df.label) for df in dfs],
		"numeric": [df.fieldtype in NUMERIC_FIELDTYPES for df in dfs],
		"rows": [[cell(r.get(df.fieldname), df, r) for df in dfs] for r in rows[:MAX_TABLE_ROWS]],
		"highlight": [
			bool(account) and any(r.get(f) == account for f in ACCOUNT_FIELDS) for r in rows[:MAX_TABLE_ROWS]
		],
		"total_rows": len(rows),
	}


def set_stock_issue_detail(doc, row, fields, tables):
	"""Material Issue: shipment, issued items with batch + supplier (replaces the plain items table)."""
	report = get_report_module()
	se = report.get_stock_entry_details([doc.name], doc.company)[0]
	items = se.get("issue_items") or []
	if not items:
		return

	shipment_fields = [
		(_("Customer Order"), se.get("customer_order"), "Customer Order"),
		(_("Shipment Ref"), se.get("shipment_ref"), None),
		(_("Customer"), se.get("shipment_customer"), "Customer"),
		(_("Customer Name"), se.get("shipment_customer_name")
			if se.get("shipment_customer_name") != se.get("shipment_customer") else None, None),
		(_("Customer Batch"), se.get("customer_batch"), None),
		(_("Invoice No"), se.get("shipment_invoice_no"), None),
	]
	existing = {f["label"] for f in fields}
	for label, value, link_doctype in shipment_fields:
		if value and label not in existing:
			fields.append({
				"label": label,
				"fieldtype": "Data",
				"group": "shipment",
				"v": cstr(value),
				"links": [[link_doctype, value, value]] if link_doctype else [],
			})

	row_items = report.get_issue_items_for_row(row, se)
	issue_table = {
		"title": _("Issued Items"),
		"columns": [_("Item"), _("Item Name"), _("Qty"), _("Batch"), _("Supplier"), _("Source Warehouse"),
			_("Expense Account")],
		"numeric": [False, False, True, False, False, False, False],
		"rows": [
			[
				cell(it.item_code, links=[["Item", it.item_code, it.item_code]]),
				cell(it.item_name),
				cell(f"{flt(it.qty):g} {it.uom or ''}".strip()),
				cell(", ".join(it.batches), links=[["Batch", b, b] for b in it.batches]),
				cell(", ".join(it.supplier_names) or _("Not found"),
					links=[["Supplier", s, n] for s, n in zip(it.suppliers, it.supplier_names)]),
				cell(it.s_warehouse, links=[["Warehouse", it.s_warehouse, it.s_warehouse]] if it.s_warehouse else []),
				cell(it.expense_account),
			]
			for it in items[:MAX_TABLE_ROWS]
		],
		"highlight": [len(row_items) < len(items) and it in row_items for it in items[:MAX_TABLE_ROWS]],
		"total_rows": len(items),
	}

	tables[:] = [t for t in tables if not (t and t["title"] == _("Items"))]
	tables.insert(0, issue_table)


def get_gl_entries_table(doc, account=None):
	gl_entries = frappe.get_all(
		"GL Entry",
		filters={"voucher_type": doc.doctype, "voucher_no": doc.name, "is_cancelled": 0},
		fields=["account", "party_type", "party", "debit", "credit", "against", "cost_center", "remarks"],
		order_by="creation, name",
		limit=MAX_TABLE_ROWS,
	)
	if not gl_entries:
		return None

	currency = frappe.get_cached_value("Company", doc.company, "default_currency") if doc.get("company") else None
	show_party = any(g.party for g in gl_entries)
	columns = [_("Account")] + ([_("Party")] if show_party else []) + [_("Debit"), _("Credit"), _("Against"), _("Cost Center")]

	rows = []
	for g in gl_entries:
		r = [cell(g.account)]
		if show_party:
			r.append(cell(g.party, links=[[g.party_type, g.party, g.party]] if g.party_type and g.party else []))
		r += [
			cell(fmt_money(g.debit, currency=currency) if flt(g.debit) else ""),
			cell(fmt_money(g.credit, currency=currency) if flt(g.credit) else ""),
			cell(shorten_against(g.against)),
			cell(g.cost_center),
		]
		rows.append(r)

	total_debit = sum(flt(g.debit) for g in gl_entries)
	total_credit = sum(flt(g.credit) for g in gl_entries)
	totals = [cell(_("Total"))] + ([cell("")] if show_party else []) + [
		cell(fmt_money(total_debit, currency=currency)),
		cell(fmt_money(total_credit, currency=currency)),
		cell(""),
		cell(""),
	]

	return {
		"title": _("Accounting Ledger Entries"),
		"totals": totals,
		"columns": columns,
		"numeric": [c in (_("Debit"), _("Credit")) for c in columns],
		"rows": rows,
		"highlight": [bool(account) and g.account == account for g in gl_entries],
		"total_rows": len(gl_entries),
	}


def shorten_against(against, limit=3):
	parts = [p.strip() for p in cstr(against).split(",") if p.strip()]
	if len(parts) <= limit:
		return ", ".join(parts)
	return ", ".join(parts[:limit]) + " " + _("(+{0} more)").format(len(parts) - limit)
