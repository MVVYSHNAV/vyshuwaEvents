# Copyright (c) 2025, It enables organizers to create and publish events, define venues, and set ticket categories, while attendees can browse events, book tickets, and receive confirmations with secure online payments.vyshnav and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


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
		schedule: DF.Table[FestaSheduleItem]
		start_date: DF.Date
		status: DF.Literal["Draft", "Scheduled", "Cancelled"]
		time: DF.Time
		title: DF.Data
		venue: DF.Link
	# end: auto-generated types

	@frappe.whitelist
	def check_in(self, ticket_id):
		frappe.get_doc({
			"doctype": "Festa Check In",
			"ticket" : ticket_id,
		}).insert().submit()
