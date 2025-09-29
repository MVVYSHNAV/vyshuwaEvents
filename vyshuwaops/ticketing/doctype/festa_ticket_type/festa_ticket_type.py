# Copyright (c) 2025, It enables organizers to create and publish events, define venues, and set ticket categories, while attendees can browse events, book tickets, and receive confirmations with secure online payments.vyshnav and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class FestaTicketType(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		currency: DF.Link | None
		event: DF.Link | None
		item_code: DF.Data | None
		item_name: DF.Link
		name: DF.Int | None
		price: DF.Data
	# end: auto-generated types
	pass
