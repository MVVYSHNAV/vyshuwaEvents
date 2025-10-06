# apps/vyshuwaops/vyshuwaops/www/signup.py
import frappe
from frappe import _

@frappe.whitelist(allow_guest=True)
def sign_up_user(full_name, email, password):
    """
    Sign up a new user and auto-login.
    """
    # Check if user already exists
    if frappe.db.exists("User", email):
        frappe.throw(_("Email already registered"))

    # Create the user
    user = frappe.get_doc({
        "doctype": "User",
        "email": email,
        "first_name": full_name,
        "enabled": 1,
        "send_welcome_email": 0
    })
    user.insert(ignore_permissions=True)

    # Set password
    frappe.utils.password.update_password(user.name, password)

    # Assign a role
    user.add_roles("Attendee")

    # Auto login the user
    frappe.local.login_manager.login_as(user.name)

    # Return success message (frontend can handle redirect)
    return {"message": _("Account created successfully")}
