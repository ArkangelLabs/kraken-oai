from __future__ import annotations

import json
from pathlib import Path

import frappe


ROLE_OPENAI_AGENT_USER = "OpenAI Agent User"
WORKSPACE_NAME = "Riley Assistant"
STANDARD_TARGETS = (
	("Page", "openai-agent-chat", Path("openai_agent_bridge/page/openai_agent_chat/openai_agent_chat.json")),
	("DocType", "OpenAI Agent", Path("openai_agent_bridge/doctype/openai_agent/openai_agent.json")),
	(
		"DocType",
		"OpenAI Agent MCP Profile",
		Path("openai_agent_bridge/doctype/openai_agent_mcp_profile/openai_agent_mcp_profile.json"),
	),
	(
		"DocType",
		"OpenAI Agent Access",
		Path("openai_agent_bridge/doctype/openai_agent_access/openai_agent_access.json"),
	),
)


def after_install() -> None:
	ensure_role()
	ensure_standard_targets(force=True)
	ensure_page_title()
	ensure_workspace()


def after_migrate() -> None:
	ensure_role()
	ensure_standard_targets()
	ensure_page_title()
	ensure_workspace()


def ensure_role() -> None:
	if frappe.db.exists("Role", ROLE_OPENAI_AGENT_USER):
		return

	role = frappe.new_doc("Role")
	role.role_name = ROLE_OPENAI_AGENT_USER
	role.desk_access = 1
	role.insert(ignore_permissions=True)


def ensure_page_title() -> None:
	if not frappe.db.exists("Page", "openai-agent-chat"):
		return

	page = frappe.get_doc("Page", "openai-agent-chat")
	page.title = WORKSPACE_NAME
	page.save(ignore_permissions=True)


def ensure_standard_targets(force: bool = False) -> None:
	from frappe.modules.import_file import import_file_by_path

	app_root = Path(__file__).resolve().parent

	for doctype, docname, relative_path in STANDARD_TARGETS:
		if force or not frappe.db.exists(doctype, docname):
			import_file_by_path(str(app_root / relative_path), force=True)


def ensure_workspace() -> None:
	content = json.dumps(
		[
			{
				"id": "openai_header",
				"type": "header",
				"data": {
					"text": "<span style=\"font-size: 18px;\"><b>Riley Assistant</b></span>",
					"col": 12,
				},
			},
			{
				"id": "openai_shortcut_chat",
				"type": "shortcut",
				"data": {"shortcut_name": "Riley Assistant", "col": 4},
			},
			{
				"id": "openai_shortcut_agents",
				"type": "shortcut",
				"data": {"shortcut_name": "OpenAI Agent", "col": 4},
			},
			{
				"id": "openai_shortcut_access",
				"type": "shortcut",
				"data": {"shortcut_name": "OpenAI Agent Access", "col": 4},
			},
			{
				"id": "openai_shortcut_mcp_profile",
				"type": "shortcut",
				"data": {"shortcut_name": "OpenAI Agent MCP Profile", "col": 4},
			},
		]
	)

	workspace = frappe.get_doc("Workspace", WORKSPACE_NAME) if frappe.db.exists("Workspace", WORKSPACE_NAME) else frappe.new_doc("Workspace")
	workspace.title = WORKSPACE_NAME
	workspace.label = WORKSPACE_NAME
	workspace.name = WORKSPACE_NAME
	workspace.module = "OpenAI Agent Bridge"
	workspace.icon = "chat"
	workspace.public = 1
	workspace.parent_page = ""
	workspace.content = content

	workspace.set("roles", [])
	for role in ["System Manager", ROLE_OPENAI_AGENT_USER]:
		workspace.append("roles", {"role": role})

	workspace.set("shortcuts", [])
	workspace.append(
		"shortcuts",
		{
			"label": "Riley Assistant",
			"type": "Page",
			"link_to": "openai-agent-chat",
			"doc_view": "",
			"color": "Grey",
		},
	)
	workspace.append(
		"shortcuts",
		{
			"label": "OpenAI Agent",
			"type": "DocType",
			"link_to": "OpenAI Agent",
			"doc_view": "List",
			"color": "Grey",
		},
	)
	workspace.append(
		"shortcuts",
		{
			"label": "OpenAI Agent MCP Profile",
			"type": "DocType",
			"link_to": "OpenAI Agent MCP Profile",
			"doc_view": "List",
			"color": "Grey",
		},
	)
	workspace.append(
		"shortcuts",
		{
			"label": "OpenAI Agent Access",
			"type": "DocType",
			"link_to": "OpenAI Agent Access",
			"doc_view": "List",
			"color": "Grey",
		},
	)

	if workspace.is_new():
		workspace.insert(ignore_permissions=True)
	else:
		workspace.save(ignore_permissions=True)

	frappe.clear_cache()
