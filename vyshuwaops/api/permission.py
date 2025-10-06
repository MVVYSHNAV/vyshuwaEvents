# permissions.py
import frappe

def get_event_permission_query(user):
    """Filter events based on user role"""
    if "Admin" in frappe.get_roles(user) or "System Manager" in frappe.get_roles(user):
        return None  # No filter for admin
    
    if "Organizer" in frappe.get_roles(user):
        return f"""(`tabEvent`.organizer = {frappe.db.escape(user)})"""
    
    if "Attendee" in frappe.get_roles(user):
        return """(`tabEvent`.status = 'Published')"""
    
    return """(1=0)"""  # No access

def get_booking_permission_query(user):
    """Filter bookings based on user role"""
    if "Admin" in frappe.get_roles(user) or "System Manager" in frappe.get_roles(user):
        return None
    
    if "Organizer" in frappe.get_roles(user):
        return f"""(`tabBooking`.event IN (
            SELECT name FROM `tabEvent` WHERE organizer = {frappe.db.escape(user)}
        ))"""
    
    if "Attendee" in frappe.get_roles(user):
        return f"""(`tabBooking`.attendee = {frappe.db.escape(user)})"""
    
    return """(1=0)"""