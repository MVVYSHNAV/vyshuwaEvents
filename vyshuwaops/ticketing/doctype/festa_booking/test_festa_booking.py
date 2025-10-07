# Copyright (c) 2025, It enables organizers to create and publish events, define venues, and set ticket categories, while attendees can browse events, book tickets, and receive confirmations with secure online payments.vyshnav and Contributors
# See license.txt

# import frappe
from frappe.tests.utils import FrappeTestCase




class TestFestaBooking(FrappeTestCase):
	def test_booking_submission_creates_payment_entry(self):
		import frappe
		# Ensure linked Festa Event exists
		if not frappe.db.exists("Festa Event", "Test Event"):
			frappe.get_doc({"doctype": "Festa Event", "title": "Test Event"}).insert(ignore_permissions=True)
		# Ensure linked User exists
		if not frappe.db.exists("User", "testuser@example.com"):
			frappe.get_doc({"doctype": "User", "email": "testuser@example.com", "first_name": "Test"}).insert(ignore_permissions=True)

		booking = frappe.get_doc({
			"doctype": "Festa Booking",
			"event": "Test Event",
			"user": "testuser@example.com",
			"total_amount": 1000,
			"currency": "INR",
		})
		booking.insert(ignore_permissions=True)
		booking.submit()

		# Check if booking is submitted
		self.assertEqual(booking.docstatus, 1)
