import frappe
from frappe.integrations.utils import get_payment_gateway_controller

@frappe.whitelist()
def create_payment_request(events):
    booking = frappe.get_doc("Festa Booking", events)
    
    # Get Razorpay controller (from Frappe Payments)
    controller = get_payment_gateway_controller("Razorpay")
    
    payment_details = {
        "amount": int(booking.total_amount * 100),  # Razorpay expects paise
        "currency": "INR",
        "reference_doctype": "Festa Booking",
        "reference_docname": booking.name,
        "receipt": booking.name,
        "customer_name": booking.user_name,
        "customer_email": booking.user_email
    }

    # Create Razorpay order
    order = controller.create_order(**payment_details)
    
    return order
