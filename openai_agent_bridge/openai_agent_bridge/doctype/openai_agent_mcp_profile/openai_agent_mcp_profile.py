from __future__ import annotations

import frappe
from frappe.model.document import Document


class OpenAIAgentMCPProfile(Document):
	def validate(self) -> None:
		if self.use_user_api_credentials:
			return

		if self.auth_type == "Bearer":
			if not self.get_password("bearer_token"):
				frappe.throw("Bearer token is required when auth type is Bearer.")
			return

		if not self.api_key:
			frappe.throw("API key is required when auth type is Token.")
		if not self.get_password("api_secret"):
			frappe.throw("API secret is required when auth type is Token.")
