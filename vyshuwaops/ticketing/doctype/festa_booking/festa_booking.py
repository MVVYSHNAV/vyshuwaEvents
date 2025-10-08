import io
import base64
import qrcode

import frappe
from frappe.model.document import Document
from frappe.utils import nowdate, get_url

from vyshuwaops.api.api import create_invoice_and_payment


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
        payment_status: DF.Literal["Paid", "Failed", "Pending"]
        qr_code_url: DF.AttachImage | None
        sales_order: DF.Link | None
        total_amount: DF.Currency
        user: DF.Link
    # end: auto-generated types

    # ----------------------------
    # Hooks
    # ----------------------------

    def before_insert(self):
        """Automatically set the booking user to the logged-in session user"""
        if not self.user:
            self.user = frappe.session.user

    def validate(self):
        self.set_total()
        self.set_currency()

    def set_currency(self):
        if getattr(self, "attendes", None) and len(self.attendes) > 0:
            first_attendee = self.attendes[0]
            if hasattr(first_attendee, "currency") and first_attendee.currency:
                self.currency = first_attendee.currency
                return
        self.currency = frappe.db.get_default("currency")

    def set_total(self):
        total = 0.0
        if not getattr(self, "attendes", None):
            self.total_amount = 0.0
            return

        for attende in self.attendes:
            try:
                price = float(getattr(attende, "price", 0) or 0)
                total += price
            except Exception:
                frappe.throw(f"Invalid price for attendee {getattr(attende, 'full_name', 'Unknown')}")
        self.total_amount = total

    # ----------------------------
    # Submission
    # ----------------------------

    def on_submit(self):
        """Main workflow on booking submission"""

        # Create Sales Order if not existing
        if not hasattr(self, 'sales_order') or not self.sales_order:
            self.create_sales_order()

        # Generate tickets immediately
        self.generate_tickets()

        # Generate QR code + send emails immediately
        self.generate_qr_code()
        self.send_booking_emails()

        # Attempt to create invoice and payment
        try:
            create_invoice_and_payment(self.name)
        except Exception as e:
            frappe.log_error(frappe.get_traceback(), "FestaBooking Invoice/Payment Creation Error")
            frappe.msgprint(f"⚠️ Invoice/Payment creation failed: {str(e)}")
            
    def after_insert(self):
        """
        Automatically submit the document immediately after it's created 
        by the Web Form (since docstatus is 0 after insert).
        """
        if self.docstatus == 0:
            try:
                # Submitting the document triggers the on_submit hook
                self.submit()
                frappe.logger().info(f"Festa Booking {self.name} auto-submitted after Web Form insert.")
            except Exception:
                # Log any submission errors but allow the insert to complete
                frappe.log_error(frappe.get_traceback(),f"Festa Booking auto-submit failed after insert for {self.name}")
 

    # ----------------------------
    # Ticket generation
    # ----------------------------

    def generate_tickets(self):
        if not getattr(self, "attendes", None):
            return

        for attende in self.attendes:
            attende_name = getattr(attende, "full_name", None) or getattr(attende, "email", None) or "Unknown"
            exists = frappe.db.exists(
                "Festa Ticket",
                {"event": self.event, "booking": self.name, "attende_name": attende_name}
            )
            if exists:
                continue

            ticket = frappe.new_doc("Festa Ticket")
            ticket.event = self.event
            ticket.booking = self.name
            ticket.ticket_type = getattr(attende, "ticket_type", None)
            ticket.attende_name = attende_name
            ticket.insert(ignore_permissions=True)
            ticket.submit()

    # ----------------------------
    # QR code generation
    # ----------------------------

    def generate_qr_code(self):
        attendee_details = "\n".join([
            f"{getattr(a, 'full_name', '')} ({getattr(a, 'ticket_type', '')}, {getattr(a, 'email', '')})"
            for a in (self.attendes or [])
        ])
        qr_data = (
            f"Booking ID: {self.name}\n"
            f"Event: {self.event}\n"
            f"Booking User: {self.user}\n"
            f"Total Amount: {getattr(self, 'total_amount', 0.0)} {getattr(self, 'currency', '')}\n"
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
        qr_bytes = output.getvalue()
        self._qr_bytes = qr_bytes

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

    # ----------------------------
    # Email sending
    # ----------------------------

    def send_booking_emails(self):
        recipients = []

        booking_email = self.user
        if booking_email and "@" not in booking_email:
            booking_email = frappe.db.get_value("User", self.user, "email")

        if booking_email:
            recipients.append(booking_email)
            self._send_email(
                recipient=booking_email,
                subject=f"Booking Confirmation - {self.event}",
                message=f"""
                    <div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #333; line-height: 1.6; max-width: 600px; margin: auto; border: 1px solid #e0e0e0; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
                        <div style="background-color: #2E86C1; color: #fff; padding: 20px; text-align: center;">
                            <h1 style="margin: 0; font-size: 24px;">Booking Confirmed</h1>
                        </div>
                        <div style="padding: 20px;">
                            <p style="font-size: 16px;">Hi <strong>{self.user}</strong>,</p>
                            <p style="font-size: 16px;">Your booking for <strong>{self.event}</strong> is confirmed. Here are your details:</p>
                            <div style="background: #f9f9f9; padding: 15px; border-radius: 8px; margin: 20px 0;">
                                <p><strong>Booking ID:</strong> {self.name}</p>
                                <p><strong>Total Amount:</strong> {self.total_amount} {self.currency}</p>
                            </div>
                            <p style="font-size: 16px;">Please keep this QR code safe. You will need it to enter the event.</p>
                            <p style="margin-top: 30px; font-size: 16px;">Thanks,<br><strong>Event Team</strong></p>
                        </div>
                        <div style="background-color: #f0f0f0; color: #555; text-align: center; padding: 15px; font-size: 12px;">
                            <p style="margin: 0;">This is an automated email. Please do not reply.</p>
                        </div>
                    </div>
                """,
                attachments=[{
                    "fname": f"Booking_{self.name}_QR.png",
                    "fcontent": self._qr_bytes
                }]
            )

        # Send to each attendee
        for attende in (self.attendes or []):
            attende_email = getattr(attende, "email", None)
            if attende_email and attende_email not in recipients:
                recipients.append(attende_email)
                self._send_email(
                    recipient=attende_email,
                    subject=f"Your Ticket for {self.event}",
                    message=f"""
                        <div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #333; line-height: 1.6; max-width: 600px; margin: auto; border: 1px solid #e0e0e0; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
                            <div style="background-color: #4CAF50; color: #fff; padding: 20px; text-align: center;">
                                <h1 style="margin: 0; font-size: 24px;">Your Ticket for {self.event}</h1>
                            </div>
                            <div style="padding: 20px;">
                                <p style="font-size: 16px;">Hi <strong>{attende.full_name}</strong>,</p>
                                <p style="font-size: 16px;">You are officially registered as an attendee for <b>{self.event}</b>.</p>
                                <div style="background: #f9f9f9; padding: 15px; border-radius: 8px; margin: 20px 0; text-align: center;">
                                    <p><strong>Ticket Type:</strong> {attende.ticket_type}</p>
                                    <p><strong>Booking ID:</strong> {self.name}</p>
                                </div>
                                <p style="font-size: 16px;">Please keep this email safe. The QR code above will serve as your ticket at the event entrance.</p>
                                <p style="margin-top: 30px; font-size: 16px;">Best regards,<br><strong>Event Team</strong></p>
                            </div>
                            <div style="background-color: #f0f0f0; color: #555; text-align: center; padding: 15px; font-size: 12px;">
                                <p style="margin: 0;">This is an automated email. Please do not reply.</p>
                            </div>
                        </div>
                    """,
                    attachments=[{
                        "fname": f"Booking_{self.name}_QR.png",
                        "fcontent": self._qr_bytes
                    }]
                )

    def _send_email(self, recipient, subject, message, attachments=None):
        frappe.sendmail(
            recipients=[recipient],
            subject=subject,
            message=message,
            attachments=attachments or [],
            reference_doctype=self.doctype,
            reference_name=self.name
        )

    # ----------------------------
    # Sales Order creation
    # ----------------------------

    def create_sales_order(self):
        if not getattr(self, "attendes", None) or len(self.attendes) == 0:
            frappe.throw("No attendees found to create Sales Order.")

        user_email = None
        if self.user:
            user_email = frappe.db.get_value("User", self.user, "email")

        customer_name = None
        if user_email:
            customer_name = frappe.db.get_value("Customer", {"email_id": user_email}, "name")

        if not customer_name:
            customer = frappe.new_doc("Customer")
            customer.customer_name = (self.user or "Guest").replace("@", "_")
            if user_email:
                customer.email_id = user_email
            customer.customer_type = "Individual"
            customer.insert(ignore_permissions=True)
            customer_name = customer.name

        so = frappe.new_doc("Sales Order")
        so.customer = customer_name
        so.transaction_date = nowdate()
        so.company = frappe.db.get_default("Company")
        so.currency = self.currency or frappe.db.get_default("currency")

        for attende in self.attendes:
            ticket_type = getattr(attende, "ticket_type", "")
            item_code = frappe.get_value("Festa Ticket Type", ticket_type, "item_code")
            if not item_code or not frappe.db.exists("Item", item_code):
                frappe.throw(f"Item Code '{item_code}' does not exist for attendee {getattr(attende, 'full_name', '')}")

            so.append("items", {
                "item_code": item_code,
                "item_name": f"Ticket - {ticket_type}",
                "description": f"Ticket for {getattr(attende, 'full_name', '')} ({getattr(attende, 'email', '')})",
                "qty": 1,
                "rate": float(getattr(attende, "price", 0) or 0),
                "delivery_date": nowdate(),
            })

        so.insert(ignore_permissions=True)
        so.submit()

        self.sales_order = so.name
        self.db_set("sales_order", so.name)
        frappe.msgprint(f"Sales Order {so.name} created for Booking {self.name}")
