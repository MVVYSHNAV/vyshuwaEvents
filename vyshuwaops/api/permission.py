import frappe


# --------------------------------------------------
# UNIVERSAL HAS_PERMISSION
# --------------------------------------------------
def has_permission(doc, ptype="read", user=None):
    if not user:
        user = frappe.session.user

    roles = frappe.get_roles(user)

    # Admins or System Managers have full access
    if "Admin" in roles or "System Manager" in roles:
        return True

    # Organizers can manage all events and bookings
    if "Organizer" in roles and doc.doctype in ["Festa Event", "Festa Booking"]:
        return True

    # Attendees can manage their own bookings and view published events
    if "Attendee" in roles:
        if doc.doctype == "Festa Booking" and doc.owner == user:
            return True
        if doc.doctype == "Festa Event":
            # Optional: allow viewing published events
            if hasattr(doc, "is_published") and doc.is_published:
                return True

    return False


# --------------------------------------------------
# PER DOCTYPE QUERY CONDITIONS
# --------------------------------------------------
def get_permission_query_conditions(user):
    """Fallback function (shouldn't be used directly)."""
    return ""


def get_festa_event_conditions(user):
    """Applied when viewing Festa Event list."""
    if not user:
        user = frappe.session.user

    roles = frappe.get_roles(user)

    if "Admin" in roles or "System Manager" in roles:
        return ""

    if "Organizer" in roles:
        return ""  # all events visible to organizers

    if "Attendee" in roles:
        # Only show published events
        return "(`tabFesta Event`.`is_published` = 1)"

    return "1=0"


def get_festa_booking_conditions(user):
    """Applied when viewing Festa Booking list."""
    if not user:
        user = frappe.session.user

    roles = frappe.get_roles(user)

    if "Admin" in roles or "System Manager" in roles:
        return ""

    if "Organizer" in roles:
        return ""  # all bookings visible to organizers

    if "Attendee" in roles:
        # Only show own bookings
        return f"(`tabFesta Booking`.`owner` = '{user}')"

    return "1=0"
