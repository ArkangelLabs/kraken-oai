from __future__ import annotations

from typing import Any

import frappe


def _normalize_filters(filters: dict[str, Any] | None) -> dict[str, Any]:
	return filters or {}


def _get_report_result(report_name: str, filters: dict[str, Any] | None = None) -> dict[str, Any]:
	return frappe.get_attr("frappe.desk.query_report.run")(
		report_name=report_name,
		filters=_normalize_filters(filters),
	)


def ping() -> dict[str, Any]:
	"""Simple health check for the local MCP surface."""
	return {"ok": True}


def check_doctype_exists(doctype: str) -> dict[str, Any]:
	"""Check whether a DocType exists."""
	return {"doctype": doctype, "exists": bool(frappe.db.exists("DocType", doctype))}


def check_document_exists(doctype: str, name: str) -> dict[str, Any]:
	"""Check whether a document exists."""
	return {"doctype": doctype, "name": name, "exists": bool(frappe.db.exists(doctype, name))}


def find_doctypes(
	search_term: str | None = None,
	module: str | None = None,
	limit: int = 20,
	is_table: bool | None = None,
	is_single: bool | None = None,
	is_custom: bool | None = None,
) -> list[dict[str, Any]]:
	"""Search available DocTypes."""
	filters: dict[str, Any] = {}
	if module:
		filters["module"] = module
	if is_table is not None:
		filters["istable"] = 1 if is_table else 0
	if is_single is not None:
		filters["issingle"] = 1 if is_single else 0
	if is_custom is not None:
		filters["custom"] = 1 if is_custom else 0

	or_filters = {}
	if search_term:
		or_filters = {"name": ["like", f"%{search_term}%"]}

	return frappe.get_list(
		"DocType",
		fields=["name", "module", "issingle", "istable", "custom"],
		filters=filters,
		or_filters=or_filters,
		limit_page_length=max(1, min(limit, 100)),
		order_by="modified desc",
	)


def get_module_list() -> list[dict[str, Any]]:
	"""List modules visible to the current user."""
	return frappe.get_list("Module Def", fields=["name"], order_by="name asc", limit_page_length=500)


def get_doctypes_in_module(module: str) -> list[dict[str, Any]]:
	"""List DocTypes in a module."""
	return frappe.get_list(
		"DocType",
		fields=["name", "issingle", "istable", "custom"],
		filters={"module": module},
		order_by="name asc",
		limit_page_length=500,
	)


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


def count_documents(doctype: str, filters: dict[str, Any] | None = None) -> dict[str, Any]:
	"""Count documents the current user can access."""
	return {
		"doctype": doctype,
		"count": frappe.db.count(doctype, filters=_normalize_filters(filters)),
	}


def get_document_count(doctype: str, filters: dict[str, Any] | None = None) -> dict[str, Any]:
	"""Compatibility alias for document counts."""
	return count_documents(doctype=doctype, filters=filters)


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


def get_required_fields(doctype: str) -> list[dict[str, Any]]:
	"""Return required fields for a DocType."""
	meta = frappe.get_meta(doctype)
	return [
		{
			"fieldname": field.fieldname,
			"label": field.label,
			"fieldtype": field.fieldtype,
			"options": field.options,
		}
		for field in meta.fields
		if field.reqd and field.fieldtype not in {"Section Break", "Column Break", "Tab Break"}
	]


def get_naming_info(doctype: str) -> dict[str, Any]:
	"""Describe the naming strategy for a DocType."""
	meta = frappe.get_meta(doctype)
	return {
		"doctype": doctype,
		"autoname": meta.autoname,
		"title_field": meta.title_field,
		"search_fields": meta.search_fields,
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


def get_report_meta(report_name: str) -> dict[str, Any]:
	"""Describe a report and its columns."""
	report = frappe.get_doc("Report", report_name)
	result = _get_report_result(report.name)
	return {
		"name": report.name,
		"module": report.module,
		"ref_doctype": report.ref_doctype,
		"report_type": report.report_type,
		"columns": result.get("columns") or [],
		"filters": report.filters,
	}


def get_report_columns(report_name: str) -> list[dict[str, Any]]:
	"""Describe the visible columns for a query report."""
	report_result = _get_report_result(report_name)
	return report_result.get("columns") or []


def run_query_report(
	report_name: str, filters: dict[str, Any] | None = None, limit: int = 50
) -> dict[str, Any]:
	"""Run a query report with filters and return a bounded result set."""
	result = _get_report_result(report_name, filters)
	rows = result.get("result") or []
	result["result"] = rows[: max(1, min(limit, 200))]
	return result


def run_doctype_report(
	doctype: str,
	fields: list[str] | None = None,
	filters: dict[str, Any] | None = None,
	limit: int = 20,
	order_by: str | None = None,
) -> dict[str, Any]:
	"""Run a simple doctype-backed listing query."""
	return {
		"doctype": doctype,
		"rows": list_documents(
			doctype=doctype,
			fields=fields,
			filters=filters,
			limit=limit,
			order_by=order_by,
		),
	}
