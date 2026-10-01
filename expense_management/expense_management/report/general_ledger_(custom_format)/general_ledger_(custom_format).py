# Copyright (c) 2026, MISL Holdings (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _, _dict
from frappe.utils import cstr, flt, getdate

from erpnext import get_company_currency, get_default_company
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
)
from erpnext.accounts.report.general_ledger.general_ledger import (
	get_data_with_opening_closing,
	get_gl_entries,
	get_translated_labels_for_totals,
	set_account_currency,
	validate_party,
)


def validate_custom_filters(filters, account_details):
	if not filters.get("company"):
		frappe.throw(_("{0} is mandatory").format(_("Company")))

	if filters.get("voucher_no") and (not filters.get("from_date") or not filters.get("to_date")):
		v_date = frappe.db.get_value("GL Entry", {"voucher_no": filters.get("voucher_no")}, "posting_date")
		if v_date:
			filters.setdefault("from_date", v_date)
			filters.setdefault("to_date", v_date)

	if not filters.get("from_date") and not filters.get("to_date"):
		frappe.throw(
			_("{0} and {1} are mandatory").format(frappe.bold(_("From Date")), frappe.bold(_("To Date")))
		)

	if filters.get("account"):
		if isinstance(filters.account, str):
			try:
				parsed = frappe.parse_json(filters.account)
				filters.account = parsed if isinstance(parsed, list) else [parsed]
			except Exception:
				filters.account = [filters.account]
		elif not isinstance(filters.account, list):
			filters.account = [filters.account]

		for account in filters.account:
			if not account_details.get(account):
				frappe.throw(_("Account {0} does not exists").format(account))

	if filters.get("from_date") and filters.get("to_date"):
		if getdate(filters.from_date) > getdate(filters.to_date):
			frappe.throw(_("From Date must be before To Date"))



def get_filter_summary_html(filters):
	account_html = ""
	if filters.get("account"):
		acc = filters.get("account")
		acc_str = ", ".join(acc) if isinstance(acc, list) else str(acc)
		if acc_str and acc_str.strip():
			account_html = f'<div style="font-size: 20px; font-weight: 700; color: #1e293b; text-align: center; margin: 10px 0 12px; background: #e2e8f0; padding: 8px 22px; border-radius: 6px; border: 1px solid #cbd5e1; display: inline-block;">{acc_str}</div>'

	other_parts = []
	if filters.get("voucher_no"):
		v_no = filters.get("voucher_no")
		v_str = ", ".join(v_no) if isinstance(v_no, list) else str(v_no)
		other_parts.append(f"<strong>{_('Voucher No')}:</strong> {v_str}")

	if filters.get("against_voucher_no"):
		avg_no = filters.get("against_voucher_no")
		avg_str = ", ".join(avg_no) if isinstance(avg_no, list) else str(avg_no)
		other_parts.append(f"<strong>{_('Against Voucher No')}:</strong> {avg_str}")

	if filters.get("party"):
		p_type = filters.get("party_type") or _("Party")
		party = filters.get("party")
		p_str = ", ".join(party) if isinstance(party, list) else str(party)
		other_parts.append(f"<strong>{p_type}:</strong> {p_str}")

	if filters.get("from_date") and filters.get("to_date"):
		other_parts.append(
			f"<strong>{_('Period')}:</strong> {filters.get('from_date')} {_('to')} {filters.get('to_date')}"
		)

	if filters.get("presentation_currency"):
		other_parts.append(f"<strong>{_('Currency')}:</strong> {filters.get('presentation_currency')}")

	details_html = ""
	if other_parts:
		details_str = " &nbsp;&nbsp;|&nbsp;&nbsp; ".join(other_parts)
		details_html = f'<div style="font-size: 14px; color: #334155; margin-top: 6px; line-height: 1.6;">{details_str}</div>'

	company_name = filters.get("company") or ""

	return f'''
	<div class="gl-custom-header-banner" style="text-align: center; padding: 16px 20px; margin-bottom: 16px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px;">
		<div style="font-size: 24px; font-weight: 800; color: #0f172a; letter-spacing: 0.5px;">{_("General Ledger")}</div>
		<div style="font-size: 15px; font-weight: 600; color: #475569; margin-top: 2px;">{company_name}</div>
		{account_html}
		{details_html}
	</div>
	'''


def execute(filters=None):
	if not filters:
		return [], []

	filters = frappe._dict(filters)

	account_details = {}

	if filters and filters.get("print_in_account_currency") and not filters.get("account"):
		frappe.throw(_("Select an account to print in account currency"))

	for acc in frappe.db.sql("""select name, is_group from tabAccount""", as_dict=1):
		account_details.setdefault(acc.name, acc)

	validate_custom_filters(filters, account_details)

	if filters.get("party"):
		if isinstance(filters.party, str):
			try:
				parsed = frappe.parse_json(filters.party)
				filters.party = parsed if isinstance(parsed, list) else [parsed]
			except Exception:
				filters.party = [filters.party]

	validate_party(filters)
	filters = set_account_currency(filters)

	columns = get_columns(filters)
	res = get_custom_result(filters, account_details)
	message = get_filter_summary_html(filters)

	return columns, res, message


def get_custom_result(filters, account_details):
	if not filters.get("categorize_by"):
		filters["categorize_by"] = "Categorize by Voucher (Consolidated)"

	if filters.get("include_default_book_entries") is None:
		filters["include_default_book_entries"] = 1

	accounting_dimensions = []
	if filters.get("include_dimensions"):
		accounting_dimensions = get_accounting_dimensions()

	gl_filters = filters.copy()
	gl_filters["show_remarks"] = 1

	gl_entries = get_gl_entries(gl_filters, accounting_dimensions)
	raw_data = get_data_with_opening_closing(gl_filters, account_details, accounting_dimensions, gl_entries)
	result = transform_to_custom_columns(raw_data, filters)
	return result


def should_show_account_column(filters):
	if filters.get("voucher_no"):
		account = filters.get("account")
		if not account:
			return True
		if isinstance(account, list) and len(account) == 0:
			return True
	return False


def get_columns(filters):
	if filters.get("presentation_currency"):
		currency = filters["presentation_currency"]
	else:
		company = filters.get("company") or get_default_company()
		filters["presentation_currency"] = currency = get_company_currency(company)

	company_currency = get_company_currency(filters.get("company") or get_default_company())

	if (
		filters.get("show_amount_in_company_currency")
		and filters["presentation_currency"] != company_currency
	):
		frappe.throw(
			_(
				f'Presentation Currency cannot be {frappe.bold(filters["presentation_currency"])} , When {frappe.bold("Show Credit / Debit in Company Currency")} is enabled.'
			)
		)

	columns = [
		{
			"label": _("Date"),
			"fieldname": "posting_date",
			"fieldtype": "Date",
			"width": 110,
		},
		{
			"label": _("Party"),
			"fieldname": "party",
			"fieldtype": "Data",
			"width": 160,
		},
		{
			"label": _("Voucher No"),
			"fieldname": "voucher_no",
			"fieldtype": "Dynamic Link",
			"options": "voucher_type",
			"width": 200,
		},
		{
			"label": _("Dr"),
			"fieldname": "debit",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 150,
		},
		{
			"label": _("Cr"),
			"fieldname": "credit",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 150,
		},
		{
			"label": _("Balance"),
			"fieldname": "balance",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 160,
		},
		{
			"label": _("Voucher Type"),
			"fieldname": "voucher_type",
			"fieldtype": "Data",
			"width": 140,
		},
		{
			"label": _("Account"),
			"fieldname": "account",
			"fieldtype": "Link",
			"options": "Account",
			"width": 200,
		},
		{
			"label": _("Against Account"),
			"fieldname": "against",
			"fieldtype": "Data",
			"width": 200,
		},
		{
			"label": _("Description"),
			"fieldname": "description",
			"fieldtype": "Data",
			"width": 280,
		},
	]

	return columns


def get_voucher_details_map(raw_data):
	vouchers_by_type = {}
	for row in raw_data:
		v_type = row.get("voucher_type")
		v_no = row.get("voucher_no")
		if v_type and v_no:
			vouchers_by_type.setdefault(v_type, set()).add(v_no)

	voucher_details = {}

	# 1. Purchase Invoices
	if pi_names := list(vouchers_by_type.get("Purchase Invoice", [])):
		try:
			pi_rows = frappe.get_all(
				"Purchase Invoice",
				filters={"name": ["in", pi_names]},
				fields=["name", "bill_no", "supplier_name", "remarks"],
			)
			for pi in pi_rows:
				voucher_details[("Purchase Invoice", pi.name)] = pi
		except Exception:
			pass

	# 2. Payment Entries
	if pe_names := list(vouchers_by_type.get("Payment Entry", [])):
		try:
			pe_rows = frappe.get_all(
				"Payment Entry",
				filters={"name": ["in", pe_names]},
				fields=["name", "reference_no", "party_name", "party", "party_type", "payment_type", "remarks"],
			)
			for pe in pe_rows:
				voucher_details[("Payment Entry", pe.name)] = pe
		except Exception:
			pass

	# 3. Journal Entries
	if je_names := list(vouchers_by_type.get("Journal Entry", [])):
		try:
			je_rows = frappe.get_all(
				"Journal Entry",
				filters={"name": ["in", je_names]},
				fields=["name", "cheque_no", "user_remark", "remarks", "voucher_type as je_voucher_type"],
			)
			for je in je_rows:
				voucher_details[("Journal Entry", je.name)] = je
		except Exception:
			pass

	# 4. Sales Invoices
	if si_names := list(vouchers_by_type.get("Sales Invoice", [])):
		try:
			si_rows = frappe.get_all(
				"Sales Invoice",
				filters={"name": ["in", si_names]},
				fields=["name", "customer_name", "remarks"],
			)
			for si in si_rows:
				voucher_details[("Sales Invoice", si.name)] = si
		except Exception:
			pass

	# 5. Expense (Expense Management)
	if exp_names := list(vouchers_by_type.get("Expense", [])):
		try:
			exp_rows = frappe.get_all(
				"Expense",
				filters={"name": ["in", exp_names]},
				fields=["name", "description", "remarks"],
			)
			for exp in exp_rows:
				voucher_details[("Expense", exp.name)] = exp
		except Exception:
			pass

	# 6. Expense Claim
	if ec_names := list(vouchers_by_type.get("Expense Claim", [])):
		try:
			ec_rows = frappe.get_all(
				"Expense Claim",
				filters={"name": ["in", ec_names]},
				fields=["name", "employee_name", "remarks"],
			)
			for ec in ec_rows:
				voucher_details[("Expense Claim", ec.name)] = ec
		except Exception:
			pass

	# 7. Stock Entry
	if se_names := list(vouchers_by_type.get("Stock Entry", [])):
		try:
			se_rows = frappe.get_all(
				"Stock Entry",
				filters={"name": ["in", se_names]},
				fields=["name", "purpose", "remarks"],
			)
			for se in se_rows:
				voucher_details[("Stock Entry", se.name)] = se
		except Exception:
			pass

	return voucher_details


def get_invoice_cheque_no(row, v_doc):
	v_type = row.get("voucher_type")
	v_no = row.get("voucher_no")
	if not v_type or not v_no:
		return ""

	if v_type == "Purchase Invoice":
		bill_no = (v_doc.get("bill_no") if v_doc else None) or row.get("bill_no")
		return bill_no.strip() if bill_no and str(bill_no).strip() else v_no
	elif v_type == "Payment Entry":
		ref_no = v_doc.get("reference_no") if v_doc else None
		return ref_no.strip() if ref_no and str(ref_no).strip() else v_no
	elif v_type == "Journal Entry":
		cheque_no = v_doc.get("cheque_no") if v_doc else None
		return cheque_no.strip() if cheque_no and str(cheque_no).strip() else v_no
	elif v_type == "Sales Invoice":
		return v_no
	else:
		return v_no


def get_description(row, v_doc):
	v_type = row.get("voucher_type")
	if not v_type:
		return ""

	if v_type == "Purchase Invoice":
		return (
			(v_doc.get("supplier_name") if v_doc else None)
			or row.get("party_name")
			or row.get("party")
			or row.get("against")
			or ""
		)
	elif v_type == "Payment Entry":
		return (
			(v_doc.get("party_name") if v_doc else None)
			or row.get("party_name")
			or row.get("party")
			or row.get("against")
			or ""
		)
	elif v_type == "Sales Invoice":
		return (
			(v_doc.get("customer_name") if v_doc else None)
			or row.get("party_name")
			or row.get("party")
			or row.get("against")
			or ""
		)
	elif v_type == "Journal Entry":
		user_rmk = v_doc.get("user_remark") if v_doc else None
		if user_rmk and str(user_rmk).strip():
			return str(user_rmk).strip()
		return row.get("against") or _("Journal Entry")
	elif v_type == "Expense":
		exp_desc = v_doc.get("description") if v_doc else None
		if exp_desc and str(exp_desc).strip():
			return str(exp_desc).strip()
		return row.get("against") or _("Expense")
	elif v_type == "Expense Claim":
		return (
			(v_doc.get("employee_name") if v_doc else None)
			or row.get("party_name")
			or row.get("against")
			or _("Expense Claim")
		)
	elif v_type == "Stock Entry":
		purpose = v_doc.get("purpose") if v_doc else None
		return purpose or row.get("against") or _("Stock Entry")
	else:
		return row.get("party_name") or row.get("against") or row.get("account") or ""


def get_remarks(row, v_doc, desc):
	raw_remarks = row.get("remarks")
	if (
		raw_remarks is None
		or str(raw_remarks).strip() == ""
		or str(raw_remarks).strip().lower() in ["no remarks", "no remark", "none", "null"]
	):
		raw_remarks = None
	else:
		raw_remarks = str(raw_remarks).strip()

	if raw_remarks:
		return raw_remarks

	# If doc has remarks from doctype level, check that too
	doc_remarks = v_doc.get("remarks") if v_doc else None
	if (
		doc_remarks
		and str(doc_remarks).strip()
		and str(doc_remarks).strip().lower() not in ["no remarks", "no remark", "none", "null"]
	):
		return str(doc_remarks).strip()

	# Generate meaningful description based on voucher type
	v_type = row.get("voucher_type")
	if not v_type:
		return ""

	against = row.get("against") or ""

	if v_type == "Purchase Invoice":
		supp = (v_doc.get("supplier_name") if v_doc else None) or row.get("party_name") or row.get("party")
		if supp:
			return f"Purchase Invoice for {supp}"
		return f"Purchase Invoice against {against}" if against else "Purchase Invoice"

	elif v_type == "Payment Entry":
		party = (v_doc.get("party_name") if v_doc else None) or row.get("party_name") or row.get("party")
		p_type = v_doc.get("payment_type") if v_doc else None
		if p_type == "Pay":
			return f"Payment to {party}" if party else "Payment Entry"
		elif p_type == "Receive":
			return f"Payment received from {party}" if party else "Payment Entry"
		return f"Payment Entry - {party}" if party else "Payment Entry"

	elif v_type == "Journal Entry":
		user_rmk = v_doc.get("user_remark") if v_doc else None
		if user_rmk and str(user_rmk).strip():
			return str(user_rmk).strip()
		return f"Journal Entry against {against}" if against else "Journal Entry"

	elif v_type == "Sales Invoice":
		cust = (v_doc.get("customer_name") if v_doc else None) or row.get("party_name") or row.get("party")
		if cust:
			return f"Sales Invoice for {cust}"
		return f"Sales Invoice against {against}" if against else "Sales Invoice"

	elif v_type == "Expense":
		exp_desc = v_doc.get("description") if v_doc else None
		if exp_desc and str(exp_desc).strip():
			return f"Expense - {str(exp_desc).strip()}"
		return f"Expense against {against}" if against else "Expense"

	elif v_type == "Expense Claim":
		emp = (v_doc.get("employee_name") if v_doc else None) or row.get("party_name")
		if emp:
			return f"Expense Claim for {emp}"
		return f"Expense Claim against {against}" if against else "Expense Claim"

	elif v_type == "Stock Entry":
		purpose = v_doc.get("purpose") if v_doc else None
		if purpose:
			return f"Stock Entry ({purpose})"
		return f"Stock Entry against {against}" if against else "Stock Entry"

	else:
		p_or_a = row.get("party_name") or against or desc
		return f"{v_type} - {p_or_a}" if p_or_a else str(v_type)


def transform_to_custom_columns(raw_data, filters):
	labels = get_translated_labels_for_totals()
	voucher_details_map = get_voucher_details_map(raw_data)

	selected_currency = (
		filters.get("presentation_currency")
		or filters.get("account_currency")
		or filters.get("company_currency")
		or get_company_currency(filters.get("company") or get_default_company())
	)

	result = []
	running_balance = 0.0

def get_party_value(row, v_doc):
	party = row.get("party_name") or row.get("party")
	if party and str(party).strip():
		return str(party).strip()
	if v_doc:
		return (
			v_doc.get("party_name")
			or v_doc.get("supplier_name")
			or v_doc.get("customer_name")
			or v_doc.get("employee_name")
			or ""
		)
	return ""


def transform_to_custom_columns(raw_data, filters):
	labels = get_translated_labels_for_totals()
	voucher_details_map = get_voucher_details_map(raw_data)

	selected_currency = (
		filters.get("presentation_currency")
		or filters.get("account_currency")
		or filters.get("company_currency")
		or get_company_currency(filters.get("company") or get_default_company())
	)

	result = []
	running_balance = 0.0

	for row in raw_data:
		acc = row.get("account")
		is_entry = bool(row.get("posting_date"))

		# 1. Check if Closing row first (since Closing label contains "Opening")
		if acc == labels["closing"] or (not is_entry and acc and _("Closing") in str(acc)):
			dr = round(flt(row.get("debit")), 4)
			cr = round(flt(row.get("credit")), 4)
			closing_balance = round(dr - cr, 4)
			if abs(closing_balance) < 1e-6:
				closing_balance = 0.0

			label = str(acc) if (acc and acc != labels["closing"]) else _("Closing (Opening + Total)")

			result.append(
				{
					"posting_date": "",
					"party": label,
					"voucher_no": "",
					"debit": dr if abs(dr) >= 1e-6 else None,
					"credit": cr if abs(cr) >= 1e-6 else None,
					"balance": closing_balance,
					"voucher_type": "",
					"account": "",
					"against": "",
					"description": "",
					"currency": selected_currency,
				}
			)

		# 2. Check if Total row
		elif acc == labels["total"] or (
			not is_entry and acc and _("Total") in str(acc) and _("Closing") not in str(acc)
		):
			dr = round(flt(row.get("debit")), 4)
			cr = round(flt(row.get("credit")), 4)
			label = str(acc) if (acc and acc != labels["total"]) else _("Total")

			result.append(
				{
					"posting_date": "",
					"party": label,
					"voucher_no": "",
					"debit": dr if abs(dr) >= 1e-6 else None,
					"credit": cr if abs(cr) >= 1e-6 else None,
					"balance": None,
					"voucher_type": "",
					"account": "",
					"against": "",
					"description": "",
					"currency": selected_currency,
				}
			)

		# 3. Check if Opening row
		elif acc == labels["opening"] or (
			not is_entry and acc and _("Opening") in str(acc) and _("Closing") not in str(acc)
		):
			dr = round(flt(row.get("debit")), 4)
			cr = round(flt(row.get("credit")), 4)
			running_balance = round(dr - cr, 4)
			if abs(running_balance) < 1e-6:
				running_balance = 0.0

			label = str(acc) if (acc and acc != labels["opening"]) else _("Opening Balance")

			result.append(
				{
					"posting_date": filters.get("from_date"),
					"party": label,
					"voucher_no": "",
					"debit": dr if abs(dr) >= 1e-6 else None,
					"credit": cr if abs(cr) >= 1e-6 else None,
					"balance": running_balance,
					"voucher_type": "",
					"account": "",
					"against": "",
					"description": "",
					"currency": selected_currency,
				}
			)

		# 4. Normal Transaction Entry
		elif is_entry:
			v_type = row.get("voucher_type") or ""
			v_no = row.get("voucher_no") or ""
			v_doc = voucher_details_map.get((v_type, v_no), {})

			dr = round(flt(row.get("debit")), 4)
			cr = round(flt(row.get("credit")), 4)
			running_balance += (dr - cr)
			rounded_balance = round(running_balance, 4)
			if abs(rounded_balance) < 1e-6:
				rounded_balance = 0.0

			party_val = get_party_value(row, v_doc)
			desc = get_description(row, v_doc)
			rmks = get_remarks(row, v_doc, desc)

			result.append(
				{
					"posting_date": row.get("posting_date"),
					"party": party_val,
					"voucher_no": v_no,
					"debit": dr if abs(dr) >= 1e-6 else None,
					"credit": cr if abs(cr) >= 1e-6 else None,
					"balance": rounded_balance,
					"voucher_type": v_type,
					"account": acc or "",
					"against": row.get("against") or "",
					"description": rmks or desc,
					"currency": selected_currency,
				}
			)

		# 5. Empty / separator row (e.g. in categorized grouped views)
		else:
			result.append(
				{
					"posting_date": "",
					"party": "",
					"voucher_no": "",
					"debit": None,
					"credit": None,
					"balance": None,
					"voucher_type": "",
					"account": "",
					"against": "",
					"description": "",
					"currency": selected_currency,
				}
			)

	return result
