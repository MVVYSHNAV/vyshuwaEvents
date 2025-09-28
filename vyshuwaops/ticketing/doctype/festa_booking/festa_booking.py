# Copyright (c) 2025
# It enables organizers to create and publish events, define venues, 
# and set ticket categories, while attendees can browse events, book tickets, 
# and receive confirmations with secure online payments.
# Vyshnav and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import nowdate, get_url
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from frappe.types import DF
    from vyshuwaops.ticketing.doctype.festa_attende_booking.festa_attende_booking import FestaAttendeBooking

from frappe.integrations.utils import get_payment_gateway_controller


class FestaBooking(Document):
    # begin: auto-generated types
    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF
        from vyshuwaops.ticketing.doctype.festa_attende_booking.festa_attende_booking import FestaAttendeBooking

        amended_from: DF.Link | None
        attendes: DF.Table[FestaAttendeBooking]
        currency: DF.Link | None
        event: DF.Link
        qr_code_url: DF.AttachImage | None
        total_amount: DF.Currency
        user: DF.Link
        sales_order: DF.Link | None
        payment_status: DF.Select | None
        razorpay_order_id: DF.Data | None
        razorpay_payment_id: DF.Data | None
        razorpay_signature: DF.Data | None
    # end: auto-generated types

    def validate(self):
        self.set_total()
        self.set_currency()

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

    def on_submit(self):
        self.generate_tickets()
        if not self.get("sales_order"):
            self.create_sales_order()
        self.generate_qr_code()
        self.send_booking_emails()

    def generate_tickets(self):
        for attende in self.attendes:
            ticket = frappe.new_doc("Festa Ticket")
            ticket.event = self.event
            ticket.booking = self.name
            ticket.ticket_type = attende.ticket_type
            ticket.attende_name = attende.full_name
            ticket.insert(ignore_permissions=True)
            ticket.submit()

    def generate_qr_code(self):
        import io, qrcode, base64

        attendee_details = "\n".join([
            f"{a.full_name} ({a.ticket_type}, {a.email})" for a in self.attendes
        ])
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
        b64_data = base64.b64encode(output.getvalue()).decode()

        filename = f"Booking_{self.name}_QR.png"
        file_doc = frappe.get_doc({
            "doctype": "File",
            "file_name": filename,
            "attached_to_doctype": self.doctype,
            "attached_to_name": self.name,
            "content": b64_data,
            "is_private": 0
        })
        file_doc.insert(ignore_permissions=True)
        self.db_set("qr_code_url", get_url(file_doc.file_url))

    def send_booking_emails(self):
        recipients = []
        qr_img_html = f'<img src="{self.qr_code_url}" alt="Booking QR Code">' if self.qr_code_url else ""

        booking_email = self.user
        if "@" not in booking_email:
            booking_email = frappe.db.get_value("User", self.user, "email")

        if booking_email:
            recipients.append(booking_email)
            self._send_email(
                recipient=booking_email,
                subject=f"Booking Confirmation - {self.event}",
                message=f"""
                    <p>Dear {self.user},</p>
                    <p>Thank you for booking tickets for <b>{self.event}</b>.</p>
                    <p><b>Booking ID:</b> {self.name}<br>
                    <b>Total Amount:</b> {self.total_amount} {self.currency}</p>
                    {qr_img_html}
                    <p>Best regards,<br>Event Team</p>
                """
            )

        for attende in self.attendes:
            if attende.email:
                recipients.append(attende.email)
                self._send_email(
                    recipient=attende.email,
                    subject=f"Your Ticket for {self.event}",
                    message=f"""
                        <p>Dear {attende.full_name},</p>
                        <p>You are registered as an attendee for <b>{self.event}</b>.</p>
                        <p><b>Ticket Type:</b> {attende.ticket_type}<br>
                        <b>Booking ID:</b> {self.name}</p>
                        {qr_img_html}
                        <p>Please keep this email as your ticket confirmation.</p>
                        <p>Best regards,<br>Event Team</p>
                    """
                )

        frappe.msgprint(f"Booking emails sent to: {', '.join(recipients)}")

    def _send_email(self, recipient, subject, message):
        frappe.sendmail(
            recipients=[recipient],
            subject=subject,
            message=message,
            reference_doctype=self.doctype,
            reference_name=self.name
        )

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
            item_code = frappe.get_value("Festa Ticket Type", attende.ticket_type, "title")
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

    # ---------------- Razorpay Payment Integration ---------------- #

    @frappe.whitelist()
    def create_payment(self):
        """Create Razorpay payment order"""
        controller = get_payment_gateway_controller("Razorpay")
        payment_details = {
            "amount": int(self.total_amount * 100),
            "currency": self.currency or "INR",
            "reference_doctype": self.doctype,
            "reference_docname": self.name,
            "receipt": self.name,
            "customer_name": self.user,
            "customer_email": frappe.db.get_value("User", self.user, "email"),
        }
        order = controller.create_order(**payment_details)
        self.db_set("razorpay_order_id", order.get("id"))
        self.db_set("payment_status", "Draft")
        return order

    @frappe.whitelist()
    def verify_payment(self, payment_id, order_id, signature):
        """Verify Razorpay payment signature"""
        controller = get_payment_gateway_controller("Razorpay")
        controller.verify_payment_signature({
            "razorpay_order_id": order_id,
            "razorpay_payment_id": payment_id,
            "razorpay_signature": signature
        })
        self.db_set("razorpay_payment_id", payment_id)
        self.db_set("razorpay_signature", signature)
        self.db_set("payment_status", "Paid")
        frappe.msgprint(f"Payment for Booking {self.name} verified successfully.")
