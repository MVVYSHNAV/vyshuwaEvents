# Copyright (c) 2025, Vyshnav and contributors
# For license information, please see license.txt

import frappe
from frappe.website.website_generator import WebsiteGenerator
from frappe.model.document import Document
from frappe.utils import flt, now_datetime

class FestaEvent(WebsiteGenerator):
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
		organizer: DF.Link | None  # Add this field - Link to User
		is_published: DF.Check
		payment_gateway: DF.Link | None
		route: DF.Data | None
		schedule: DF.Table[FestaSheduleItem]
		start_date: DF.Date
		status: DF.Literal["Draft", "Scheduled", "Cancelled", "Booked"]
		time: DF.Time
		title: DF.Data
		venue: DF.Link
	# end: auto-generated types
	
	website = frappe._dict({
		"condition_field": "is_published",
		"page_title_field": "title"
	})
	
	def before_save(self):
		"""Set organizer to current user if creating new event"""
		if self.is_new() and not self.organizer:
			self.organizer = frappe.session.user
	
	def validate(self):
		"""Validate event data"""
		if self.end_date and self.start_date:
			if self.end_date < self.start_date:
				frappe.throw("End date cannot be before start date")
	
	def has_permission(self, ptype, user=None):
		"""Custom permission logic for events"""
		if not user:
			user = frappe.session.user
		
		# Admin/System Manager has full access
		if "Admin" in frappe.get_roles(user) or "System Manager" in frappe.get_roles(user):
			return True
		
		# Organizers can only access their own events
		if "Organizer" in frappe.get_roles(user):
			if ptype in ["read", "write", "delete"]:
				return self.organizer == user
			if ptype == "create":
				return True
		
		# Attendees can only read published events
		if "Attendee" in frappe.get_roles(user):
			if ptype == "read":
				return self.is_published == 1
			return False
		
		return False
	
	def get_context(self, context):
		"""Set context for web view"""
		context.no_cache = 1
		context.show_sidebar = True
		
		# Get tickets for this event
		context.tickets = frappe.get_all(
			"Festa Ticket Type",
			filters={"event": self.name},
			fields=["name", "ticket_name", "price", "quantity_available", "quantity_sold"]
		)
		
		return context
	
	@frappe.whitelist()
	def create_payment_request(self, ticket_type=None, quantity=1):
		"""Create payment request for ticket booking"""
		if not self.is_published:
			frappe.throw("Cannot create payment for unpublished event")
		
		if not ticket_type:
			frappe.throw("Please select a ticket type")
		
		# Get ticket details
		ticket = frappe.get_doc("Festa Ticket Type", ticket_type)
		
		if not ticket.price:
			frappe.throw("Ticket price not set")
		
		# Check availability
		available = ticket.quantity_available - ticket.quantity_sold
		if available < int(quantity):
			frappe.throw(f"Only {available} tickets available")
		
		# Create booking first
		booking = frappe.get_doc({
			"doctype": "Festa Booking",
			"event": self.name,
			"ticket_type": ticket_type,
			"attendee": frappe.session.user,
			"quantity": quantity,
			"total_amount": flt(ticket.price) * int(quantity),
			"booking_status": "Pending",
			"payment_status": "Pending"
		})
		booking.insert(ignore_permissions=True)
		
		# Create payment request
		payment_request = frappe.get_doc({
			"doctype": "Payment Request",
			"party_type": "Customer",
			"party": frappe.session.user,
			"amount": flt(ticket.price) * int(quantity),
			"reference_doctype": "Festa Booking",
			"reference_name": booking.name,
			"mode_of_payment": "Online",
			"payment_gateway": self.payment_gateway or "Razorpay"
		})
		
		payment_request.insert(ignore_permissions=True)
		payment_request.submit()
		
		return {
			"payment_request": payment_request.name,
			"booking": booking.name
		}
	
	@frappe.whitelist()
	def check_in(self, ticket_id):
		"""Check in attendee with ticket"""
		# Verify ticket belongs to this event
		ticket = frappe.get_doc("Festa Booking", ticket_id)
		
		if ticket.event != self.name:
			frappe.throw("Invalid ticket for this event")
		
		if ticket.payment_status != "Paid":
			frappe.throw("Ticket payment not confirmed")
		
		# Check if already checked in
		existing = frappe.db.exists("Festa Check In", {"ticket": ticket_id})
		if existing:
			frappe.throw("Already checked in")
		
		# Create check-in record
		check_in = frappe.get_doc({
			"doctype": "Festa Check In",
			"ticket": ticket_id,
			"event": self.name,
			"attendee": ticket.attendee,
			"check_in_time": now_datetime()
		})
		check_in.insert(ignore_permissions=True)
		check_in.submit()
		
		frappe.msgprint(f"Successfully checked in!")
		return check_in.name


@frappe.whitelist()
def payment_request_paid(doc, method):
	"""Hook to handle payment completion"""
	if doc.reference_doctype == "Festa Booking" and doc.reference_name:
		try:
			booking = frappe.get_doc("Festa Booking", doc.reference_name)
			booking.db_set("payment_status", "Paid")
			booking.db_set("booking_status", "Confirmed")
			
			# Update ticket quantity
			ticket = frappe.get_doc("Festa Ticket Type", booking.ticket_type)
			ticket.db_set("quantity_sold", ticket.quantity_sold + booking.quantity)
			
			# Send confirmation email
			booking.send_confirmation_email()
			
			frappe.msgprint(f"Booking '{booking.name}' confirmed after payment.")
		except Exception as e:
			frappe.log_error(f"Error updating Festa Booking after payment: {str(e)}")


def get_permission_query_conditions(user):
	"""Query permission filter for list view"""
	if not user:
		user = frappe.session.user
	
	# Admin/System Manager sees everything
	if "Admin" in frappe.get_roles(user) or "System Manager" in frappe.get_roles(user):
		return None
	
	# Organizers see only their events
	if "Organizer" in frappe.get_roles(user):
		return f"""(`tabFesta Event`.organizer = {frappe.db.escape(user)})"""
	
	# Attendees see only published events
	if "Attendee" in frappe.get_roles(user):
		return """(`tabFesta Event`.is_published = 1)"""
	
	# No access for other roles
	return """(1=0)"""


def has_permission(doc, ptype, user):
	"""Document-level permission check"""
	if not user:
		user = frappe.session.user
	
	# Admin/System Manager has full access
	if "Admin" in frappe.get_roles(user) or "System Manager" in frappe.get_roles(user):
		return True
	
	# Organizers can only access their own events
	if "Organizer" in frappe.get_roles(user):
		if ptype in ["read", "write", "delete"]:
			return doc.organizer == user
		if ptype == "create":
			return True
	
	# Attendees can only read published events
	if "Attendee" in frappe.get_roles(user):
		if ptype == "read":
			return doc.is_published == 1
		return False
	
	return False