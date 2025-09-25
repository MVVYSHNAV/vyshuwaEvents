// Copyright (c) 2025,
// Enables organizers to create and publish events, define venues, and set ticket categories,
// while attendees can browse events, book tickets, and receive confirmations with secure online payments.
// Vyshnav and contributors

frappe.ui.form.on("Festa Event", {
    refresh(frm) {
        // Hide buttons if status is Cancelled
        if (frm.doc.status === "Cancelled") return;

        // Determine current publish state
        const is_published = frm.doc.status === "Scheduled";
        const button_label = is_published ? __("Unpublish") : __("Publish");

        // Add Publish/Unpublish button
        frm.add_custom_button(button_label, () => {
            frm.set_value("status", is_published ? "Draft" : "Scheduled");
            frm.set_value("is_published", !is_published);
            frm.save();
        });

        // Add Cancel button
        frm.add_custom_button(__("Cancel"), () => {
            frappe.confirm(
                __("Are you sure you want to cancel this event?"),
                () => {
                    frm.set_value("status", "Cancelled");
                    frm.set_value("is_published", 0);
                    frm.save();
                }
            );
        }, __("Action")).addClass("btn-danger");

        // Add Start Check In button only if the event is scheduled
        if (frm.doc.status === "Scheduled") {
            frm.add_custom_button(__("Start Check In"), () => {
                new frappe.ui.Scanner({
                    dialog: true, 
                    multiple: false,
                    on_scan(data) {
                        const ticket_id = data.decodedText;
                        frm.call("check_in", { ticket_id }).then(() => {
                            frappe.show_alert(__("Checked in successfully"));
                            frm.refresh();
                        }).catch((err) => {
                            frappe.msgprint(__("Error during check-in: ") + err.message);
                        });
                    }
                });
            }, __("Action")).addClass("btn-info");
        }
    },
});
