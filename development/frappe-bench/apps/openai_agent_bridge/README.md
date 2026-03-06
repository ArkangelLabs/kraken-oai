### OpenAI Agent Bridge

Frappe app that integrates OpenAI Agent Builder workflows into Desk with ChatKit.

### What this app adds

- `OpenAI Agent` DocType
  - Managed by `System Manager`
  - Stores `workflow_id` (`wf_...`) and enable/disable state
- `OpenAI Agent Access` DocType
  - Managed by `System Manager`
  - Maps `User` to `OpenAI Agent` for access control
- `OpenAI Agent User` role
  - Role that can use assigned agents in the chat page
- Session API endpoints
  - `openai_agent_bridge.api.get_available_agents`
  - `openai_agent_bridge.api.create_chatkit_session`
- Workspace + Page
  - Workspace: `OpenAI Agents`
  - Embedded ChatKit page: `openai-agent-chat`

### Session API behavior

The backend creates ChatKit sessions with:

- `workflow.id` from `OpenAI Agent.workflow_id`
- `user` set to `frappe.session.user` (current logged-in Frappe user)

### OpenAI key configuration

Set either one of the following in the backend:

- `openai_api_key` in `site_config.json`
- `OPENAI_API_KEY` environment variable

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
