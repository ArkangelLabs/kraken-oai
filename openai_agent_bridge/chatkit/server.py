from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator, Iterator
from typing import Any

import frappe
from agents import Agent, OpenAIProvider, RunConfig, Runner
from agents.mcp import MCPServerSse, MCPServerStreamableHttp
from chatkit.agents import AgentContext, simple_to_agent_input, stream_agent_response
from chatkit.server import ChatKitServer, NonStreamingResult
from chatkit.types import Action, NoticeEvent, SyncCustomActionResponse, ThreadMetadata, UserMessageItem, WidgetItem
from werkzeug.wrappers import Response

from .store import FrappeChatKitStore


def _get_openai_api_key() -> str | None:
	return frappe.conf.get("openai_api_key") or os.environ.get("OPENAI_API_KEY")


def _build_auth_headers(profile) -> dict[str, str]:
	auth_type = (profile.auth_type or "Token").strip()
	if auth_type == "Bearer":
		token = profile.get_password("bearer_token")
		if not token:
			frappe.throw("Bearer token is missing on the MCP profile.")
		return {"Authorization": f"Bearer {token}"}

	api_key = profile.api_key
	api_secret = profile.get_password("api_secret")
	if not api_key or not api_secret:
		frappe.throw("API key and API secret are required on the MCP profile.")
	return {"Authorization": f"token {api_key}:{api_secret}"}


def _get_mcp_profile(user: str):
	name = frappe.db.get_value("OpenAI Agent MCP Profile", {"user": user, "enabled": 1}, "name")
	if not name:
		return None
	return frappe.get_doc("OpenAI Agent MCP Profile", name)


def _iter_async(async_iterable: AsyncIterator[bytes]) -> Iterator[bytes]:
	loop = asyncio.new_event_loop()
	asyncio.set_event_loop(loop)
	iterator = async_iterable.__aiter__()
	try:
		while True:
			try:
				yield loop.run_until_complete(iterator.__anext__())
			except StopAsyncIteration:
				break
	finally:
		loop.run_until_complete(loop.shutdown_asyncgens())
		asyncio.set_event_loop(None)
		loop.close()


class FrappeChatKitServer(ChatKitServer[dict[str, Any]]):
	def __init__(self):
		super().__init__(store=FrappeChatKitStore())

	def _build_agent(self, agent_doc, profile) -> Agent[AgentContext[dict[str, Any]]]:
		mcp_servers = []
		if profile:
			params = {
				"url": profile.mcp_server_url,
				"headers": _build_auth_headers(profile),
				"timeout": 30,
				"sse_read_timeout": 300,
			}
			if profile.mcp_transport == "SSE":
				mcp_servers = [MCPServerSse(params=params, require_approval="never")]
			else:
				mcp_servers = [MCPServerStreamableHttp(params=params, require_approval="never")]

		return Agent(
			name=agent_doc.agent_name,
			model=agent_doc.model or "gpt-4.1",
			instructions=agent_doc.instructions or agent_doc.description or None,
			mcp_servers=mcp_servers,
		)

	async def respond(
		self,
		thread: ThreadMetadata,
		input_user_message: UserMessageItem | None,
		context: dict[str, Any],
	) -> AsyncIterator[Any]:
		api_key = _get_openai_api_key()
		if not api_key:
			frappe.throw(
				"Set openai_api_key in site_config.json or OPENAI_API_KEY in the backend environment."
			)

		agent_doc = frappe.get_doc("OpenAI Agent", context["agent"])
		profile = _get_mcp_profile(context["user"])
		items_page = await self.store.load_thread_items(
			thread.id, after=None, limit=200, order="asc", context=context
		)
		model_input = await simple_to_agent_input(items_page.data)
		agent_context = AgentContext(thread=thread, store=self.store, request_context=context)
		agent = self._build_agent(agent_doc, profile)
		run_config = RunConfig(
			model_provider=OpenAIProvider(api_key=api_key, use_responses=True),
			tracing_disabled=True,
			workflow_name=agent_doc.agent_name,
			group_id=thread.id,
		)

		mcp_servers = list(agent.mcp_servers)
		try:
			for server in mcp_servers:
				await server.connect()

			result = Runner.run_streamed(
				agent,
				model_input,
				context=agent_context,
				run_config=run_config,
			)
			async for event in stream_agent_response(agent_context, result):
				yield event
		finally:
			for server in reversed(mcp_servers):
				await server.cleanup()

	async def action(
		self,
		thread: ThreadMetadata,
		action: Action[str, Any],
		sender: WidgetItem | None,
		context: dict[str, Any],
	) -> AsyncIterator[Any]:
		yield NoticeEvent(message=f"Unsupported widget action: {action.type}")

	async def sync_action(
		self,
		thread: ThreadMetadata,
		action: Action[str, Any],
		sender: WidgetItem | None,
		context: dict[str, Any],
	) -> SyncCustomActionResponse:
		return SyncCustomActionResponse()


def build_chatkit_response(request_body: bytes, context: dict[str, Any]) -> Response:
	server = FrappeChatKitServer()
	result = asyncio.run(server.process(request_body, context))
	if isinstance(result, NonStreamingResult):
		return Response(result.json, mimetype="application/json")

	headers = {
		"Cache-Control": "no-cache",
		"X-Accel-Buffering": "no",
	}
	return Response(_iter_async(result), mimetype="text/event-stream", headers=headers)
