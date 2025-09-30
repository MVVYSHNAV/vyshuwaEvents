# Copyright (c) 2025, It enables organizers to create and publish events, define venues, and set ticket categories, while attendees can browse events, book tickets, and receive confirmations with secure online payments.vyshnav and contributors
# For license information, please see license.txt

import frappe
from frappe.website.website_generator import WebsiteGenerator
from frappe.model.document import Document
from frappe.utils import flt

class WebsiteSettings:
    # The field that determines whether the event is shown on the website
    condition_field = "is_published"
class FestaEvent(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from vyshuwaops.vyshuwaops.doctype.festa_shedule_item.festa_shedule_item import FestaSheduleItem

		categories: DF.Link
		cover_image: DF.AttachImage | None
		description: DF.SmallText
		end_date: DF.Date | None
		end_time: DF.Time | None
		host: DF.Link | None
		is_published: DF.Check
		payment_gateway: DF.Link | None
		route: DF.Data | None
		schedule: DF.Table[FestaSheduleItem]
		start_date: DF.Date
		status: DF.Literal["Draft", "Scheduled", "Cancelled"]
		time: DF.Time
		title: DF.Data
		venue: DF.Link
	# end: auto-generated types
	
 
	website = WebsiteSettings()
 
	
	@frappe.whitelist()
	def create_payment_request(docname):
		event = frappe.get_doc("Festa Event", docname)

		if not event.is_published:
			frappe.throw("Cannot create payment for unpublished event")

		if not hasattr(event, "ticket_price") or not event.ticket_price:
			frappe.throw("Ticket price not set for this event")

		payment_request = frappe.get_doc({
			"doctype": "Payment Request",
			"party_type": "Customer",
			"party": event.customer_email or "",
			"amount": flt(event.ticket_price),
			"reference_doctype": "Festa Event",
			"reference_name": event.name,
			"mode_of_payment": "Online"
		})

		payment_request.insert()
		payment_request.submit()

		return payment_request.name

	def payment_request_paid(doc, method):
		if doc.reference_doctype == "Festa Event" and doc.reference_name:
			try:
				event = frappe.get_doc("Festa Event", doc.reference_name)
				event.db_set("status", "Booked")
				event.db_set("is_published", 0)
				frappe.msgprint(f"Event '{event.name}' marked as Booked after payment.")
			except Exception as e:
				frappe.log_error(f"Error updating Festa Event after payment: {str(e)}")


	@frappe.whitelist
	def check_in(self, ticket_id):
		frappe.get_doc({
			"doctype": "Festa Check In",
			"ticket" : ticket_id,
		}).insert().submit()
