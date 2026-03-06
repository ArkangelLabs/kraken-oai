### OpenAI Agent Bridge

Frappe app that embeds ChatKit in Desk and serves it from the Responses API.

### What this app adds

- `OpenAI Agent` DocType
  - Managed by `System Manager`
  - Stores model, instructions, and enable/disable state
- `OpenAI Agent Access` DocType
  - Managed by `System Manager`
  - Maps `User` to `OpenAI Agent` for access control
- `OpenAI Agent MCP Profile` DocType
  - Optional per-user override for remote MCP transport, URL, and auth
- `OpenAI Agent User` role
  - Role that can use assigned agents in the chat page
- ChatKit protocol endpoint
  - `openai_agent_bridge.api.get_available_agents`
  - `openai_agent_bridge.api.chatkit`
- Read-only MCP endpoint
  - `openai_agent_bridge.mcp.handle_mcp`
- Workspace + Page
  - Workspace: `OpenAI Agents`
  - Embedded ChatKit page: `openai-agent-chat`

### Responses API behavior

The backend runs the selected agent through the Responses API and persists thread history in Frappe.

### MCP behavior

By default the backend automatically attaches a remote MCP server for the signed-in user:

- URL: `openai_agent_mcp_server_url` from `site_config.json`, or the app's own MCP endpoint
- Auth: the signed-in user's Frappe API key and API secret
- Transport: `openai_agent_mcp_transport` from `site_config.json`, default `Streamable HTTP`

`OpenAI Agent MCP Profile` can override the default URL, transport, or auth for a specific user.

### OpenAI key configuration

Set either one of the following in the backend:

- `openai_api_key` in `site_config.json`
- `OPENAI_API_KEY` environment variable

Optional MCP config in `site_config.json`:

- `openai_agent_mcp_server_url`
- `openai_agent_mcp_transport`

### Installation

```bash
cd $PATH_TO_BENCH
bench get-app $URL_OF_THIS_REPO
bench --site $SITE install-app openai_agent_bridge
bench --site $SITE migrate
bench build --app openai_agent_bridge
```

### Docker dev test notes

For `frappe_docker` development flow:

```bash
docker compose -f devcontainer-example/docker-compose.yml up -d
docker compose -f devcontainer-example/docker-compose.yml exec -T -w /workspace/development/frappe-bench frappe bench --site development.localhost migrate
```

Then open Desk and go to `/app/openai-agents` or `/app/openai-agent-chat`.

To run the local Desk server from this repo setup:

```bash
docker compose -f devcontainer-example/docker-compose.yml exec -w /workspace/development/frappe-bench frappe bench start
```

### License

mit
