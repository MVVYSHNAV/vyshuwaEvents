import frappe
import hmac
import hashlib
import io
import json
import base64
import qrcode
from frappe.model.document import Document
from frappe.utils import nowdate, get_url
from vyshuwaops.api.api import create_payment, get_payment_gateway_controller


class FestaBooking(Document):
    # ----------------------------
    # Validation Hooks
    # ----------------------------
    def validate(self):
        self.set_total()
        self.set_currency()

    def before_insert(self):
        if not self.user:
            self.user = frappe.session.user

    def set_currency(self):
        if self.attendes and hasattr(self.attendes[0], "currency"):
            self.currency = self.attendes[0].currency
        else:
            self.currency = frappe.db.get_default("currency")

    def set_total(self):
        total = 0
        for attende in self.attendes:
            try:
                total += float(attende.price)
            except Exception:
                frappe.throw(f"Invalid price for attendee {attende.full_name}")
        self.total_amount = total

    # ----------------------------
    # Submission & Payment
    # ----------------------------
    def on_submit(self):
        """
        Workflow on booking submission:
        1. Generate tickets
        2. Create Sales Order
        3. Generate QR
        4. Send emails
        5. Create Payment Entry
        """
        self.generate_tickets()

        if not self.sales_order:
            self.create_sales_order()

        self.generate_qr_code()
        self.send_booking_emails()

        # Auto-create payment entry for attendees
        if "Attendee" in frappe.get_roles(self.user):
            try:
                create_payment(self.name)
            except Exception as e:
                frappe.msgprint(f"⚠️ Payment Entry could not be created: {e}")

    # ----------------------------
    # Ticket generation
    # ----------------------------
    def generate_tickets(self):
        for attende in self.attendes:
            exists = frappe.db.exists(
                "Festa Ticket",
                {"event": self.event, "booking": self.name, "attende_name": attende.full_name}
            )
            if exists:
                continue

            ticket = frappe.new_doc("Festa Ticket")
            ticket.event = self.event
            ticket.booking = self.name
            ticket.ticket_type = attende.ticket_type
            ticket.attende_name = attende.full_name
            ticket.insert(ignore_permissions=True)
            ticket.submit()

    # ----------------------------
    # QR code generation
    # ----------------------------
    def generate_qr_code(self):
        attendee_details = "\n".join([f"{a.full_name} ({a.ticket_type}, {a.email})" for a in self.attendes])
        qr_data = (
            f"Booking ID: {self.name}\n"
            f"Event: {self.event}\n"
            f"Booking User: {self.user}\n"
            f"Total Amount: {self.total_amount} {self.currency}\n"
            f"Attendees:\n{attendee_details}"
        )

        qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
        qr.add_data(qr_data)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        output = io.BytesIO()
        img.save(output, format="PNG")
        self._qr_bytes = output.getvalue()

        ascii_qr_io = io.StringIO()
        qr.print_ascii(out=ascii_qr_io, invert=True)
        self._ascii_qr = ascii_qr_io.getvalue()

        filename = f"Booking_{self.name}_QR.png"
        file_doc = frappe.get_doc({
            "doctype": "File",
            "file_name": filename,
            "attached_to_doctype": self.doctype,
            "attached_to_name": self.name,
            "content": base64.b64encode(self._qr_bytes).decode(),
            "is_private": 0
        })
        file_doc.insert(ignore_permissions=True)
        self.db_set("qr_code_url", get_url(file_doc.file_url))

    # ----------------------------
    # Emails
    # ----------------------------
    def send_booking_emails(self):
        recipients = []
        booking_email = self.user
        if "@" not in booking_email:
            booking_email = frappe.db.get_value("User", self.user, "email")

        if booking_email:
            recipients.append(booking_email)
            self._send_email(
                recipient=booking_email,
                subject=f"Booking Confirmation - {self.event}",
                message=f"Booking confirmed. QR attached.",
                attachments=[{"fname": f"Booking_{self.name}_QR.png", "fcontent": self._qr_bytes}]
            )

        for attende in self.attendes:
            if attende.email:
                recipients.append(attende.email)
                self._send_email(
                    recipient=attende.email,
                    subject=f"Your Ticket for {self.event}",
                    message=f"Ticket confirmed. QR attached.",
                    attachments=[{"fname": f"Booking_{self.name}_QR.png", "fcontent": self._qr_bytes}]
                )

        frappe.msgprint(f"Booking emails sent to: {', '.join(recipients)}")

    def _send_email(self, recipient, subject, message, attachments=None):
        frappe.sendmail(
            recipients=[recipient],
            subject=subject,
            message=message,
            attachments=attachments,
            reference_doctype=self.doctype,
            reference_name=self.name
        )

    # ----------------------------
    # Sales Order
    # ----------------------------
    def create_sales_order(self):
        if not self.attendes:
            frappe.throw("No attendees found to create Sales Order.")

        customer_name = frappe.db.get_value("Customer", {"customer_name": self.user}, "name")
        if not customer_name:
            customer = frappe.new_doc("Customer")
            customer.customer_name = self.user
            customer.customer_type = "Individual"
            customer.insert(ignore_permissions=True)
            customer_name = customer.name

        so = frappe.new_doc("Sales Order")
        so.customer = customer_name
        so.transaction_date = nowdate()
        so.company = frappe.db.get_default("Company")
        so.currency = self.currency

        for attende in self.attendes:
            item_code = frappe.get_value("Festa Ticket Type", attende.ticket_type, "item_code")
            if not item_code or not frappe.db.exists("Item", item_code):
                frappe.throw(f"Item Code '{item_code}' does not exist for attendee {attende.full_name}")

            so.append("items", {
                "item_code": item_code,
                "item_name": f"Ticket - {attende.ticket_type}",
                "description": f"Ticket for {attende.full_name} ({attende.email})",
                "qty": 1,
                "rate": float(attende.price),
                "delivery_date": nowdate(),
            })

        so.insert(ignore_permissions=True)
        so.submit()
        self.sales_order = so.name
        frappe.msgprint(f"Sales Order {so.name} created for Booking {self.name}")

    # ----------------------------
    # Razorpay Verification & Webhook (Optional)
    # ----------------------------
    @staticmethod
    @frappe.whitelist()
    def verify_payment(docname, payment_id, order_id, signature):
        booking = frappe.get_doc("Festa Booking", docname)
        controller = get_payment_gateway_controller("Razorpay")

        controller.verify_payment_signature({
            "razorpay_order_id": order_id,
            "razorpay_payment_id": payment_id,
            "razorpay_signature": signature
        })

        payment_list = frappe.get_all(
            "Festa Payment",
            filters={"booking": booking.name, "razorpay_order_id": order_id},
            limit=1
        )
        if not payment_list:
            frappe.throw("Payment record not found.")

        payment_doc = frappe.get_doc("Festa Payment", payment_list[0].name)
        payment_doc.razorpay_payment_id = payment_id
        payment_doc.razorpay_signature = signature
        payment_doc.payment_status = "Paid"
        payment_doc.save(ignore_permissions=True)
        booking.db_set("payment_status", "Paid")
        frappe.msgprint(f"Payment for Booking {booking.name} verified.")

    @staticmethod
    @frappe.whitelist(allow_guest=True)
    def razorpay_webhook():
        webhook_secret = frappe.db.get_single_value("Razorpay Settings", "webhook_secret") or "your_secret_here"
        payload = frappe.local.request.get_data(as_text=True)
        signature = frappe.local.request.headers.get("X-Razorpay-Signature")

        if not FestaBooking.verify_razorpay_signature(payload, signature, webhook_secret):
            frappe.respond_as_web_page("Error", "Invalid signature", status_code=400)
            return

        event = json.loads(payload)
        FestaBooking.handle_razorpay_event(event)
        return "Webhook received"

    @staticmethod
    def verify_razorpay_signature(payload, signature, secret):
        generated_signature = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(generated_signature, signature)

    @staticmethod
    def handle_razorpay_event(event):
        event_type = event.get("event")
        payment_entity = event.get("payload", {}).get("payment", {}).get("entity", {})
        razorpay_order_id = payment_entity.get("order_id")
        razorpay_payment_id = payment_entity.get("id")

        if event_type == "payment.captured":
            FestaBooking.update_payment_status(razorpay_order_id, razorpay_payment_id, "Paid")
        elif event_type == "payment.failed":
            FestaBooking.update_payment_status(razorpay_order_id, razorpay_payment_id, "Failed")

    @staticmethod
    def update_payment_status(order_id, payment_id, status):
        payment_list = frappe.get_all("Festa Payment", filters={"razorpay_order_id": order_id}, limit=1)
        if not payment_list:
            frappe.log_error(f"Payment with order_id {order_id} not found", "Razorpay Webhook")
            return

        payment_doc = frappe.get_doc("Festa Payment", payment_list[0].name)
        payment_doc.razorpay_payment_id = payment_id
        payment_doc.payment_status = status
        payment_doc.save(ignore_permissions=True)

        booking = frappe.get_doc("Festa Booking", payment_doc.booking)
        booking.db_set("payment_status", status)
