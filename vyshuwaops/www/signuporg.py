import frappe
from frappe import _

@frappe.whitelist(allow_guest=True)
def sign_up_organiser(full_name, email, password):
    """
    Sign up a new organiser user and auto-login.
    """

    # Check if user already exists
    if frappe.db.exists("User", email):
        frappe.throw(_("Email already registered"))

    try:
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

        # Assign organiser role
        user.add_roles("Organizer")

        # Commit to DB
        frappe.db.commit()

        # Auto-login the new user
        frappe.local.login_manager.login_as(user.name)

        return {"message": _("Organiser account created successfully")}
    
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(frappe.get_traceback(), "Organiser Signup Error")
        frappe.throw(_("Could not create organiser account: {0}").format(str(e)))
