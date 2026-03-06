from __future__ import annotations

import asyncio
import os
from contextlib import contextmanager
from dataclasses import dataclass
from collections.abc import AsyncIterator, Iterator
from typing import Any

import agents
import frappe
from frappe.utils import get_url
from agents import Agent, OpenAIProvider, RunConfig, Runner
from agents.mcp import MCPServerSse, MCPServerStreamableHttp
from chatkit.agents import AgentContext, simple_to_agent_input, stream_agent_response
import chatkit.server as chatkit_server
from chatkit.server import ChatKitServer, CustomStreamError, NonStreamingResult
from chatkit.types import Action, NoticeEvent, SyncCustomActionResponse, ThreadMetadata, UserMessageItem, WidgetItem
from werkzeug.wrappers import Response

from .store import FrappeChatKitStore


_original_chatkit_logger_exception = chatkit_server.logger.exception


def _frappe_chatkit_logger_exception(*args, **kwargs):
	try:
		frappe.log_error(
			title="OpenAI Agent ChatKit Internal Error",
			message=frappe.get_traceback(),
		)
	except Exception:
		pass
	return _original_chatkit_logger_exception(*args, **kwargs)


chatkit_server.logger.exception = _frappe_chatkit_logger_exception


@contextmanager
def _safe_agents_sdk_user_agent_override():
	ua = f"Agents/Python {agents.__version__} ChatKit/Python"
	chat_completions_token = chatkit_server.chat_completions_headers_override.set({"User-Agent": ua})
	responses_token = chatkit_server.responses_headers_override.set({"User-Agent": ua})
	try:
		yield
	finally:
		for override, token in (
			(chatkit_server.chat_completions_headers_override, chat_completions_token),
			(chatkit_server.responses_headers_override, responses_token),
		):
			try:
				override.reset(token)
			except ValueError:
				# Python 3.14 can report a false context mismatch here after
				# streaming completes, which would otherwise surface as stream.error.
				pass


chatkit_server.agents_sdk_user_agent_override = _safe_agents_sdk_user_agent_override


def _get_openai_api_key() -> str | None:
	return frappe.conf.get("openai_api_key") or os.environ.get("OPENAI_API_KEY")


@dataclass
class EffectiveMCPConfig:
	url: str
	transport: str
	headers: dict[str, str]


def _get_default_mcp_server_url() -> str:
	configured_url = frappe.conf.get("openai_agent_mcp_server_url") or os.environ.get(
		"OPENAI_AGENT_MCP_SERVER_URL"
	)
	if configured_url:
		return configured_url
	return get_url("/api/method/openai_agent_bridge.mcp.handle_mcp")


def _get_default_mcp_transport() -> str:
	return (
		frappe.conf.get("openai_agent_mcp_transport")
		or os.environ.get("OPENAI_AGENT_MCP_TRANSPORT")
		or "Streamable HTTP"
	)


def _get_user_api_auth_headers(user: str) -> dict[str, str]:
	user_doc = frappe.get_doc("User", user)
	updated = False
	if not user_doc.api_key:
		user_doc.api_key = frappe.generate_hash(length=15)
		updated = True
	if not user_doc.get_password("api_secret", raise_exception=False):
		user_doc.api_secret = frappe.generate_hash(length=15)
		updated = True
	if updated:
		user_doc.save(ignore_permissions=True)
		# The MCP request is made immediately after provisioning credentials.
		# Commit first so the downstream authenticated request can see them.
		frappe.db.commit()

	api_secret = user_doc.get_password("api_secret", raise_exception=False)
	if not user_doc.api_key or not api_secret:
		frappe.throw(f"Unable to provision API credentials for {user}.")

	return {"Authorization": f"token {user_doc.api_key}:{api_secret}"}


def _build_auth_headers(profile) -> dict[str, str]:
	if getattr(profile, "use_user_api_credentials", 0):
		return _get_user_api_auth_headers(profile.user)

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


def _get_effective_mcp_config(user: str) -> EffectiveMCPConfig | None:
	profile = _get_mcp_profile(user)
	if profile:
		return EffectiveMCPConfig(
			url=profile.mcp_server_url or _get_default_mcp_server_url(),
			transport=profile.mcp_transport or _get_default_mcp_transport(),
			headers=_build_auth_headers(profile),
		)

	default_url = _get_default_mcp_server_url()
	if not default_url:
		return None

	return EffectiveMCPConfig(
		url=default_url,
		transport=_get_default_mcp_transport(),
		headers=_get_user_api_auth_headers(user),
	)


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

	def _build_agent(self, agent_doc, mcp_config: EffectiveMCPConfig | None) -> Agent[AgentContext[dict[str, Any]]]:
		mcp_servers = []
		if mcp_config:
			params = {
				"url": mcp_config.url,
				"headers": mcp_config.headers,
				"timeout": 30,
				"sse_read_timeout": 300,
			}
			if mcp_config.transport == "SSE":
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
		try:
			api_key = _get_openai_api_key()
			if not api_key:
				frappe.throw(
					"Set openai_api_key in site_config.json or OPENAI_API_KEY in the backend environment."
				)

			agent_doc = frappe.get_doc("OpenAI Agent", context["agent"])
			mcp_config = _get_effective_mcp_config(context["user"])
			items_page = await self.store.load_thread_items(
				thread.id, after=None, limit=200, order="asc", context=context
			)
			model_input = await simple_to_agent_input(items_page.data)
			agent_context = AgentContext(thread=thread, store=self.store, request_context=context)
			agent = self._build_agent(agent_doc, mcp_config)
			run_config = RunConfig(
				model_provider=OpenAIProvider(api_key=api_key, use_responses=True),
				tracing_disabled=True,
				workflow_name=agent_doc.agent_name,
				group_id=thread.id,
			)

			mcp_servers = list(agent.mcp_servers)
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
		except CustomStreamError:
			raise
		except Exception as exc:
			frappe.log_error(
				title="OpenAI Agent ChatKit Stream Error",
				message=frappe.get_traceback(),
			)
			raise CustomStreamError(f"{type(exc).__name__}: {exc}", allow_retry=True)
		finally:
			for server in reversed(locals().get("mcp_servers", [])):
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
