from __future__ import annotations

from typing import Any

import frappe


def _normalize_filters(filters: dict[str, Any] | None) -> dict[str, Any]:
	return filters or {}


def get_document(doctype: str, name: str, fields: list[str] | None = None) -> dict[str, Any]:
	"""Read a single document that the current user can access."""
	document = frappe.get_doc(doctype, name).as_dict(no_nulls=True)
	if not fields:
		return document
	return {field: document.get(field) for field in fields}


def list_documents(
	doctype: str,
	fields: list[str] | None = None,
	filters: dict[str, Any] | None = None,
	limit: int = 20,
	order_by: str | None = None,
) -> list[dict[str, Any]]:
	"""List documents the current user can access."""
	return frappe.get_list(
		doctype,
		fields=fields or ["name"],
		filters=_normalize_filters(filters),
		limit_page_length=max(1, min(limit, 100)),
		order_by=order_by,
	)


def get_doctype_schema(doctype: str) -> dict[str, Any]:
	"""Return basic DocType metadata for read-only exploration."""
	meta = frappe.get_meta(doctype)
	return {
		"name": meta.name,
		"module": meta.module,
		"search_fields": meta.search_fields,
		"title_field": meta.title_field,
		"fields": [
			{
				"fieldname": field.fieldname,
				"label": field.label,
				"fieldtype": field.fieldtype,
				"options": field.options,
				"reqd": field.reqd,
				"read_only": field.read_only,
				"hidden": field.hidden,
			}
			for field in meta.fields
		],
	}


def get_field_options(
	doctype: str, fieldname: str, filters: dict[str, Any] | None = None, limit: int = 20
) -> list[dict[str, Any]] | list[str]:
	"""Resolve Link or Select field options for the current user."""
	meta = frappe.get_meta(doctype)
	field = meta.get_field(fieldname)
	if not field:
		frappe.throw(f"Field {fieldname} was not found on {doctype}.")

	if field.fieldtype == "Select":
		return [option.strip() for option in (field.options or "").split("\n") if option.strip()]

	if field.fieldtype != "Link" or not field.options:
		frappe.throw(f"Field {fieldname} on {doctype} is not a Link or Select field.")

	return frappe.get_list(
		field.options,
		fields=["name"],
		filters=_normalize_filters(filters),
		limit_page_length=max(1, min(limit, 100)),
	)


def list_reports(module: str | None = None) -> list[dict[str, Any]]:
	"""List reports visible to the current user."""
	filters = {"disabled": 0}
	if module:
		filters["module"] = module
	return frappe.get_list("Report", filters=filters, fields=["name", "ref_doctype", "report_type", "module"])


def get_report_columns(report_name: str) -> list[dict[str, Any]]:
	"""Describe the visible columns for a query report."""
	report = frappe.get_doc("Report", report_name)
	report_result = frappe.get_attr("frappe.desk.query_report.run")(report_name=report.name)
	return report_result.get("columns") or []


def run_query_report(
	report_name: str, filters: dict[str, Any] | None = None, limit: int = 50
) -> dict[str, Any]:
	"""Run a query report with filters and return a bounded result set."""
	result = frappe.get_attr("frappe.desk.query_report.run")(
		report_name=report_name,
		filters=_normalize_filters(filters),
	)
	rows = result.get("result") or []
	result["result"] = rows[: max(1, min(limit, 200))]
	return result
