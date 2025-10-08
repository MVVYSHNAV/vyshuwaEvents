//  frappe.ready(() => {
//             const urlParams = new URLSearchParams(window.location.search);
//             const eventName = urlParams.get("event");

//             // Prefill event field if provided
//             if (eventName) {
//                 $("input[name='event']").val(eventName);
//             }

//             // Prefill user if logged in
//             frappe.call({
//                 method: "frappe.client.get_value",
//                 args: {
//                     doctype: "User",
//                     filters: { name: frappe.session.user },
//                     fieldname: ["name", "email", "full_name"]
//                 },
//                 callback: function(r) {
//                     if (r.message) {
//                         $("input[name='user']").val(r.message.name);
//                     }
//                 }
//             });

//             // Add attendee row
//             function addAttendeeRow(name = '', email = '', price = 0) {
//                 const row = `<tr>
//                     <td><input type="text" name="attendee_name[]" value="${name}" required></td>
//                     <td><input type="email" name="attendee_email[]" value="${email}" required></td>
//                     <td><input type="number" name="attendee_price[]" value="${price}" required></td>
//                     <td><button type="button" class="remove-btn">Remove</button></td>
//                 </tr>`;
//                 $("#attendees-table tbody").append(row);
//                 updateTotalAmount();
//             }

//             // Remove attendee row
//             $("#attendees-table").on("click", ".remove-btn", function() {
//                 $(this).closest("tr").remove();
//                 updateTotalAmount();
//             });

//             // Update total amount
//             function updateTotalAmount() {
//                 let total = 0;
//                 $("input[name='attendee_price[]']").each(function() {
//                     total += parseFloat($(this).val()) || 0;
//                 });
//                 $("input[name='total_amount']").val(total);
//             }

//             // Recalculate total on price change
//             $("#attendees-table").on("input", "input[name='attendee_price[]']", updateTotalAmount);

//             // Add attendee button click
//             $("#add-attendee-btn").on("click", () => addAttendeeRow());

//             // Handle form submission
//             $("#attende-book-ticket-form").on("submit", function(e) {
//                 e.preventDefault();

//                 // Collect form data
//                 let formData = {
//                     event: $("input[name='event']").val(),
//                     user: $("input[name='user']").val(),
//                     currency: $("select[name='currency']").val(),
//                     total_amount: $("input[name='total_amount']").val(),
//                     attendes: []
//                 };

//                 $("#attendees-table tbody tr").each(function() {
//                     const name = $(this).find("input[name='attendee_name[]']").val();
//                     const email = $(this).find("input[name='attendee_email[]']").val();
//                     const price = $(this).find("input[name='attendee_price[]']").val();
//                     formData.attendes.push({ name: name, email: email, price: price });
//                 });

//                 // Submit via Frappe Web Form
//                 frappe.call({
//                     method: "frappe.www.web_form.submit",
//                     args: {
//                         web_form_name: "attende_book_ticket",
//                         data: formData
//                     },
//                     callback: function(r) {
//                         if (!r.exc) {
//                             $("#message").css("color", "green").text("Booking successful!");
//                             $("#attende-book-ticket-form")[0].reset();
//                             $("#attendees-table tbody").empty();
//                             updateTotalAmount();
//                         } else {
//                             $("#message").css("color", "red").text("Error: " + r.exc);
//                         }
//                     },
//                     error: function(err) {
//                         $("#message").css("color", "red").text("Server error. Please try again later.");
//                     }
//                 });
//             });
//         });