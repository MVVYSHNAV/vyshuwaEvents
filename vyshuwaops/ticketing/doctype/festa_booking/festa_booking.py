# Copyright (c) 2025, It enables organizers to create and publish events, define venues, and set ticket categories, while attendees can browse events, book tickets, and receive confirmations with secure online payments.vyshnav and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class FestaBooking(Document):
	def validate(self):
		self.set_total()
		self.set_currency()

	def set_currency(self):
		self.set_currency = self.attendes[0].currency
		
	def set_total(self):
		self.total_amount = 0
		for attende in self.attendes:
			self.total_amount += attende.price

	def on_submit(self):
		self.generate_ticket()

	def generate_ticket(self):
		for attende in self.attendes:
			ticket = frappe.new_doc("Festa Ticket")
			ticket.event = self.event
			ticket.booking = self.name
			ticket.ticket_type = attende.ticket_type
			ticket.attende_name = attende.full_name
			ticket.insert().submit()

	