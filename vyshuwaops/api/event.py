import frappe

@frappe.whitelist(allow_guest=True)
def get_published_events():
    """
    Fetch all published Festa Events
    """
    events = frappe.get_all(
        "Festa Event",
        filters={"is_published": 1},
        fields=[
            "name",
            "title",
            "description",
            "cover_image",
            "host",
            "venue",
            "start_date",
            "time",
            "end_date",
            "end_time",
            "status",
            "route"
        ],
        order_by="start_date asc"
    )
    return events
