app_name = "openai_agent_bridge"
app_title = "Riley Assistant"
app_publisher = "Mythril"
app_description = "OpenAI Agent Builder + ChatKit integration for Frappe"
app_email = "admin@example.com"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "openai_agent_bridge",
# 		"logo": "/assets/openai_agent_bridge/logo.png",
# 		"title": "OpenAI Agent Bridge",
# 		"route": "/openai_agent_bridge",
# 		"has_permission": "openai_agent_bridge.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/openai_agent_bridge/css/openai_agent_bridge.css"
# app_include_js = "/assets/openai_agent_bridge/js/openai_agent_bridge.js"

# include js, css files in header of web template
# web_include_css = "/assets/openai_agent_bridge/css/openai_agent_bridge.css"
# web_include_js = "/assets/openai_agent_bridge/js/openai_agent_bridge.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "openai_agent_bridge/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
	"OpenAI Agent": "openai_agent_bridge/doctype/openai_agent/openai_agent.js",
}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "openai_agent_bridge/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "openai_agent_bridge.utils.jinja_methods",
# 	"filters": "openai_agent_bridge.utils.jinja_filters"
# }

# Installation
# ------------

after_install = "openai_agent_bridge.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "openai_agent_bridge.uninstall.before_uninstall"
# after_uninstall = "openai_agent_bridge.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "openai_agent_bridge.utils.before_app_install"
# after_app_install = "openai_agent_bridge.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "openai_agent_bridge.utils.before_app_uninstall"
# after_app_uninstall = "openai_agent_bridge.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "openai_agent_bridge.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

permission_query_conditions = {
	"OpenAI Agent": "openai_agent_bridge.permissions.openai_agent_query_conditions",
	"OpenAI Agent MCP Profile": "openai_agent_bridge.permissions.openai_agent_mcp_profile_query_conditions",
}

has_permission = {
	"OpenAI Agent": "openai_agent_bridge.permissions.openai_agent_has_permission",
	"OpenAI Agent MCP Profile": "openai_agent_bridge.permissions.openai_agent_mcp_profile_has_permission",
}

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"openai_agent_bridge.tasks.all"
# 	],
# 	"daily": [
# 		"openai_agent_bridge.tasks.daily"
# 	],
# 	"hourly": [
# 		"openai_agent_bridge.tasks.hourly"
# 	],
# 	"weekly": [
# 		"openai_agent_bridge.tasks.weekly"
# 	],
# 	"monthly": [
# 		"openai_agent_bridge.tasks.monthly"
# 	],
# }

# Testing
# -------

after_migrate = "openai_agent_bridge.install.after_migrate"

# before_tests = "openai_agent_bridge.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "openai_agent_bridge.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "openai_agent_bridge.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["openai_agent_bridge.utils.before_request"]
# after_request = ["openai_agent_bridge.utils.after_request"]

# Job Events
# ----------
# before_job = ["openai_agent_bridge.utils.before_job"]
# after_job = ["openai_agent_bridge.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"openai_agent_bridge.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []
