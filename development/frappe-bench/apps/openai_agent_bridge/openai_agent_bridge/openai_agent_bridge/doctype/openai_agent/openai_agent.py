from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document


class OpenAIAgent(Document):
	def validate(self) -> None:
		self.agent_name = (self.agent_name or "").strip()
		self.workflow_id = (self.workflow_id or "").strip()

		if self.workflow_id and not self.workflow_id.startswith("wf_"):
			frappe.throw(_("Workflow ID must start with wf_."))
