import frappe
import frappe
import hmac
import hashlib
import json

def on_submit_handler(doc, method):
    # Call the class method directly
    if hasattr(doc, "on_submit"):
        doc.on_submit()

def get_payment_gateway_controller(payment_gateway_name):
    """
    Safely get payment gateway controller doc for given gateway name.
    """
    gateway_doc = frappe.get_doc("Payment Gateway", payment_gateway_name)

    if gateway_doc.gateway_controller:
        try:
            return frappe.get_doc(gateway_doc.gateway_settings, gateway_doc.gateway_controller)
        except Exception as e:
            frappe.throw(f"Error loading gateway controller: {e}")

    # fallback to <Payment Gateway> Settings doc
    settings_doctype = f"{payment_gateway_name} Settings"
    if frappe.db.exists("DocType", settings_doctype):
        try:
            return frappe.get_doc(settings_doctype)
        except Exception as e:
            frappe.throw(f"Error loading settings doc '{settings_doctype}': {e}")

    frappe.throw(f"Payment Gateway controller/settings not found for '{payment_gateway_name}'")


def create_payment(booking_name: str):
    """
    Create a Payment Entry for a submitted Festa Booking.
    - Fetches the Sales Order linked to the booking
    - Creates a Payment Entry against that Sales Order
    """

    booking = frappe.get_doc("Festa Booking", booking_name)

    if not booking.sales_order:
        frappe.throw(f"No Sales Order linked with Booking {booking_name}")

    sales_order = frappe.get_doc("Sales Order", booking.sales_order)

    # Determine customer
    customer = sales_order.customer
    if not customer:
        frappe.throw(f"Sales Order {sales_order.name} has no customer")

    # Get default mode of payment (you can customize this)
    mode_of_payment = frappe.db.get_single_value("Accounts Settings", "default_mode_of_payment")
    if not mode_of_payment:
        mode_of_payment = "Cash"  # fallback

    payment = frappe.new_doc("Payment Entry")
    payment.payment_type = "Receive"
    payment.company = sales_order.company
    payment.posting_date = nowdate()
    payment.mode_of_payment = mode_of_payment
    payment.party_type = "Customer"
    payment.party = customer
    payment.paid_amount = sales_order.grand_total
    payment.received_amount = sales_order.grand_total
    payment.paid_to = frappe.get_value("Company", sales_order.company, "default_receivable_account")
    payment.references = []

    # Link to Sales Order
    payment.append("references", {
        "reference_doctype": "Sales Order",
        "reference_name": sales_order.name,
        "total_amount": sales_order.grand_total,
        "outstanding_amount": sales_order.grand_total,
        "allocated_amount": sales_order.grand_total
    })

    payment.insert(ignore_permissions=True)
    payment.submit()

    # Update Booking with payment info
    booking.db_set("payment_status", "Paid")
    frappe.msgprint(f"Payment Entry {payment.name} created for Booking {booking.name}")

    return payment.name


@frappe.whitelist()
def verify_payment(docname, payment_id, order_id, signature):
    booking = frappe.get_doc("Festa Booking", docname)
    controller = get_payment_gateway_controller("Razorpay")

    # Verify the payment signature
    controller.verify_payment_signature({
        "razorpay_order_id": order_id,
        "razorpay_payment_id": payment_id,
        "razorpay_signature": signature
    })

    # Find linked payment doc
    payment_list = frappe.get_all("Festa Payment", filters={"booking": booking.name, "razorpay_order_id": order_id}, limit=1)
    if not payment_list:
        frappe.throw("Payment record not found for this booking and order.")

    payment_doc = frappe.get_doc("Festa Payment", payment_list[0].name)
    payment_doc.razorpay_payment_id = payment_id
    payment_doc.razorpay_signature = signature
    payment_doc.payment_status = "Paid"
    payment_doc.save()

    # Optionally update booking status
    booking.payment_status = "Paid"
    booking.save()

    frappe.msgprint(f"Payment for Booking {booking.name} verified successfully.")



@frappe.whitelist(allow_guest=True)  # allow_guest because Razorpay posts without login
def razorpay_webhook():
    # Get webhook secret key from Payment Gateway settings or env variable
    webhook_secret = frappe.db.get_single_value("Razorpay Settings", "webhook_secret") or "your_secret_here"

    # Get the request body and headers
    payload = frappe.local.request.get_data(as_text=True)
    signature = frappe.local.request.headers.get("X-Razorpay-Signature")

    # Verify signature
    if not verify_razorpay_signature(payload, signature, webhook_secret):
        frappe.respond_as_web_page("Error", "Invalid signature", status_code=400)
        return

    event = json.loads(payload)

    # Handle events here
    handle_razorpay_event(event)

    return "Webhook received"

def verify_razorpay_signature(payload, signature, secret):
    generated_signature = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(generated_signature, signature)

def handle_razorpay_event(event):
    event_type = event.get("event")
    payload = event.get("payload", {})

    if event_type == "payment.captured":
        payment_entity = payload.get("payment", {}).get("entity", {})
        razorpay_order_id = payment_entity.get("order_id")
        razorpay_payment_id = payment_entity.get("id")
        # Update your payment record status here
        update_payment_status(razorpay_order_id, razorpay_payment_id, "Paid")

    elif event_type == "payment.failed":
        payment_entity = payload.get("payment", {}).get("entity", {})
        razorpay_order_id = payment_entity.get("order_id")
        razorpay_payment_id = payment_entity.get("id")
        update_payment_status(razorpay_order_id, razorpay_payment_id, "Failed")

    # Add more event types as needed

def update_payment_status(order_id, payment_id, status):
    payment = frappe.get_all("Festa Payment", filters={"razorpay_order_id": order_id}, limit=1)
    if not payment:
        frappe.log_error(f"Payment with order_id {order_id} not found for webhook update", "Razorpay Webhook")
        return

    payment_doc = frappe.get_doc("Festa Payment", payment[0].name)
    payment_doc.razorpay_payment_id = payment_id
    payment_doc.payment_status = status
    payment_doc.save()

    # Optionally update Festa Booking payment_status
    booking = frappe.get_doc("Festa Booking", payment_doc.booking)
    booking.payment_status = status
    booking.save()