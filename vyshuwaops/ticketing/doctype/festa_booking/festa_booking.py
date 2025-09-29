# Copyright (c) 2025
# Vyshnav and contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import nowdate, get_url
from vyshuwaops.api.api import create_payment
import io, qrcode, base64

class FestaBooking(Document):
    # ----------------------------
    # Auto-generated type hints
    # ----------------------------
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

    # ----------------------------
    # Validation
    # ----------------------------
    def validate(self):
        self.set_total()
        self.set_currency()

    def set_currency(self):
        if self.attendes and hasattr(self.attendes[0], "currency"):
            self.currency = self.attendes[0].currency
        else:
            self.currency = frappe.db.get_default("currency")
    
    def before_insert(self):
        """Automatically set the booking user to the logged-in session user"""
        if not self.user:
            self.user = frappe.session.user

    def set_total(self):
        total = 0
        for attende in self.attendes:
            try:
                total += float(attende.price)
            except Exception:
                frappe.throw(f"Invalid price for attendee {attende.full_name}")
        self.total_amount = total

    # ----------------------------
    # Submission
    # ----------------------------
    def on_submit(self):
        """Main workflow on booking submission"""
        self.generate_tickets()
        if not self.get("sales_order"):
            self.create_sales_order()
        self.generate_qr_code()
        self.send_booking_emails()

        # Create payment request after sales order submission
        if self.sales_order:
            so_status = frappe.db.get_value("Sales Order", self.sales_order, "docstatus")
            if so_status == 1:  # Submitted
                try:
                    create_payment(self.name)
                except Exception as e:
                    frappe.msgprint(f"⚠️ Payment Request could not be created: {e}")

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
                frappe.msgprint(f"Ticket already exists for {attende.full_name}, skipping...")
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

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4
        )
        qr.add_data(qr_data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        output = io.BytesIO()
        img.save(output, format="PNG")
        qr_bytes = output.getvalue()  # store bytes for email attachment

        # Save as File in Frappe
        filename = f"Booking_{self.name}_QR.png"
        file_doc = frappe.get_doc({
            "doctype": "File",
            "file_name": filename,
            "attached_to_doctype": self.doctype,
            "attached_to_name": self.name,
            "content": base64.b64encode(qr_bytes).decode(),
            "is_private": 0
        })
        file_doc.insert(ignore_permissions=True)
        self.db_set("qr_code_url", get_url(file_doc.file_url))

        # Store bytes for email
        self._qr_bytes = qr_bytes

    # ----------------------------
    # Email
    # ----------------------------
    def send_booking_emails(self):
        recipients = []

        # Booking owner
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
                    <img src="{self.qr_code_url}" alt="Booking QR Code">
                    <p>Best regards,<br>Event Team</p>
                """,
                attachments=[{
                    "fname": f"Booking_{self.name}_QR.png",
                    "fcontent": self._qr_bytes
                }]
            )

        # Attendees
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
                        <img src="{self.qr_code_url}" alt="Booking QR Code">
                        <p>Please keep this email as your ticket confirmation.</p>
                        <p>Best regards,<br>Event Team</p>
                    """,
                    attachments=[{
                        "fname": f"Booking_{self.name}_QR.png",
                        "fcontent": self._qr_bytes
                    }]
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
    # Reminders
    # ----------------------------
    def send_reminder(self):
        recipients = []

        booking_email = self.user
        if "@" not in booking_email:
            booking_email = frappe.db.get_value("User", self.user, "email")
        if booking_email:
            recipients.append(booking_email)

        for attende in self.attendes:
            if attende.email:
                recipients.append(attende.email)

        if not recipients:
            return

        subject = f"Reminder: Upcoming Event - {self.event}"
        message = f"""
            <p>Hello,</p>
            <p>This is a friendly reminder for your upcoming event booking:</p>
            <p><b>Event:</b> {self.event}<br>
            <b>Booking ID:</b> {self.name}</p>
            <p>We look forward to seeing you!</p>
            <p>Thanks,<br>Event Team</p>
        """

        frappe.sendmail(recipients=recipients, subject=subject, message=message)

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
# Module-level function for scheduled reminders
# ----------------------------
def send_reminders():
    """Send reminders for all submitted bookings"""
    bookings = frappe.get_all("Festa Booking", filters={"docstatus": 1}, pluck="name")
    for name in bookings:
        booking = frappe.get_doc("Festa Booking", name)
        booking.send_reminder()
