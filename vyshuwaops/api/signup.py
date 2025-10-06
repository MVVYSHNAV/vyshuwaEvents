import frappe

@frappe.whitelist(allow_guest=True, methods=["POST"])
def register_user(full_name, email, password):
    try:
        if frappe.db.exists("User", {"email": email}):
            return {"success": False, "message": "Email already registered"}

        user = frappe.get_doc({
            "doctype": "User",
            "email": email,
            "first_name": full_name,
            "enabled": 1,
            "new_password": password,
            "send_welcome_email": 1
        })
        user.insert(ignore_permissions=True)
        frappe.db.commit()

        return {"success": True, "message": "User registered successfully"}
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Signup Error")
        return {"success": False, "message": str(e)}
