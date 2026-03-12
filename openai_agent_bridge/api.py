from __future__ import annotations

import asyncio
import json
import os
from typing import Any

import frappe
from frappe import _
from werkzeug.wrappers import Response

from openai_agent_bridge.chatkit import build_chatkit_response, debug_chatkit_probe


DEFAULT_CHATKIT_DOMAIN_KEY = "domain_pk_69ab0f58e25881938658c48e368ec0500a2c5f59ab572a55"
DEFAULT_CHATKIT_DOMAIN_KEYS_BY_HOST = {
	"greenfoot-energy.mythril.cloud": "domain_pk_69b2bc8bf7788190abf849760aec9a440338f2347883f82e",
	"greenfoot.v.frappe.cloud": DEFAULT_CHATKIT_DOMAIN_KEY,
}


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


def _can_edit_agent_instructions(user: str, agent_name: str) -> bool:
	if _is_system_manager(user):
		return True

	if user == "Guest":
		return False

	if "OpenAI Agent User" not in frappe.get_roles(user):
		return False

	return bool(
		frappe.db.exists(
			"OpenAI Agent Access",
			{"user": user, "agent": agent_name, "enabled": 1},
		)
	)


def _coerce_chatkit_domain_key_map(value: Any) -> dict[str, str]:
	if not value:
		return {}

	if isinstance(value, dict):
		return {
			str(host).strip().lower(): str(key).strip()
			for host, key in value.items()
			if host and key
		}

	if isinstance(value, str):
		parsed: Any = None
		try:
			parsed = json.loads(value)
		except json.JSONDecodeError:
			parsed = None

		if isinstance(parsed, dict):
			return _coerce_chatkit_domain_key_map(parsed)

		mapping: dict[str, str] = {}
		for raw_line in value.replace(",", "\n").splitlines():
			line = raw_line.strip()
			if not line or "=" not in line:
				continue
			host, key = line.split("=", 1)
			host = host.strip().lower()
			key = key.strip()
			if host and key:
				mapping[host] = key
		return mapping

	return {}


def _get_chatkit_domain_key_map() -> dict[str, str]:
	config_map = _coerce_chatkit_domain_key_map(
		frappe.conf.get("openai_chatkit_domain_keys")
		or frappe.conf.get("openai_agent_chatkit_domain_keys")
		or os.environ.get("OPENAI_CHATKIT_DOMAIN_KEYS")
		or os.environ.get("OPENAI_AGENT_CHATKIT_DOMAIN_KEYS")
	)
	if config_map:
		return config_map
	return DEFAULT_CHATKIT_DOMAIN_KEYS_BY_HOST


def _get_default_chatkit_domain_key() -> str | None:
	return (
		frappe.conf.get("openai_chatkit_domain_key")
		or frappe.conf.get("openai_agent_chatkit_domain_key")
		or os.environ.get("OPENAI_CHATKIT_DOMAIN_KEY")
		or os.environ.get("OPENAI_AGENT_CHATKIT_DOMAIN_KEY")
		or DEFAULT_CHATKIT_DOMAIN_KEY
	)


@frappe.whitelist()
def get_available_agents() -> list[dict[str, Any]]:
	if frappe.session.user == "Guest":
		frappe.throw(_("You must be logged in to use OpenAI chat."))

	allowed_names = _get_allowed_agent_names(frappe.session.user)
	if not allowed_names:
		return []

	agents = frappe.get_all(
		"OpenAI Agent",
		filters={"name": ["in", allowed_names], "enabled": 1},
		fields=["name", "agent_name", "model", "workflow_id"],
		order_by="agent_name asc",
	)

	domain_keys = _get_chatkit_domain_key_map()
	default_domain_key = _get_default_chatkit_domain_key()
	for agent in agents:
		agent["chatkit_domain_keys"] = domain_keys
		if default_domain_key:
			agent["default_chatkit_domain_key"] = default_domain_key

	return agents


@frappe.whitelist(methods=["POST"])
def update_agent_instructions(agent_name: str, instructions: str | None = None) -> dict[str, Any]:
	if frappe.session.user == "Guest":
		frappe.throw(_("You must be logged in to update agent instructions."), frappe.PermissionError)

	if not _can_edit_agent_instructions(frappe.session.user, agent_name):
		frappe.throw(_("You do not have permission to edit these instructions."), frappe.PermissionError)

	doc = frappe.get_doc("OpenAI Agent", agent_name)
	doc.instructions = (instructions or "").strip()
	doc.save(ignore_permissions=True)
	frappe.clear_cache(doctype="OpenAI Agent")

	return {
		"name": doc.name,
		"instructions": doc.instructions,
	}


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


@frappe.whitelist()
def debug_chatkit() -> dict[str, Any]:
	if not _is_system_manager(frappe.session.user):
		frappe.throw(_("Only System Managers can run ChatKit diagnostics."), frappe.PermissionError)

	agent_name = _get_default_agent_name(frappe.session.user)
	if not agent_name:
		frappe.throw(_("No enabled OpenAI agent is assigned to your user."))

	return asyncio.run(debug_chatkit_probe(agent_name, frappe.session.user))
