frappe.web_form.after_load = () => {
  const params = new URLSearchParams(window.location.search);
  if (params.has('event')) {
    frappe.web_form.set_value('event', params.get('event'));
  }
  if (params.has('ticket')) {
    frappe.web_form.set_value('ticket_type', params.get('ticket'));
  }
  if (params.has('price')) {
    frappe.web_form.set_value('price', params.get('price'));
  }
};
