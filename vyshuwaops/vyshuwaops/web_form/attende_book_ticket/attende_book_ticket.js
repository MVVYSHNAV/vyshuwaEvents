frappe.ready(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const eventName = urlParams.get("event");

    // Prefill event field if provided
    if (eventName) {
        $("input[name='event']").val(eventName);
    }

    // Prefill user if logged in
    frappe.call({
        method: "frappe.client.get_value",
        args: {
            doctype: "User",
            filters: { name: frappe.session.user },
            fieldname: ["name", "email", "full_name"]
        },
        callback: function(r) {
            if (r.message) {
                $("input[name='user']").val(r.message.name);
            }
        }
    });

    // Handle form submission
    $("#attende-book-ticket-form").on("submit", function(e) {
        e.preventDefault();

        let formData = {};
        $(this).serializeArray().forEach(field => {
            formData[field.name] = field.value;
        });

        frappe.call({
            method: "frappe.www.web_form.submit",
            args: {
                web_form_name: "attende_book_ticket",
                data: formData
            },
            callback: function(r) {
                if (!r.exc) {
                    $("#message").css("color", "green").text("Booking successful!");
                    $("#attende-book-ticket-form")[0].reset();
                } else {
                    $("#message").css("color", "red").text("Error: " + r.exc);
                }
            },
            error: function(err) {
                $("#message").css("color", "red").text("Server error. Please try again later.");
            }
        });
    });
});
