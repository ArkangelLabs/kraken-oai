from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from werkzeug.wrappers import Response

from openai_agent_bridge.chatkit import build_chatkit_response


def _is_system_manager(user: str) -> bool:
	return "System Manager" in frappe.get_roles(user)


def _get_allowed_agent_names(user: str) -> list[str]:
	if _is_system_manager(user):
		return frappe.get_all("OpenAI Agent", filters={"enabled": 1}, pluck="name")

	agent_names = frappe.get_all(
		"OpenAI Agent Access",
		filters={"user": user, "enabled": 1},
		pluck="agent",
	)

	if not agent_names:
		return []

	return frappe.get_all(
		"OpenAI Agent",
		filters={"name": ["in", agent_names], "enabled": 1},
		pluck="name",
	)


def _get_default_agent_name(user: str) -> str | None:
	allowed_names = _get_allowed_agent_names(user)
	if not allowed_names:
		return None
	return str(
		frappe.db.get_value(
			"OpenAI Agent",
			{"name": ["in", allowed_names], "enabled": 1},
			"name",
			order_by="agent_name asc",
		)
	)


@frappe.whitelist()
def get_available_agents() -> list[dict[str, Any]]:
	if frappe.session.user == "Guest":
		frappe.throw(_("You must be logged in to use OpenAI chat."))

	allowed_names = _get_allowed_agent_names(frappe.session.user)
	if not allowed_names:
		return []

	return frappe.get_all(
		"OpenAI Agent",
		filters={"name": ["in", allowed_names], "enabled": 1},
		fields=["name", "agent_name", "model", "workflow_id"],
		order_by="agent_name asc",
	)


@frappe.whitelist(methods=["POST"])
def chatkit() -> Response:
	if frappe.session.user == "Guest":
		frappe.throw(_("You must be logged in to use OpenAI chat."))

	agent_name = _get_default_agent_name(frappe.session.user)
	if not agent_name:
		frappe.throw(_("No enabled OpenAI agent is assigned to your user."))

	agent_doc = frappe.get_doc("OpenAI Agent", agent_name)
	if not agent_doc.enabled:
		frappe.throw(_("The selected OpenAI agent is disabled."))

	if not _is_system_manager(frappe.session.user):
		has_access = frappe.db.exists(
			"OpenAI Agent Access",
			{"user": frappe.session.user, "agent": agent_doc.name, "enabled": 1},
		)
		if not has_access:
			frappe.throw(_("You do not have access to this OpenAI agent."), frappe.PermissionError)

	request_body = frappe.request.get_data()
	return build_chatkit_response(
		request_body=request_body,
		context={"user": frappe.session.user, "agent": agent_doc.name},
	)
