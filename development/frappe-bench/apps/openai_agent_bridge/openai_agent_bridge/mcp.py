from __future__ import annotations

from frappe_mcp import MCP

from .mcp_tools import (
	get_document,
	get_doctype_schema,
	get_field_options,
	get_report_columns,
	list_documents,
	list_reports,
	run_query_report,
)


mcp = MCP(name="Riley Assistant Frappe MCP")

mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": False})(get_document)
mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": False})(list_documents)
mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": False})(get_doctype_schema)
mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": False})(get_field_options)
mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": False})(list_reports)
mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": False})(get_report_columns)
mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": False})(run_query_report)


@mcp.register()
def handle_mcp():
	return None
