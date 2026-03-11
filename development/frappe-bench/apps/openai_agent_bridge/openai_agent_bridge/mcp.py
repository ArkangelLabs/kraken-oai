from __future__ import annotations

import json
from typing import Any, Callable

import frappe
from werkzeug.wrappers import Response

from .mcp_tools import (
	check_doctype_exists,
	check_document_exists,
	count_documents,
	find_doctypes,
	get_document,
	get_document_count,
	get_doctype_schema,
	get_doctypes_in_module,
	get_field_options,
	get_module_list,
	get_naming_info,
	get_report_meta,
	get_report_columns,
	get_required_fields,
	list_documents,
	list_reports,
	ping,
	run_doctype_report,
	run_query_report,
)

JSONRPC_VERSION = "2.0"
PROTOCOL_VERSION = "2025-03-26"
SERVER_NAME = "Riley Assistant Frappe MCP"
SERVER_VERSION = "0.1.0"


def _tool_definitions() -> dict[str, dict[str, Any]]:
	return {
		"ping": {
			"description": "Simple health check for the local MCP surface.",
			"inputSchema": {"type": "object", "properties": {}},
			"annotations": {"readOnlyHint": True, "openWorldHint": False},
			"fn": ping,
		},
		"check_doctype_exists": {
			"description": "Check whether a DocType exists.",
			"inputSchema": {
				"type": "object",
				"properties": {"doctype": {"type": "string"}},
				"required": ["doctype"],
			},
			"annotations": {"readOnlyHint": True, "openWorldHint": False},
			"fn": check_doctype_exists,
		},
		"check_document_exists": {
			"description": "Check whether a document exists.",
			"inputSchema": {
				"type": "object",
				"properties": {"doctype": {"type": "string"}, "name": {"type": "string"}},
				"required": ["doctype", "name"],
			},
			"annotations": {"readOnlyHint": True, "openWorldHint": False},
			"fn": check_document_exists,
		},
		"find_doctypes": {
			"description": "Search available DocTypes.",
			"inputSchema": {
				"type": "object",
				"properties": {
					"search_term": {"type": ["string", "null"]},
					"module": {"type": ["string", "null"]},
					"limit": {"type": "integer"},
					"is_table": {"type": ["boolean", "null"]},
					"is_single": {"type": ["boolean", "null"]},
					"is_custom": {"type": ["boolean", "null"]},
				},
			},
			"annotations": {"readOnlyHint": True, "openWorldHint": False},
			"fn": find_doctypes,
		},
		"get_module_list": {
			"description": "List modules visible to the current user.",
			"inputSchema": {"type": "object", "properties": {}},
			"annotations": {"readOnlyHint": True, "openWorldHint": False},
			"fn": get_module_list,
		},
		"get_doctypes_in_module": {
			"description": "List DocTypes in a module.",
			"inputSchema": {
				"type": "object",
				"properties": {"module": {"type": "string"}},
				"required": ["module"],
			},
			"annotations": {"readOnlyHint": True, "openWorldHint": False},
			"fn": get_doctypes_in_module,
		},
		"get_document": {
			"description": "Read a single document that the current user can access.",
			"inputSchema": {
				"type": "object",
				"properties": {
					"doctype": {"type": "string"},
					"name": {"type": "string"},
					"fields": {"type": ["array", "null"], "items": {"type": "string"}},
				},
				"required": ["doctype", "name"],
			},
			"annotations": {"readOnlyHint": True, "openWorldHint": False},
			"fn": get_document,
		},
		"list_documents": {
			"description": "List documents the current user can access.",
			"inputSchema": {
				"type": "object",
				"properties": {
					"doctype": {"type": "string"},
					"fields": {"type": ["array", "null"], "items": {"type": "string"}},
					"filters": {"type": ["object", "null"], "additionalProperties": {}},
					"limit": {"type": "integer"},
					"order_by": {"type": ["string", "null"]},
				},
				"required": ["doctype"],
			},
			"annotations": {"readOnlyHint": True, "openWorldHint": False},
			"fn": list_documents,
		},
		"count_documents": {
			"description": "Count documents the current user can access.",
			"inputSchema": {
				"type": "object",
				"properties": {
					"doctype": {"type": "string"},
					"filters": {"type": ["object", "null"], "additionalProperties": {}},
				},
				"required": ["doctype"],
			},
			"annotations": {"readOnlyHint": True, "openWorldHint": False},
			"fn": count_documents,
		},
		"get_document_count": {
			"description": "Compatibility alias for document counts.",
			"inputSchema": {
				"type": "object",
				"properties": {
					"doctype": {"type": "string"},
					"filters": {"type": ["object", "null"], "additionalProperties": {}},
				},
				"required": ["doctype"],
			},
			"annotations": {"readOnlyHint": True, "openWorldHint": False},
			"fn": get_document_count,
		},
		"get_doctype_schema": {
			"description": "Return basic DocType metadata for read-only exploration.",
			"inputSchema": {
				"type": "object",
				"properties": {"doctype": {"type": "string"}},
				"required": ["doctype"],
			},
			"annotations": {"readOnlyHint": True, "openWorldHint": False},
			"fn": get_doctype_schema,
		},
		"get_required_fields": {
			"description": "Return required fields for a DocType.",
			"inputSchema": {
				"type": "object",
				"properties": {"doctype": {"type": "string"}},
				"required": ["doctype"],
			},
			"annotations": {"readOnlyHint": True, "openWorldHint": False},
			"fn": get_required_fields,
		},
		"get_naming_info": {
			"description": "Describe the naming strategy for a DocType.",
			"inputSchema": {
				"type": "object",
				"properties": {"doctype": {"type": "string"}},
				"required": ["doctype"],
			},
			"annotations": {"readOnlyHint": True, "openWorldHint": False},
			"fn": get_naming_info,
		},
		"get_field_options": {
			"description": "Resolve Link or Select field options for the current user.",
			"inputSchema": {
				"type": "object",
				"properties": {
					"doctype": {"type": "string"},
					"fieldname": {"type": "string"},
					"filters": {"type": ["object", "null"], "additionalProperties": {}},
					"limit": {"type": "integer"},
				},
				"required": ["doctype", "fieldname"],
			},
			"annotations": {"readOnlyHint": True, "openWorldHint": False},
			"fn": get_field_options,
		},
		"list_reports": {
			"description": "List reports visible to the current user.",
			"inputSchema": {
				"type": "object",
				"properties": {"module": {"type": ["string", "null"]}},
			},
			"annotations": {"readOnlyHint": True, "openWorldHint": False},
			"fn": list_reports,
		},
		"get_report_columns": {
			"description": "Describe the visible columns for a query report.",
			"inputSchema": {
				"type": "object",
				"properties": {"report_name": {"type": "string"}},
				"required": ["report_name"],
			},
			"annotations": {"readOnlyHint": True, "openWorldHint": False},
			"fn": get_report_columns,
		},
		"get_report_meta": {
			"description": "Describe a report and its columns.",
			"inputSchema": {
				"type": "object",
				"properties": {"report_name": {"type": "string"}},
				"required": ["report_name"],
			},
			"annotations": {"readOnlyHint": True, "openWorldHint": False},
			"fn": get_report_meta,
		},
		"run_query_report": {
			"description": "Run a query report with filters and return a bounded result set.",
			"inputSchema": {
				"type": "object",
				"properties": {
					"report_name": {"type": "string"},
					"filters": {"type": ["object", "null"], "additionalProperties": {}},
					"limit": {"type": "integer"},
				},
				"required": ["report_name"],
			},
			"annotations": {"readOnlyHint": True, "openWorldHint": False},
			"fn": run_query_report,
		},
		"run_doctype_report": {
			"description": "Run a simple doctype-backed listing query.",
			"inputSchema": {
				"type": "object",
				"properties": {
					"doctype": {"type": "string"},
					"fields": {"type": ["array", "null"], "items": {"type": "string"}},
					"filters": {"type": ["object", "null"], "additionalProperties": {}},
					"limit": {"type": "integer"},
					"order_by": {"type": ["string", "null"]},
				},
				"required": ["doctype"],
			},
			"annotations": {"readOnlyHint": True, "openWorldHint": False},
			"fn": run_doctype_report,
		},
	}


def _json_response(payload: dict[str, Any], status_code: int = 200) -> Response:
	return Response(json.dumps(payload), status=status_code, mimetype="application/json")


def _success(request_id: Any, result: dict[str, Any]) -> Response:
	return _json_response({"jsonrpc": JSONRPC_VERSION, "id": request_id, "result": result})


def _error(request_id: Any, code: int, message: str, status_code: int = 200) -> Response:
	return _json_response(
		{"jsonrpc": JSONRPC_VERSION, "id": request_id, "error": {"code": code, "message": message}},
		status_code=status_code,
	)


def _serialize_tool_call_result(result: Any) -> dict[str, Any]:
	return {"content": [{"type": "text", "text": json.dumps(result)}], "isError": False}


def _call_tool(tool_fn: Callable[..., Any], arguments: dict[str, Any] | None) -> dict[str, Any]:
	arguments = arguments or {}
	result = tool_fn(**arguments)
	return _serialize_tool_call_result(result)


@frappe.whitelist(methods=["POST"])
def handle_mcp() -> Response:
	try:
		payload = frappe.request.get_json(force=True) or {}
	except Exception:
		return _error(None, -32700, "Parse error", status_code=400)

	request_id = payload.get("id")
	method = payload.get("method")
	params = payload.get("params") or {}
	tools = _tool_definitions()

	if method == "initialize":
		return _success(
			request_id,
			{
				"protocolVersion": PROTOCOL_VERSION,
				"serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
				"capabilities": {"tools": {"listChanged": False}},
			},
		)

	if method == "ping":
		return _success(request_id, {})

	if method == "tools/list":
		return _success(
			request_id,
			{
				"tools": [
					{
						"name": name,
						"description": tool["description"],
						"inputSchema": tool["inputSchema"],
						"annotations": tool["annotations"],
					}
					for name, tool in tools.items()
				]
			},
		)

	if method == "tools/call":
		tool_name = params.get("name")
		tool = tools.get(tool_name)
		if not tool:
			return _error(request_id, -32601, f"Unknown tool: {tool_name}")
		try:
			return _success(request_id, _call_tool(tool["fn"], params.get("arguments")))
		except Exception as exc:
			frappe.log_error(title="OpenAI Agent MCP Tool Error", message=frappe.get_traceback())
			return _success(
				request_id,
				{"content": [{"type": "text", "text": str(exc)}], "isError": True},
			)

	return _error(request_id, -32601, f"Method not found: {method}")
