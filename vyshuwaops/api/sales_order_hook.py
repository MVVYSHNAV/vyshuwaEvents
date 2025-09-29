import frappe
from vyshuwaops.api.api import create_payment

def handle_sales_order_submit(doc, method):
    """Auto-create payment request when Sales Order is submitted for a Festa Booking"""
    booking = frappe.db.get_value("Festa Booking", {"sales_order": doc.name}, "name")
    if booking:
        frappe.msgprint(f"Creating Payment Request for Booking {booking} via Sales Order {doc.name}")
        create_payment(booking)