from __future__ import annotations

from datetime import datetime
from typing import Any

import frappe
from chatkit.store import Store
from chatkit.types import Attachment, Page, ThreadItem, ThreadMetadata
from pydantic import TypeAdapter


THREAD_ADAPTER = TypeAdapter(ThreadMetadata)
THREAD_ITEM_ADAPTER = TypeAdapter(ThreadItem)
ATTACHMENT_ADAPTER = TypeAdapter(Attachment)


class FrappeChatKitStore(Store[dict[str, Any]]):
	def _get_thread_name(self, thread_id: str, user: str) -> str:
		thread_name = frappe.db.get_value("OpenAI Chat Thread", {"thread_id": thread_id}, "name")
		if not thread_name:
			raise frappe.DoesNotExistError(f"Chat thread {thread_id} was not found.")

		thread_user = frappe.db.get_value("OpenAI Chat Thread", thread_name, "user")
		if thread_user != user:
			raise frappe.PermissionError("You do not have access to this chat thread.")

		return str(thread_name)

	async def load_thread(self, thread_id: str, context: dict[str, Any]) -> ThreadMetadata:
		thread_name = self._get_thread_name(thread_id, context["user"])
		payload = frappe.db.get_value("OpenAI Chat Thread", thread_name, "payload_json")
		return THREAD_ADAPTER.validate_json(payload)

	async def save_thread(self, thread: ThreadMetadata, context: dict[str, Any]) -> None:
		user = context["user"]
		agent = context.get("agent")
		values = {
			"user": user,
			"agent": agent,
			"thread_id": thread.id,
			"title": thread.title,
			"status": thread.status or "active",
			"last_activity": datetime.now(),
			"payload_json": thread.model_dump_json(exclude_none=True),
		}
		name = frappe.db.get_value("OpenAI Chat Thread", {"thread_id": thread.id}, "name")
		if name:
			existing_user = frappe.db.get_value("OpenAI Chat Thread", name, "user")
			if existing_user != user:
				raise frappe.PermissionError("You do not have access to this chat thread.")
			frappe.db.set_value("OpenAI Chat Thread", name, values, update_modified=True)
		else:
			doc = frappe.get_doc({"doctype": "OpenAI Chat Thread", **values})
			doc.insert(ignore_permissions=True)
		frappe.db.commit()

	async def load_thread_items(
		self,
		thread_id: str,
		after: str | None,
		limit: int,
		order: str,
		context: dict[str, Any],
	) -> Page[ThreadItem]:
		thread_name = self._get_thread_name(thread_id, context["user"])
		rows = frappe.get_all(
			"OpenAI Chat Thread Item",
			filters={"thread": thread_name},
			fields=["item_id", "payload_json"],
			order_by=f"created_at {'desc' if order == 'desc' else 'asc'}",
			limit_page_length=max(limit + 1, 1),
		)
		if after:
			ids = [row["item_id"] for row in rows]
			if after in ids:
				rows = rows[ids.index(after) + 1 :]
		has_more = len(rows) > limit
		rows = rows[:limit]
		items = [THREAD_ITEM_ADAPTER.validate_json(row["payload_json"]) for row in rows]
		next_after = rows[-1]["item_id"] if has_more and rows else None
		return Page(data=items, has_more=has_more, after=next_after)

	async def save_attachment(self, attachment: Attachment, context: dict[str, Any]) -> None:
		values = {
			"user": context["user"],
			"attachment_id": attachment.id,
			"payload_json": attachment.model_dump_json(exclude_none=True),
		}
		name = frappe.db.get_value(
			"OpenAI Chat Attachment", {"attachment_id": attachment.id}, "name"
		)
		if name:
			frappe.db.set_value("OpenAI Chat Attachment", name, values, update_modified=True)
		else:
			doc = frappe.get_doc({"doctype": "OpenAI Chat Attachment", **values})
			doc.insert(ignore_permissions=True)
		frappe.db.commit()

	async def load_attachment(self, attachment_id: str, context: dict[str, Any]) -> Attachment:
		name = frappe.db.get_value(
			"OpenAI Chat Attachment",
			{"attachment_id": attachment_id, "user": context["user"]},
			"name",
		)
		if not name:
			raise frappe.DoesNotExistError(f"Attachment {attachment_id} was not found.")
		payload = frappe.db.get_value("OpenAI Chat Attachment", name, "payload_json")
		return ATTACHMENT_ADAPTER.validate_json(payload)

	async def delete_attachment(self, attachment_id: str, context: dict[str, Any]) -> None:
		name = frappe.db.get_value(
			"OpenAI Chat Attachment",
			{"attachment_id": attachment_id, "user": context["user"]},
			"name",
		)
		if name:
			frappe.delete_doc("OpenAI Chat Attachment", name, ignore_permissions=True, force=True)
			frappe.db.commit()

	async def load_threads(
		self,
		limit: int,
		after: str | None,
		order: str,
		context: dict[str, Any],
	) -> Page[ThreadMetadata]:
		rows = frappe.get_all(
			"OpenAI Chat Thread",
			filters={"user": context["user"], "agent": context.get("agent")},
			fields=["thread_id", "payload_json"],
			order_by=f"last_activity {'desc' if order == 'desc' else 'asc'}",
			limit_page_length=max(limit + 1, 1),
		)
		if after:
			ids = [row["thread_id"] for row in rows]
			if after in ids:
				rows = rows[ids.index(after) + 1 :]
		has_more = len(rows) > limit
		rows = rows[:limit]
		threads = [THREAD_ADAPTER.validate_json(row["payload_json"]) for row in rows]
		next_after = rows[-1]["thread_id"] if has_more and rows else None
		return Page(data=threads, has_more=has_more, after=next_after)

	async def add_thread_item(self, thread_id: str, item: ThreadItem, context: dict[str, Any]) -> None:
		thread_name = self._get_thread_name(thread_id, context["user"])
		doc = frappe.get_doc(
			{
				"doctype": "OpenAI Chat Thread Item",
				"thread": thread_name,
				"item_id": item.id,
				"item_type": item.type,
				"created_at": item.created_at,
				"payload_json": item.model_dump_json(exclude_none=True),
			}
		)
		doc.insert(ignore_permissions=True)
		frappe.db.set_value(
			"OpenAI Chat Thread", thread_name, "last_activity", datetime.now(), update_modified=True
		)
		frappe.db.commit()

	async def save_item(self, thread_id: str, item: ThreadItem, context: dict[str, Any]) -> None:
		thread_name = self._get_thread_name(thread_id, context["user"])
		name = frappe.db.get_value(
			"OpenAI Chat Thread Item", {"thread": thread_name, "item_id": item.id}, "name"
		)
		values = {
			"thread": thread_name,
			"item_id": item.id,
			"item_type": item.type,
			"created_at": item.created_at,
			"payload_json": item.model_dump_json(exclude_none=True),
		}
		if name:
			frappe.db.set_value("OpenAI Chat Thread Item", name, values, update_modified=True)
		else:
			doc = frappe.get_doc({"doctype": "OpenAI Chat Thread Item", **values})
			doc.insert(ignore_permissions=True)
		frappe.db.set_value(
			"OpenAI Chat Thread", thread_name, "last_activity", datetime.now(), update_modified=True
		)
		frappe.db.commit()

	async def load_item(self, thread_id: str, item_id: str, context: dict[str, Any]) -> ThreadItem:
		thread_name = self._get_thread_name(thread_id, context["user"])
		payload = frappe.db.get_value(
			"OpenAI Chat Thread Item",
			{"thread": thread_name, "item_id": item_id},
			"payload_json",
		)
		if not payload:
			raise frappe.DoesNotExistError(f"Chat thread item {item_id} was not found.")
		return THREAD_ITEM_ADAPTER.validate_json(payload)

	async def delete_thread(self, thread_id: str, context: dict[str, Any]) -> None:
		thread_name = self._get_thread_name(thread_id, context["user"])
		for item_name in frappe.get_all(
			"OpenAI Chat Thread Item",
			filters={"thread": thread_name},
			pluck="name",
			limit_page_length=0,
		):
			frappe.delete_doc("OpenAI Chat Thread Item", item_name, ignore_permissions=True, force=True)
		frappe.delete_doc("OpenAI Chat Thread", thread_name, ignore_permissions=True, force=True)
		frappe.db.commit()

	async def delete_thread_item(self, thread_id: str, item_id: str, context: dict[str, Any]) -> None:
		thread_name = self._get_thread_name(thread_id, context["user"])
		name = frappe.db.get_value(
			"OpenAI Chat Thread Item", {"thread": thread_name, "item_id": item_id}, "name"
		)
		if name:
			frappe.delete_doc("OpenAI Chat Thread Item", name, ignore_permissions=True, force=True)
			frappe.db.commit()
