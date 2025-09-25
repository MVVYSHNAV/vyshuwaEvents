# Copyright (c) 2025,
# It enables organizers to create and publish events, define venues, and set ticket categories,
# while attendees can browse events, book tickets, and receive confirmations with secure online payments.
# Vyshnav and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import io
import qrcode
import random
import string

class FestaTicket(Document):
    def before_insert(self):
        self.generate_qr_code()

    def generate_qr_code(self):
        # Generate a random ticket ID based on the event name.
        # This creates a more unique and identifiable ticket ID than the document's default name.
        event_name = "".join(e for e in self.event if e.isalnum())
        random_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        self.ticket_id = f"{event_name}-{random_id}"

        # Place the attendee's name on its own line at the top to give it prominence.
        qr_string = (
            f"Attendee: {self.attende_name or ''}\n"
            f"Ticket ID: {self.ticket_id or ''}\n"
            f"Event: {self.event or ''}\n"
            f"Type: {self.ticket_type or ''}\n"
            f"Issued On: {frappe.utils.now()}"
        )

        # Use the QRCode class for more control over style and color.
        # This allows for a more "modern" look by specifying box size and border.
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,  # A slightly larger size for a clearer look
            border=4,
        )

        # Add the data to the QR code
        qr.add_data(qr_string)
        qr.make(fit=True)

        # Generate the QR image with custom colors.
        # A dark blue (#1A4F8F) is used for the fill color.
        img = qr.make_image(
            fill_color="#1A4F8F",
            back_color="white"
        )

        # Save the image to a BytesIO object
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
