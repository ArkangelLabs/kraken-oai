from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document


class OpenAIAgentAccess(Document):
	def validate(self) -> None:
		self.user = (self.user or "").strip()

		existing = frappe.db.exists(
			"OpenAI Agent Access",
			{
				"user": self.user,
				"agent": self.agent,
				"name": ["!=", self.name],
			},
		)
		if existing:
			frappe.throw(_("This user already has an access entry for the selected OpenAI agent."))
