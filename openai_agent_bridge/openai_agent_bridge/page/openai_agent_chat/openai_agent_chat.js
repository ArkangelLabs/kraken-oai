frappe.provide("openai_agent_bridge");

const DEFAULT_CHATKIT_DOMAIN_KEY = "domain_pk_69ab0f58e25881938658c48e368ec0500a2c5f59ab572a55";
const CHATKIT_DOMAIN_KEYS_BY_HOST = {
	"greenfoot-energy.mythril.cloud": "domain_pk_69b2bc8bf7788190abf849760aec9a440338f2347883f82e",
	"greenfoot.v.frappe.cloud": DEFAULT_CHATKIT_DOMAIN_KEY,
};

frappe.pages["openai-agent-chat"].on_page_load = function (wrapper) {
	new openai_agent_bridge.OpenAIAgentChatPage(wrapper);
};

openai_agent_bridge.OpenAIAgentChatPage = class OpenAIAgentChatPage {
	constructor(wrapper) {
		this.wrapper = $(wrapper);
		this.chatkitScriptPromise = null;
		this.currentAgent = null;
		this.agentName = null;
		this.chatkitDomainKey = null;
		this.chatkitDomainKeys = { ...CHATKIT_DOMAIN_KEYS_BY_HOST };
		this.defaultChatkitDomainKey = DEFAULT_CHATKIT_DOMAIN_KEY;
		this.make();
	}

	make() {
		this.page = frappe.ui.make_app_page({
			parent: this.wrapper,
			title: __("Riley Assistant"),
			single_column: true,
		});

		this.injectStyle();
		this.page.body.html(`
			<div class="openai-agent-chat-page">
				<div class="openai-agent-chat-host" data-field="chat-host">
					<openai-chatkit class="openai-chatkit-widget"></openai-chatkit>
				</div>
			</div>
		`);

		this.chatHost = this.page.body.find('[data-field="chat-host"]');

		this.loadAgents();
	}

	getResolvedDomainKey() {
		const host = window.location.host;
		const configuredHosts = Object.keys(this.chatkitDomainKeys || {});

		if (configuredHosts.length) {
			return this.chatkitDomainKeys[host] || null;
		}

		return this.defaultChatkitDomainKey || DEFAULT_CHATKIT_DOMAIN_KEY;
	}

	buildTheme() {
		const rootStyles = getComputedStyle(document.documentElement);
		const surfaceBackground =
			rootStyles.getPropertyValue("--bg-color").trim() ||
			rootStyles.getPropertyValue("--gray-100").trim() ||
			"#f8f7f4";
		const surfaceForeground =
			rootStyles.getPropertyValue("--gray-900").trim() ||
			rootStyles.getPropertyValue("--text-color").trim() ||
			"#1a1f2e";

		return {
			colorScheme: "light",
			radius: "soft",
			color: {
				surface: {
					background: surfaceBackground,
					foreground: surfaceForeground,
				},
				// Keep ChatKit controls aligned with the warm Mythril neutral palette.
				grayscale: {
					hue: 42,
					tint: 8,
					shade: 0,
				},
			},
		};
	}

	injectStyle() {
		if (document.getElementById("openai-agent-chat-style")) {
			return;
		}

		const style = document.createElement("style");
		style.id = "openai-agent-chat-style";
		style.textContent = `
			.layout-main-section .layout-main-section-wrapper:has(.openai-agent-chat-page) {
				padding: var(--padding-md, 0.75rem);
				background: var(--subtle-fg, transparent);
			}
			.layout-main-section:has(.openai-agent-chat-page) .page-head,
			.layout-main-section:has(.openai-agent-chat-page) .layout-footer,
			.layout-main-section:has(.openai-agent-chat-page) .page-actions,
			.layout-main-section:has(.openai-agent-chat-page) .page-form {
				display: none !important;
			}
			.openai-agent-chat-page {
				display: grid;
				padding: var(--padding-sm, 0.5rem);
			}
			.openai-agent-chat-host {
				height: min(82vh, 900px);
				min-height: 520px;
				border: 1px solid var(--border-color, #d1d5db);
				border-radius: var(--border-radius-md, 0.75rem);
				overflow: hidden;
				background: var(--bg-color, #ffffff);
			}
			.openai-chatkit-widget {
				display: block;
				height: 100%;
				width: 100%;
			}
			@media (max-width: 768px) {
				.layout-main-section .layout-main-section-wrapper:has(.openai-agent-chat-page) {
					padding: var(--padding-xs, 0.25rem);
				}
				.openai-agent-chat-page {
					padding: 0;
				}
			}
		`;

		document.head.appendChild(style);
	}

	async loadAgents() {
		try {
			const response = await frappe.call({ method: "openai_agent_bridge.api.get_available_agents" });
			const agents = response.message || [];

			if (!agents.length) {
				this.showUnavailableState(
					__("No agents are available for your user. Ask a System Manager to add an OpenAI Agent Access record.")
				);
				return;
			}

			this.agentName = agents[0].name;
			this.chatkitDomainKeys = {
				...CHATKIT_DOMAIN_KEYS_BY_HOST,
				...(agents[0].chatkit_domain_keys || {}),
			};
			this.defaultChatkitDomainKey =
				agents[0].default_chatkit_domain_key || DEFAULT_CHATKIT_DOMAIN_KEY;
			this.chatkitDomainKey = this.getResolvedDomainKey();
			if (!this.chatkitDomainKey) {
				this.showUnavailableState(
					__(
						"Riley Assistant is not configured for this site host. Ask a System Manager to add a ChatKit domain key for {0}.",
						[window.location.host]
					)
				);
				return;
			}
			await this.mountChat(this.agentName);
		} catch (error) {
			this.showUnavailableState(__("Unable to load agents."));
			frappe.msgprint({
				title: __("Riley Assistant"),
				indicator: "red",
				message: __("Failed to load agent assignments."),
			});
			console.error(error);
		}
	}

	async mountChat(agentName) {
		if (!agentName) {
			return;
		}

		try {
			await this.ensureChatkitScript();

			const chatElement = this.chatHost.find("openai-chatkit").get(0);
			if (!chatElement || typeof chatElement.setOptions !== "function") {
				throw new Error("ChatKit web component is unavailable.");
			}

			chatElement.setOptions({
				api: {
					url: "/api/method/openai_agent_bridge.api.chatkit",
					domainKey: this.chatkitDomainKey,
					fetch: (input, init = {}) =>
						window.fetch(input, {
							...init,
							credentials: "same-origin",
							headers: {
								"X-Frappe-CSRF-Token": frappe.csrf_token,
								...(init.headers || {}),
							},
						}),
				},
				theme: this.buildTheme(),
			});

			this.currentAgent = agentName;
		} catch (error) {
			frappe.msgprint({
				title: __("Riley Assistant"),
				indicator: "red",
				message: __("Failed to initialize the embedded ChatKit UI."),
			});
			console.error(error);
		}
	}

	async ensureChatkitScript() {
		if (window.customElements && window.customElements.get("openai-chatkit")) {
			return;
		}

		if (this.chatkitScriptPromise) {
			return this.chatkitScriptPromise;
		}

		this.chatkitScriptPromise = new Promise((resolve, reject) => {
			const existing = document.querySelector('script[data-openai-chatkit="1"]');
			if (existing) {
				existing.addEventListener("load", resolve, { once: true });
				existing.addEventListener("error", reject, { once: true });
				return;
			}

			const script = document.createElement("script");
			script.src = "https://cdn.platform.openai.com/deployments/chatkit/chatkit.js";
			script.async = true;
			script.dataset.openaiChatkit = "1";
			script.onload = resolve;
			script.onerror = reject;
			document.head.appendChild(script);
		});

		return this.chatkitScriptPromise;
	}

	showUnavailableState(message) {
		this.chatHost.html(`<div class="text-muted small">${frappe.utils.escape_html(message)}</div>`);
	}
};
