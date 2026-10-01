# Copyright (c) 2026, MISL Holdings (Pvt) Ltd and contributors
# For license information, please see license.txt

import importlib
import frappe
import frappe.desk.query_report
import erpnext.accounts.report.general_ledger.general_ledger as gl_module
from expense_management.expense_management.doctype.expense_management_settings.expense_management_settings import (
	is_override_gl_enabled,
)

_original_gl_execute = gl_module.execute
_original_get_script = frappe.desk.query_report.get_script


def custom_gl_execute(filters=None):
	if is_override_gl_enabled():
		custom_module = importlib.import_module(
			"expense_management.expense_management.report.general_ledger_(custom_format).general_ledger_(custom_format)"
		)
		return custom_module.execute(filters)
	return _original_gl_execute(filters)


# Monkeypatch Python execute on import
gl_module.execute = custom_gl_execute


@frappe.whitelist()
def get_script(report_name):
	if report_name == "General Ledger" and is_override_gl_enabled():
		res = _original_get_script("General Ledger (Custom Format)")
		if res and isinstance(res, dict) and res.get("script"):
			res["script"] = res["script"].replace(
				'frappe.query_reports["General Ledger (Custom Format)"]',
				'frappe.query_reports["General Ledger"]',
			)
		return res

	return _original_get_script(report_name)


# Monkeypatch get_script on module as well
frappe.desk.query_report.get_script = get_script
