import frappe
import hmac
import hashlib
import json
from frappe.utils import nowdate

# ------------------------------------------------
# Public API: Create Invoice + Payment Entry
# ------------------------------------------------

@frappe.whitelist()
def create_invoice_and_payment(booking_name):
    """Create Sales Invoice and Payment Entry for Festa Booking."""
    try:
        booking = frappe.get_doc("Festa Booking", booking_name)
        if not booking.sales_order:
            frappe.throw(f"No Sales Order linked with Booking {booking_name}")

        sales_order = frappe.get_doc("Sales Order", booking.sales_order)
        invoice = frappe.get_doc({
            "doctype": "Sales Invoice",
            "customer": sales_order.customer,
            "company": sales_order.company,
            "posting_date": nowdate(),
            "due_date": nowdate(),
            "items": [
                dict(item_code=i.item_code, qty=i.qty, rate=i.rate)
                for i in sales_order.items
            ],
        })
        invoice.insert(ignore_permissions=True)
        invoice.submit()

        try:
            mode_of_payment = frappe.db.get_single_value("Accounts Settings", "default_mode_of_payment")
        except Exception:
            mode_of_payment = "Cash"
        payment_entry = frappe.get_doc({
            "doctype": "Payment Entry",
            "payment_type": "Receive",
            "company": sales_order.company,
            "posting_date": nowdate(),
            "mode_of_payment": mode_of_payment,
            "party_type": "Customer",
            "party": sales_order.customer,
            "paid_amount": invoice.grand_total,
            "received_amount": invoice.grand_total,
            "paid_to": frappe.get_value("Company", sales_order.company, "default_cash_account"),
            "references": [{
                "reference_doctype": "Sales Invoice",
                "reference_name": invoice.name,
                "total_amount": invoice.grand_total,
                "outstanding_amount": invoice.outstanding_amount,
                "allocated_amount": invoice.grand_total,
            }],
        })
        payment_entry.insert(ignore_permissions=True)
        payment_entry.submit()

        booking.db_set("payment_status", "Paid")
        frappe.msgprint(f"Invoice {invoice.name} and Payment Entry {payment_entry.name} created for Booking {booking.name}")
        return {
            "invoice": invoice.name,
            "payment_entry": payment_entry.name,
            "status": "success"
        }

    except Exception:
        frappe.log_error(frappe.get_traceback(), "FestaAPI: create_invoice_and_payment")
        frappe.throw("Internal error in invoice/payment creation")


# ------------------------------------------------
# Public API: Razorpay Webhook Handler
# ------------------------------------------------

@frappe.whitelist(allow_guest=True)
def razorpay_webhook():
    
    """Main Razorpay webhook endpoint (called by Razorpay)."""
    try:
        frappe.local.response["http_status_code"] = 200
        signature = frappe.get_request_header("X-Razorpay-Signature")
        data = frappe.request.get_data(as_text=True)
        event = json.loads(data)
        print(event)
        frappe.log_error('data',event)

        try:
            webhook_secret = frappe.db.get_single_value("Razorpay Settings", "webhook_secret")
        except Exception:
            webhook_secret = 'vyshuwaops'
        if not webhook_secret:
            frappe.log_error("Missing webhook_secret in Razorpay Settings", "Razorpay Webhook Config Error")
            return "Webhook secret missing"

        expected_signature = hmac.new(
            webhook_secret.encode(), data.encode(), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(expected_signature, signature or ""):
            frappe.log_error("Invalid Razorpay webhook signature", "Razorpay Webhook Invalid Signature")
            frappe.local.response["http_status_code"] = 401
            return "Invalid signature"

        _handle_razorpay_event(event)
        return "OK"

    except Exception:
        frappe.log_error(frappe.get_traceback(), "Razorpay Webhook Fatal Error")
        frappe.local.response["http_status_code"] = 500
        return "Internal Error"

# ================================================
# Event Routing / Core Handlers (private)
# ================================================

def _handle_razorpay_event(event):
    try:
        event_type = event.get("event")
        payment_data = event.get("payload", {}).get("payment", {}).get("entity", {})
        if not payment_data:
            frappe.log_error(json.dumps(event)[:140], "Razorpay Empty Payload")
            return

        if event_type == "payment.captured":
            _process_payment_captured(payment_data)
        elif event_type == "payment.failed":
            _process_payment_failed(payment_data)
        else:
            frappe.log_error(f"Unhandled event: {event_type}", "Razorpay Webhook Info")
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Razorpay Event Handler Error")

def _process_payment_captured(payment_data):
    """Create Payment Request and Payment Entry on successful payment."""
    try:
        payment_id = payment_data.get("id")
        order_id = payment_data.get("order_id")
        amount = (payment_data.get("amount") or 0) / 100
        currency = payment_data.get("currency") or "INR"
        email = payment_data.get("email")
        contact = payment_data.get("contact")
        description = payment_data.get("description")
        notes = payment_data.get("notes", {})

        token = notes.get("token") or _extract_token_from_description(description)

        existing_entry = frappe.db.exists("Payment Entry", {"reference_no": payment_id})
        if existing_entry:
            frappe.logger().info(f"Payment Entry already exists for {payment_id}")
            return

        pr_name = frappe.db.get_value("Payment Request", {"reference_name": token})
        if not pr_name:
            pr_name = create_payment_request(token, email, amount, currency)
        pr_doc = frappe.get_doc("Payment Request", pr_name)

        payment_entry = frappe.new_doc("Payment Entry")
        payment_entry.payment_type = "Receive"
        payment_entry.posting_date = nowdate()
        payment_entry.mode_of_payment = "Razorpay"
        payment_entry.party_type = "Customer"
        payment_entry.party = pr_doc.party
        payment_entry.company = pr_doc.company
        payment_entry.reference_no = payment_id
        payment_entry.reference_date = nowdate()
        payment_entry.paid_amount = amount
        payment_entry.received_amount = amount
        payment_entry.currency = currency
        payment_entry.paid_to = frappe.db.get_value("Company", pr_doc.company, "default_receivable_account")

        payment_entry.insert(ignore_permissions=True)
        payment_entry.submit()

        pr_doc.db_set("status", "Paid")
        pr_doc.db_set("payment_entry", payment_entry.name)
        frappe.db.commit()

        frappe.logger().info(f"✅ Payment captured: {payment_id} | {amount} {currency}")

    except Exception:
        frappe.log_error(frappe.get_traceback(), "Razorpay Payment Capture Error")

def _process_payment_failed(payment_data):
    """Logs payment failure event."""
    try:
        email = payment_data.get("email")
        contact = payment_data.get("contact")
        amount = (payment_data.get("amount") or 0) / 100
        reason = payment_data.get("error_description") or "Unknown"
        frappe.log_error(f"Payment failed for {email or contact} | {amount} | {reason}", "Razorpay Payment Failed")
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Razorpay Payment Failed Handler Error")


# ---------------------------------------------
# Payment Request and Customer Utility (private)
# ---------------------------------------------

def create_payment_request(token, email, amount, currency):
    """Create Payment Request if not found."""
    try:
        customer = _get_or_create_customer(email)
        company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value("Global Defaults", "default_company")

        pr = frappe.new_doc("Payment Request")
        pr.party_type = "Customer"
        pr.party = customer
        pr.company = company
        pr.currency = currency
        pr.email_to = email
        pr.reference_doctype = "Sales Order"
        pr.reference_name = token or f"RZP-{frappe.generate_hash('', 8)}"
        pr.message = f"Auto-generated for Razorpay payment {token or ''}"
        pr.grand_total = amount
        pr.insert(ignore_permissions=True)
        pr.submit()

        frappe.db.commit()
        frappe.logger().info(f"💳 Created Payment Request {pr.name} for {email}")
        return pr.name

    except Exception:
        frappe.log_error(frappe.get_traceback(), "Razorpay Create Payment Request Error")
        return None

def _get_or_create_customer(email):
    """Get or create a Customer by email."""
    if not email:
        return "Guest"
    existing = frappe.db.get_value("Customer", {"email_id": email})
    if existing:
        return existing
    cust = frappe.new_doc("Customer")
    cust.customer_name = email.split("@")[0]
    cust.email_id = email
    cust.customer_type = "Individual"
    cust.insert(ignore_permissions=True)
    frappe.db.commit()
    return cust.name

def _extract_token_from_description(description):
    """Extract booking token from text like 'Payment for Festa Booking 5j0gj4por6'."""
    if not description:
        return None
    parts = description.split()
    if len(parts) >= 2:
        return parts[-1].strip()
    return None

