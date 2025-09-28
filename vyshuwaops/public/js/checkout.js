function payBooking(booking_name) {
    frappe.call({
        method: "vyshuwaops.ticketing.doctype.festa_booking.festa_booking.FestaBooking.create_payment",
        args: { "name": booking_name },
        callback: function(res) {
            if (res.message) {
                var options = {
                    doctype: "Festa Booking",
                    docname: booking_name,
                    razorpay_order_id: res.message.id,
                    name: "Event Booking",
                    description: "Pay for your tickets"
                };
                var rzp = new frappe.checkout.razorpay(options);

                rzp.on_success = function(response) {
                    frappe.call({
                        method: "vyshuwaops.ticketing.doctype.festa_booking.festa_booking.FestaBooking.verify_payment",
                        args: {
                            payment_id: response.razorpay_payment_id,
                            order_id: response.razorpay_order_id,
                            signature: response.razorpay_signature,
                            name: booking_name
                        }
                    });
                };

                rzp.on_fail = function(response) {
                    frappe.msgprint("Payment Failed. Try again.");
                };

                rzp.init();
            }
        }
    });
}
