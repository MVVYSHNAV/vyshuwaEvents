# Copyright (c) 2025, It enables organizers to create and publish events, define venues, and set ticket categories, while attendees can browse events, book tickets, and receive confirmations with secure online payments.vyshnav and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class FestaPayment(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amount: DF.Data | None
		booking: DF.Link | None
		customer_name: DF.Data | None
		name: DF.Int | None
		payment_status: DF.Literal["Draft", "Paid"]
		razorpay_order_id: DF.Data | None
		razorpay_payment_id: DF.Data | None
		razorpay_signature: DF.Data | None
	# end: auto-generated types
	pass
