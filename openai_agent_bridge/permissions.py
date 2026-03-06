from __future__ import annotations

import frappe


def _is_system_manager(user: str) -> bool:
	return "System Manager" in frappe.get_roles(user)


def openai_agent_query_conditions(user: str | None = None) -> str | None:
	user = user or frappe.session.user

	if _is_system_manager(user):
		return None

	if user == "Guest":
		return "1=0"

	user_escaped = frappe.db.escape(user)
	return (
		"`tabOpenAI Agent`.`name` in ("
		"select `agent` from `tabOpenAI Agent Access` "
		f"where `user` = {user_escaped} and `enabled` = 1)"
	)


def openai_agent_has_permission(doc, user: str | None = None, permission_type: str | None = None) -> bool:
	user = user or frappe.session.user

	if _is_system_manager(user):
		return True

	if user == "Guest":
		return False

	return bool(
		frappe.db.exists(
			"OpenAI Agent Access",
			{"user": user, "agent": doc.name, "enabled": 1},
		)
	)


def openai_agent_mcp_profile_query_conditions(user: str | None = None) -> str | None:
	user = user or frappe.session.user

	if _is_system_manager(user):
		return None

	if user == "Guest":
		return "1=0"

	return f"`tabOpenAI Agent MCP Profile`.`user` = {frappe.db.escape(user)}"


def openai_agent_mcp_profile_has_permission(
	doc, user: str | None = None, permission_type: str | None = None
) -> bool:
	user = user or frappe.session.user

	if _is_system_manager(user):
		return True

	if user == "Guest":
		return False

	return doc.user == user
