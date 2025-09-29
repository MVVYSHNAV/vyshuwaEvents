// Copyright (c) 2025, It enables organizers to create and publish events, define venues, and set ticket categories, while attendees can browse events, book tickets, and receive confirmations with secure online payments.vyshnav and contributors
// For license information, please see license.txt

frappe.ui.form.on('Festa Booking', {
    refresh: function (frm) {
        if (frm.doc.docstatus === 1 && frm.doc.payment_status !== "Paid") {
            frm.add_custom_button(__('Make Payment'), function () {
                frappe.call({
                    method: 'vyshuwaops.api.api.create_payment',
                    args: {
                        docname: frm.doc.name
                    },
                    callback: function (r) {
                        if (!r.exc && r.message) {
                            frappe.msgprint("Payment Order Created: " + r.message.id);
                            // You can trigger Razorpay popup here if needed
                        }
                    }
                });
            }, __('Actions'));
        }
    }
});
