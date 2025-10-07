import frappe
from vyshuwaops.api.api import create_payment_request

def handle_sales_order_submit(doc, method):
    """Auto-create payment request when Sales Order is submitted for a Festa Booking"""
    booking_name = frappe.db.get_value("Festa Booking", {"sales_order": doc.name}, "name")
    if booking_name:
        booking = frappe.get_doc("Festa Booking", booking_name)
        frappe.msgprint(f"Creating Payment Request for Booking {booking_name} via Sales Order {doc.name}")
        create_payment_request(
            token=booking_name,
            email=booking.user,
            amount=booking.total_amount,
            currency=booking.currency
        )