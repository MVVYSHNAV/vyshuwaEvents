# Copyright (c) 2025
# It enables organizers to create and publish events, define venues, 
# and set ticket categories, while attendees can browse events, book tickets, 
# and receive confirmations with secure online payments.
# Vyshnav and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import nowdate
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from frappe.types import DF
    from vyshuwaops.ticketing.doctype.festa_attende_booking.festa_attende_booking import FestaAttendeBooking


class FestaBooking(Document):
    # Auto-generated type hints
    if TYPE_CHECKING:
        amended_from: "DF.Link | None"
        attendes: "DF.Table[FestaAttendeBooking]"
        currency: "DF.Link | None"
        event: "DF.Link"
        total_amount: "DF.Currency"
        user: "DF.Link"
        sales_order: "DF.Link | None"   # <-- Add custom Link field to Sales Order

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
        """On submit: create tickets and sales order"""
        self.generate_tickets()
        if not self.get("sales_order"):
            self.create_sales_order()

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

    def create_sales_order(self):
        """Create Sales Order linked to this booking (only once, on submit)"""
        if not self.attendes:
            frappe.throw("No attendees found to create Sales Order.")

        # Get or create Customer
        customer_name = frappe.db.get_value("Customer", {"customer_name": self.full_name}, "name")
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
            # Map attendee ticket_type to Item
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

    # def on_payment_authorized(self, payment_status: str):
    #     """Handle payment gateway callback"""
    #     if payment_status in ("Authorized", "Completed") and self.sales_order:
    #         so_doc = frappe.get_doc("Sales Order", self.sales_order)
    #         if so_doc.docstatus == 0:
    #             so_doc.submit()
