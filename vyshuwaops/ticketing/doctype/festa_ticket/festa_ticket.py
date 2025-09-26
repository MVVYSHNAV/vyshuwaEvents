# Copyright (c) 2025,
# It enables organizers to create and publish events, define venues, and set ticket categories,
# while attendees can browse events, book tickets, and receive confirmations with secure online payments.
# Vyshnav and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class FestaTicket(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        amended_from: DF.Link | None
        attende_name: DF.Data
        booking: DF.Link | None
        event: DF.Link
        price: DF.Data | None
        qr_code: DF.AttachImage | None
        ticket_id: DF.Data | None
        ticket_type: DF.Link
        venue: DF.Data | None
    # end: auto-generated types
    def before_insert(self):
        self.generate_qr_code()

    def generate_qr_code(self):
        import io
        import qrcode
        import json

        # Prepare QR data
        qr_data = {
            "attendee_name": self.attende_name or "",
            "ticket_id": self.name or "",
            "event": self.event or "",
            "ticket_type": self.ticket_type or "",
            "issued_on": frappe.utils.now()
        }

        # Convert to JSON
        qr_string = json.dumps(qr_data)

        # Generate QR image
        img = qrcode.make(qr_string)
        output = io.BytesIO()
        img.save(output, format="PNG")
        hex_data = output.getvalue()

        # Save QR code file
        qr_Code_file = frappe.get_doc({
            "doctype": "File",
            "file_name": f"ticket-qr-code-{self.attende_name}.png",
            "content": hex_data,
            "attached_to_doctype": "Festa Ticket",
            "attached_to_name": self.attende_name,
            "attached_to_field": "qr_code"
        }).save()

        # Save file URL to the ticket
        self.qr_code = qr_Code_file.file_url
