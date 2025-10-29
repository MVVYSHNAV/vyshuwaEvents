import frappe

def get_context(context):
    # Optional: get payment details from query params
    payment_id = frappe.form_dict.get("payment_id")
    
    if payment_id:
        payment_doc = frappe.get_doc("Payment Entry", payment_id)
        context.payment_status = payment_doc.status
        context.amount = payment_doc.paid_amount
        context.customer = payment_doc.party_name
    else:
        context.payment_status = "Completed"
        context.amount = None
        context.customer = None
