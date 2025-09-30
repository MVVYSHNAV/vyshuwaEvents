import frappe

@frappe.whitelist(allow_guest=True)
def register_user_with_role(email, full_name):
    if frappe.db.exists("User", email):
        return {"status": "error", "message": "User already exists"}

    user = frappe.get_doc({
        "doctype": "User",
        "email": email,
        "first_name": full_name.split(" ")[0],
        "last_name": " ".join(full_name.split(" ")[1:]),
        "enabled": 1,
       
        "send_welcome_email": 0,
        
    })
    user.insert(ignore_permissions=True)
    user.add_roles("Organiser")
    frappe.db.commit()

    return {
        "status": "success",
        "message": "User created successfully",
        "user": user.name
    }
