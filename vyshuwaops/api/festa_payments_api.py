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

        # Create Sales Invoice
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

        # Get mode of payment (fallback to Cash)
        try:
            mode_of_payment = (
                frappe.db.get_value("Company", sales_order.company, "default_mode_of_payment")
                or "Cash"
            )
        except Exception:
            mode_of_payment = "Cash"

        # Create Payment Entry
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
                "outstanding_amount": invoice.grand_total,
                "allocated_amount": invoice.grand_total,
            }],
        })
        payment_entry.insert(ignore_permissions=True)
        payment_entry.submit()

        # Update booking payment status
        booking.db_set("payment_status", "Paid")

        # ✅ Submit the booking at the end (if still in draft)
        if booking.docstatus == 0:
            booking.submit()
            frappe.logger().info(f"🎉 Festa Booking {booking.name} submitted after successful invoice & payment.")

        frappe.msgprint(
            f"Invoice {invoice.name} and Payment Entry {payment_entry.name} created. "
            f"Booking {booking.name} submitted successfully."
        )

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

# =====================================================
#  PAYMENT CAPTURE PROCESSOR
# =====================================================
def _process_payment_captured(payment_data):
    """Triggered when Razorpay sends payment.captured event."""
    try:
        payment_id = payment_data.get("id")
        amount = float(payment_data.get("amount", 0)) / 100.0
        email = payment_data.get("email")
        status = payment_data.get("status")
        token = (payment_data.get("notes") or {}).get("booking_id")

        frappe.logger().info(f"💰 Processing payment.captured for Booking {token}")

        # ------------------------------
        # Validate Booking Reference
        # ------------------------------
        if not token:
            frappe.logger().error(f"❌ No booking_id found in payment notes for payment {payment_id}")
            return

        if status != "captured":
            frappe.logger().info(f"⏸ Payment {payment_id} not captured (status: {status})")
            return

        booking = frappe.get_doc("Festa Booking", token)
        if not booking:
            frappe.logger().error(f"❌ Festa Booking not found: {token}")
            return

        # =================================================
        # 1️⃣ Create Payment Entry
        # =================================================
        payment_entry = frappe.new_doc("Payment Entry")
        payment_entry.payment_type = "Receive"
        payment_entry.party_type = "Customer"
        payment_entry.party = booking.customer or email
        payment_entry.posting_date = nowdate()
        payment_entry.mode_of_payment = "Razorpay"
        payment_entry.company = booking.company
        payment_entry.paid_amount = amount
        payment_entry.received_amount = amount
        payment_entry.paid_to = (
            frappe.db.get_value("Company", booking.company, "default_bank_account")
            or frappe.db.get_value("Company", booking.company, "default_cash_account")
        )
        payment_entry.references = [{
            "reference_doctype": "Festa Booking",
            "reference_name": booking.name,
            "allocated_amount": amount
        }]
        payment_entry.insert(ignore_permissions=True)
        payment_entry.submit()
        frappe.logger().info(f"✅ Payment Entry created: {payment_entry.name}")

        # =================================================
        # 2️⃣ Update Status and Submit Festa Booking 
        # (Submission now happens AFTER payment status is set to Paid)
        # =================================================
        # Update fields
        booking.db_set("payment_status", "Paid")
        booking.db_set("razorpay_payment_id", payment_id)
        frappe.db.commit() # Commit the payment status change

        # Submit the booking if it was in Draft status (docstatus == 0)
        if booking.docstatus == 0:
            booking.submit()
            frappe.logger().info(f"🎉 Festa Booking {booking.name} submitted successfully after payment.")

        # =================================================
        # 3️⃣ Optional: Create Sales Invoice automatically
        # =================================================
        try:
            if booking.sales_order:
                sales_order = frappe.get_doc("Sales Order", booking.sales_order)
                invoice = frappe.get_doc({
                    "doctype": "Sales Invoice",
                    "customer": sales_order.customer,
                    "company": sales_order.company,
                    "posting_date": nowdate(),
                    "due_date": nowdate(),
                    "items": [
                        {
                            "item_code": i.item_code,
                            "qty": i.qty,
                            "rate": i.rate
                        } for i in sales_order.items
                    ],
                })
                invoice.insert(ignore_permissions=True)
                invoice.submit()
                frappe.logger().info(f"🧾 Sales Invoice {invoice.name} created for Booking {booking.name}")
        except Exception:
            frappe.log_error(frappe.get_traceback(), "Razorpay Sales Invoice Creation Error")

    except Exception:
        frappe.log_error(frappe.get_traceback(), "Razorpay Payment Captured Handler Error")



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