function make_payment(booking) {
    var options = {
        "name": "Festa Booking",                   // Modal title
        "description": "Pay for your ticket",      // Modal description
        "image": "/assets/images/logo.png",       // Optional logo
        "prefill": {
            "name": booking.user,
            "email": booking.user_email,
            "contact": booking.user_phone
        },
        "theme": {
            "color": "#3399cc"
        },
        "doctype": "Festa Booking",                // Mandatory
        "docname": booking.name                     // Mandatory
    };

    var razorpay = new frappe.checkout.razorpay(options);

    razorpay.on_open = () => {
        console.log("Razorpay modal opened");
    }

    razorpay.on_success = (response) => {
        console.log("Payment Success:", response);
        frappe.msgprint("Payment successful!");
        // Optional: call backend to verify payment
    }

    razorpay.on_fail = (response) => {
        console.log("Payment Failed:", response);
        frappe.msgprint("Payment failed. Please try again.");
    }

    razorpay.init(); // Creates order and opens modal
}
