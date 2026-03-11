from __future__ import annotations

from urllib.parse import urlparse

import frappe
from frappe import _
from frappe.model.document import Document


class OpenAIAgent(Document):
	def validate(self) -> None:
		self.agent_name = (self.agent_name or "").strip()
		self.workflow_id = (self.workflow_id or "").strip()
		self.api_base_url_override = (self.api_base_url_override or "").strip()
		self.shell_container_id = (self.shell_container_id or "").strip()
		self.shell_allowed_domains = self._normalize_multiline(self.shell_allowed_domains)
		self.shell_skill_ids = self._normalize_multiline(self.shell_skill_ids)

		if self.workflow_id and not self.workflow_id.startswith("wf_"):
			frappe.throw(_("Workflow ID must start with wf_."))

		if self.api_base_url_override:
			parsed = urlparse(self.api_base_url_override)
			if parsed.scheme not in {"http", "https"} or not parsed.netloc:
				frappe.throw(_("API Base URL Override must be a valid http or https URL."))

		if self.shell_memory_limit and self.shell_memory_limit not in {"1g", "4g", "16g", "64g"}:
			frappe.throw(_("Hosted Shell Memory Limit must be one of 1g, 4g, 16g, or 64g."))

		if self.shell_network_enabled and not (self.enable_shell or 0):
			frappe.throw(_("Enable Hosted Shell before enabling Hosted Shell Network."))

	@staticmethod
	def _normalize_multiline(value: str | None) -> str:
		items = [line.strip() for line in (value or "").splitlines() if line.strip()]
		return "\n".join(items)
