import frappe
from vyshuwaops.api.api import create_payment_request

def handle_sales_order_submit(doc, method):
    """
    Automatically create a Payment Request when a Sales Order 
    is submitted for a linked Festa Booking.
    """
    try:
        # Find the Festa Booking linked to this Sales Order
        booking_name = frappe.db.get_value("Festa Booking", {"sales_order": doc.name}, "name")

        if not booking_name:
            frappe.logger().info(f"No Festa Booking linked to Sales Order {doc.name}")
            return

        booking = frappe.get_doc("Festa Booking", booking_name)

        frappe.msgprint(f"💳 Creating Payment Request for Booking {booking_name} via Sales Order {doc.name}")

        # Create payment request using helper
        pr_name = create_payment_request(
            token=booking_name,
            email=booking.user,
            amount=booking.total_amount,
            currency=booking.currency or "INR"
        )

        if pr_name:
            frappe.logger().info(f"✅ Payment Request {pr_name} created for Booking {booking_name}")
            booking.db_set("payment_request", pr_name)
            frappe.db.commit()
        else:
            frappe.log_error(f"Failed to create payment request for {booking_name}", "Festa Payment Request Error")

    except Exception:
        frappe.log_error(frappe.get_traceback(), "Festa Hook: handle_sales_order_submit")
