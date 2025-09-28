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
from frappe.integrations.utils import get_payment_gateway_controller

if TYPE_CHECKING:
    from frappe.types import DF
    from vyshuwaops.ticketing.doctype.festa_attende_booking.festa_attende_booking import FestaAttendeBooking


class FestaBooking(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

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
    # end: auto-generated types

    def validate(self):
        """Run validations before save"""
        self.set_total()
        self.set_currency()

    def set_currency(self):
        """Set booking currency from the first attendee"""
        if self.attendes and hasattr(self.attendes[0], "currency"):
            self.currency = self.attendes[0].currency
        else:
            self.currency = frappe.db.get_default("currency")  # fallback

    def set_total(self):
        """Calculate total amount from attendees"""
        total = 0
        for attende in self.attendes:
            try:
                total += float(attende.price)
            except Exception:
                frappe.throw(f"Invalid price for attendee {attende.full_name}")
        self.total_amount = total

    def on_submit(self):
        """On submit: create tickets, sales order, generate QR code, and send emails"""
        self.generate_tickets()
        if not self.get("sales_order"):
            self.create_sales_order()
        self.generate_qr_code()
        self.send_booking_emails()

    def generate_tickets(self):
        """Create Festa Ticket for each attendee"""
        for attende in self.attendes:
            ticket = frappe.new_doc("Festa Ticket")
            ticket.event = self.event
            ticket.booking = self.name
            ticket.ticket_type = attende.ticket_type
            ticket.attende_name = attende.full_name
            ticket.insert(ignore_permissions=True)
            ticket.submit()

    def generate_qr_code(self):
        """Generate QR code with full booking details and attach to Booking"""
        import io
        import qrcode
        import base64

        # Prepare attendee details
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

        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        # Convert image to base64
        output = io.BytesIO()
        img.save(output, format="PNG")
        b64_data = base64.b64encode(output.getvalue()).decode()

        # Save as File in Frappe
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

        # Save public URL
        self.db_set("qr_code_url", get_url(file_doc.file_url))

    def send_booking_emails(self):
        """Send email notifications to booking user and attendees with QR code"""
        recipients = []

        qr_img_html = f'<img src="{self.qr_code_url}" alt="Booking QR Code">' if self.qr_code_url else ""

        # Booking User
        booking_email = self.user
        if "@" not in booking_email:  # system user
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

        # Each Attendee
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
        """Helper to send email"""
        frappe.sendmail(
            recipients=[recipient],
            subject=subject,
            message=message,
            reference_doctype=self.doctype,
            reference_name=self.name
        )

    def create_sales_order(self):
        """Create Sales Order linked to this booking (only once, on submit)"""
        if not self.attendes:
            frappe.throw("No attendees found to create Sales Order.")

        # Get or create Customer
        customer_name = frappe.db.get_value("Customer", {"customer_name": self.user}, "name")
        if not customer_name:
            customer = frappe.new_doc("Customer")
            customer.customer_name = self.user
            customer.customer_type = "Individual"
            customer.insert(ignore_permissions=True)
            customer_name = customer.name

        # Create Sales Order
        so = frappe.new_doc("Sales Order")
        so.customer = customer_name
        so.transaction_date = nowdate()
        so.company = frappe.db.get_default("Company")
        so.currency = self.currency

        # Add attendees as line items
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

        # Link Sales Order back to booking (prevents duplicate creation)
        self.sales_order = so.name
        frappe.msgprint(f"Sales Order {so.name} created for Booking {self.name}")

        
    @frappe.whitelist()
    def create_payment(self):
        """Create a Razorpay payment order via Frappe Payments app"""
        controller = get_payment_gateway_controller("Razorpay")
        
        payment_details = {
            "amount": int(self.total_amount * 100),  # Razorpay expects paise
            "currency": self.currency or "INR",
            "reference_doctype": self.doctype,
            "reference_docname": self.name,
            "receipt": self.name,
            "customer_name": self.user,
            "customer_email": frappe.db.get_value("User", self.user, "email"),
        }

        # Create Razorpay order
        order = controller.create_order(**payment_details)

        # Save Razorpay order ID
        self.db_set("razorpay_order_id", order.get("id"))
        self.db_set("payment_status", "Draft")

        return order

    
