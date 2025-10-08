app_name = "vyshuwaops"
app_title = "Vyshuwaops"
app_publisher = "It enables organizers to create and publish events, define venues, and set ticket categories, while attendees can browse events, book tickets, and receive confirmations with secure online payments.vyshnav"
app_description = "vyshuwaops s a Frappe-based web application for managing events, ticketing, and bookings."
app_email = "vyshnav@gmail.com"
app_license = "mit"

# Apps
# ------------------

required_apps = ["payments"]


scheduler_events = {
    "daily": [
        "vyshuwaops.ticketing.doctype.festa_booking.festa_booking.send_reminders"
    ],
    "weekly": [
        "vyshuwaops.ticketing.doctype.festa_event.festa_event.cleanup_expired_events"
    ]
}


doc_events = {
    "Sales Order": {
        "on_submit": "vyshuwaops.api.sales_order_hook.handle_sales_order_submit"
    },
    "Payment Request": {
        "on_submit": "vyshuwaops.vyshuwaops.doctype.festa_event.festa_event.payment_request_paid"
    }

}

web_methods = {
    # Razorpay sends a POST request with the webhook payload
    "POST": {
        # The key is the URL path segment, the value is the full function path
        "razorpay_webhook": "vyshuwaops.api.api.razorpay_webhook"
}
}


permission_query_conditions = {
    "Festa Event": "vyshuwaops.api.permission.get_festa_event_conditions",
    "Festa Booking": "vyshuwaops.api.permission.get_festa_booking_conditions",
}

has_permission = {
    "Festa Event": "vyshuwaops.api.permission.has_permission",
    "Festa Booking": "vyshuwaops.api.permission.has_permission",
}

# app_include_js = [
#     "/assets/vyshuwaops/js/custom_webform_script.js"
# ]

# doctype_js = {
#     "Web Form": "public/js/web_form_custom.js"
# }





# override_whitelisted_methods = {
#     "vyshuwaops.api.api.razorpay_webhook": "vyshuwaops.api.api.razorpay_webhook"
# }

# override_whitelisted_methods = {
#     "vyshuwaops.vyshuwaops.api.signup.register_user": "vyshuwaops.vyshuwaops.api.signup.register_user"
# }




# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [    
# 	{
# 		"name": "vyshuwaops",
# 		"logo": "/assets/vyshuwaops/logo.png",
# 		"title": "Vyshuwaops",
# 		"route": "/vyshuwaops",
# 		"has_permission": "vyshuwaops.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/vyshuwaops/css/vyshuwaops.css"
# app_include_js = "/assets/vyshuwaops/js/vyshuwaops.js"

# include js, css files in header of web template
# web_include_css = "/assets/vyshuwaops/css/vyshuwaops.css"
# web_include_js = "/assets/vyshuwaops/js/vyshuwaops.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "vyshuwaops/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "vyshuwaops/public/icons.svg"

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
# 	"methods": "vyshuwaops.utils.jinja_methods",
# 	"filters": "vyshuwaops.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "vyshuwaops.install.before_install"
# after_install = "vyshuwaops.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "vyshuwaops.uninstall.before_uninstall"
# after_uninstall = "vyshuwaops.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "vyshuwaops.utils.before_app_install"
# after_app_install = "vyshuwaops.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "vyshuwaops.utils.before_app_uninstall"
# after_app_uninstall = "vyshuwaops.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "vyshuwaops.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

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
# 		"vyshuwaops.tasks.all"
# 	],
# 	"daily": [
# 		"vyshuwaops.tasks.daily"
# 	],
# 	"hourly": [
# 		"vyshuwaops.tasks.hourly"
# 	],
# 	"weekly": [
# 		"vyshuwaops.tasks.weekly"
# 	],
# 	"monthly": [
# 		"vyshuwaops.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "vyshuwaops.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "vyshuwaops.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "vyshuwaops.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["vyshuwaops.utils.before_request"]
# after_request = ["vyshuwaops.utils.after_request"]

# Job Events
# ----------
# before_job = ["vyshuwaops.utils.before_job"]
# after_job = ["vyshuwaops.utils.after_job"]

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
# 	"vyshuwaops.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

