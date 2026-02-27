from flask import Flask, render_template, request, jsonify, send_from_directory
import os
from datetime import datetime, timedelta
import random
from reportlab.lib import colors
from reportlab.lib.pagesizes import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

app = Flask(__name__)

# Set a temporary directory to save PDFs. In production, use a more secure location.
UPLOAD_FOLDER = 'invoices'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


def generate_hsn():
    return f"996311"

@app.route("/generate", methods=["POST"])
def generate_invoice():

    transactions = []

    date = request.form.getlist("date[]")
    descriptions = request.form.getlist("description[]")
    particulars = request.form.getlist("particular[]")
    debits = request.form.getlist("debit[]")

    balance = 0
    HSN = generate_hsn()
    for i in range(len(descriptions)):
        debit = float(debits[i]) if debits[i] else 0
        balance += debit
        
        transactions.append({
            "date": date[i],
            "room": request.form["room_no"],
            "hsn": HSN,
            "description": descriptions[i],
            "particular": particulars[i],
            "debit": debit,
            "credit": 0,
            "balance": balance
        })

    tariff = balance
    cgst = tariff * 0.025
    sgst = tariff * 0.025
    total_tax = cgst + sgst
    bill = tariff + total_tax
    paid = float(request.form.get("paid", 0))
    balance_due = bill - paid

    return render_template("pdfinvoice.html",
        hotel_name=request.form["hotel_name"],
        hotel_address=request.form["hotel_address"],
        hotel_phone=request.form["hotel_phone"],
        hotel_res_phone=request.form["hotel_res_phone"],
        hotel_gstin=request.form["hotel_gstin"],
        
        folio_no=request.form["folio_no"],
        bill_no=request.form["bill_no"],
        bill_date=datetime.strptime(request.form["checkout"], "%Y-%m-%dT%H:%M"),

        guest_name=request.form["guest_name"],
        guest_address=request.form["guest_address"],
        mobile=request.form["mobile"],
        email=request.form["email"],
        company=request.form["company"],

        room_no=request.form["room_no"],
        room_type=request.form["room_type"],
        pax=request.form["pax"],

        checkin=datetime.strptime(request.form["checkin"], "%Y-%m-%dT%H:%M"),
        checkout=datetime.strptime(request.form["checkout"], "%Y-%m-%dT%H:%M"),

        
        transactions=transactions,

        summary={
            "hsn": transactions[0]["hsn"] if transactions else "",
            "taxable": tariff,
            "cgst_amt": cgst,
            "sgst_amt": sgst,
            "total_tax": total_tax,
            "net_amount": bill
        },

        totals={
            "advance": 0,
            "tariff": tariff,
            "cgst": cgst,
            "sgst": sgst,
            "bill": bill,
            "paid": paid,
            "balance": balance_due
        }
    )

@app.route("/form", methods=["GET"])
def form():
    return render_template("new_form.html")

@app.route("/", methods=["GET"])
def menu():
    return render_template("menu.html")

@app.route("/hotel", methods=["GET", "POST"])
def index():

    if request.method == "POST":

        # HOTEL DETAILS
        hotel_name = request.form.get("hotel_name")
        hotel_address = request.form.get("hotel_address")
        hotel_phone = request.form.get("hotel_phone")
        hotel_res_phone = request.form.get("hotel_res_phone")
        hotel_gstin = request.form.get("hotel_gstin")

        # BOOKING DETAILS
        folio_no = request.form.get("folio_no")
        bill_no = request.form.get("bill_no")
        room_no = request.form.get("room_no")
        room_type = request.form.get("room_type")
        guest_name = request.form.get("guest_name")
        guest_address = request.form.get("guest_address")
        pax = request.form.get("pax")
        food_plan = request.form.get("food_plan")
        company = request.form.get("company")

        checkin = request.form.get("checkin")
        checkout = request.form.get("checkout")
        tariff = float(request.form.get("tariff"))

        # convert date-time
        checkin_dt = datetime.strptime(checkin, "%Y-%m-%dT%H:%M")
        checkout_dt = datetime.strptime(checkout, "%Y-%m-%dT%H:%M")

        # generate stay rows (one per night)
        stay_rows = []
        current = checkin_dt

        while current.date() < checkout_dt.date():
            cgst = tariff * 0.025
            sgst = tariff * 0.025
            total = tariff + cgst + sgst

            stay_rows.append({
                "date": current.strftime("%d-%m-%Y"),
                "hsn": generate_hsn(),
                "amount": tariff,
                "cgst": cgst,
                "sgst": sgst,
                "total": total
            })

            current += timedelta(days=1)

        tariff_total = sum(r["amount"] for r in stay_rows)
        cgst_total = sum(r["cgst"] for r in stay_rows)
        sgst_total = sum(r["sgst"] for r in stay_rows)
        grand_total = sum(r["total"] for r in stay_rows)

        # PAYMENTS
        pay_dates = request.form.getlist("pay_date[]")
        pay_methods = request.form.getlist("pay_method[]")
        pay_amounts = request.form.getlist("pay_amount[]")

        payments = []
        for d, m, a in zip(pay_dates, pay_methods, pay_amounts):
            if a:
                payments.append({
                    "date": datetime.strptime(d, "%Y-%m-%d").strftime("%d-%m-%Y"),
                    "method": m,
                    "amount": float(a)
                })

        payment_total = sum(p["amount"] for p in payments)
        net_balance = grand_total - payment_total

        return render_template("invoice.html",
            hotel_name=hotel_name,
            hotel_address=hotel_address,
            hotel_phone=hotel_phone,
            hotel_res_phone=hotel_res_phone,
            hotel_gstin=hotel_gstin,
            folio_no=folio_no,
            bill_no=bill_no,
            room_no=room_no,
            room_type=room_type,
            guest_name=guest_name,
            guest_address=guest_address,
            pax=pax,
            food_plan=food_plan,
            company=company,
            checkin=checkin_dt.strftime("%d-%m-%Y %H:%M"),
            checkout=checkout_dt.strftime("%d-%m-%Y %H:%M"),
            tariff=tariff,
            stay_rows=stay_rows,
            tariff_total=tariff_total,
            cgst_total=cgst_total,
            sgst_total=sgst_total,
            grand_total=grand_total,
            payments=payments,
            payment_total=payment_total,
            net_balance=net_balance
        )

    return render_template("form.html")



def create_invoice_pdf(data, items, filename):
    """Generates an 8cm-wide invoice PDF."""
    
    # Define a custom page size (80mm width). Height is arbitrary for start, 
    # as we'll set it dynamically later if needed. SimpleDocTemplate will handle height.
    page_width = 120 * mm
    # A safe large height to start, ReportLab will adjust it to content
    page_height = 1000 * mm 
    pagesize = (page_width, page_height)
    
    doc = SimpleDocTemplate(filename, pagesize=pagesize,
                            rightMargin=5*mm, leftMargin=5*mm,
                            topMargin=5*mm, bottomMargin=5*mm)
    elements = []
    styles = getSampleStyleSheet()

    # --- Define Custom Styles ---
    # Centered style for header info
    style_center = ParagraphStyle(name='CenteredText', parent=styles['Normal'],
                                   alignment=TA_CENTER, leading=10, fontSize=9)
    # Right-aligned for totals and amounts
    style_right = ParagraphStyle(name='RightText', parent=styles['Normal'],
                                   alignment=TA_RIGHT, fontSize=9)
    # Left-aligned with smaller font for items
    style_left_small = ParagraphStyle(name='LeftSmallText', parent=styles['Normal'],
                                   alignment=TA_LEFT, fontSize=8)
    # Standard left-aligned
    style_left = ParagraphStyle(name='LeftText', parent=styles['Normal'],
                                alignment=TA_LEFT, fontSize=9)
    # Bold left for header labels
    style_bold_left = ParagraphStyle(name='BoldLeft', parent=styles['Normal'],
                                     alignment=TA_LEFT, fontSize=10, fontName='Helvetica-Bold')

    # --- Add Header Data ---
    # Add an empty paragraph for spacing to avoid drawing too high on the page
    elements.append(Spacer(1, 2*mm)) 
    
    # Loop through the static data to populate the text paragraphs.
    for text in data['header_info']:
        # If 'bold' key is set to true, use the bold style, otherwise normal centered.
        style = style_bold_left if text.get('bold') else style_center
        elements.append(Paragraph(text['content'], style))

    # Add spacing after header
    elements.append(Spacer(1, 4*mm)) 

    # --- Add Bill-To Information ---
    elements.append(Paragraph(f"<b>111TABLE</b>", style_bold_left))
    elements.append(Spacer(1, 1*mm))
    elements.append(Paragraph("<b>Bill To:</b>", style_bold_left))
    elements.append(Paragraph(f"India", style_left)) # 'India' from data['bill_to']
    elements.append(Spacer(1, 1*mm))
    elements.append(Paragraph("<b>Ship To:</b>", style_bold_left))
    elements.append(Paragraph(f"R-5", style_left)) # 'R-5' from data['ship_to']
    elements.append(Spacer(1, 2*mm))

    # --- Add Invoice Details (Right-Aligned) ---
    invoice_details_str = (
        f"<b>Date:</b> {data['date']}<br/>"
        f"<b>Time:</b> {data['time']}<br/>"
        f"<b>Invoice No.:</b> {data['invoice_no']}"
    )
    elements.append(Paragraph(invoice_details_str, style_right))
    elements.append(Spacer(1, 3*mm))

    # --- Create Items Table ---
    # Define table headers for the item table.
    table_data = [['#', 'Name', 'Qty', 'Price', 'Amount']]
    
    # Process the dynamic item list to prepare rows for the table.
    for i, item in enumerate(items, 1):
        # We prepare strings for the table, format quantity to remove unnecessary decimals.
        table_row = [
            str(i),
            Paragraph(item['name'], style_left_small), # Using a Paragraph to allow word wrapping
            f"{float(item['qty']):.0f}", # format qty to integer
            f"{float(item['price']):.2f}", # format price to 2 decimals
            f"{float(item['amount']):.2f}"  # format amount to 2 decimals
        ]
        table_data.append(table_row)

    # --- Define Table Style ---
    # Create the table object with the list of prepared rows.
    # Set the widths of each column. The sum should be less than the available width.
    t = Table(table_data, colWidths=[6*mm, 30*mm, 9*mm, 12*mm, 14*mm])
    
    # Apply styling to the table.
    t.setStyle(TableStyle([
        # Headers: Bold, black text on a light gray background.
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 2*mm),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'), # Center headers

        # Grid lines: Top and bottom lines, no vertical internal lines
        ('LINEBELOW', (0, 0), (-1, 0), 0.2*mm, colors.black), # Line below headers
        ('GRID', (0, 1), (-1, -1), 0.1*mm, colors.black),  # A full grid for all item rows (optional, can adjust for look)
        # Or remove internal vertical lines:
        # ('LINEBEFORE', (1,1), (-1, -1), 0.1*mm, colors.white), 

        # Left-align item names.
        ('ALIGN', (1, 1), (1, -1), 'LEFT'),
        # Right-align numeric columns.
        ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),
        # Set the font size for the item list.
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        # Remove grid for better 'invoice list' feel (if preferred over full grid)
        # ('BOX', (0, 0), (-1, -1), 0.25, colors.black), # box around whole table
    ]))
    
    elements.append(t)
    elements.append(Spacer(1, 4*mm))

    # --- Add Total / Subtotal Section ---
    # Add a paragraph for total items count on the left.
    elements.append(Paragraph(f"<b>Total:</b> {data['total_items']}", style_bold_left))
    elements.append(Spacer(1, -1*mm)) # Reduce space between total items and line
    elements.append(Paragraph("-" * 85, style_bold_left)) # Simple line separator
    
    elements.append(Spacer(1, 2*mm))

    # Add the Sub Total and Total rows, right-aligned.
    elements.append(Paragraph(f"Sub Total : {data['sub_total']}", style_right))
    elements.append(Paragraph(f"Total : {data['total']}", style_right))

    # --- Build the PDF document ---
    # This will create and save the PDF to the specified filename.
    doc.build(elements)


@app.route('/hotelview')
def hotelview():
    """Renders the main invoice input form."""
    return render_template('index.html')


@app.route('/generate_pdf', methods=['POST'])
def generate_pdf():
    """Receives JSON data and generates the 8cm invoice PDF."""
    try:
        # Get the JSON data from the request body.
        request_data = request.get_json()
        if not request_data:
            return jsonify({'error': 'No data received'}), 400

        # Extract the list of dynamic items from the data.
        items = request_data.get('items', [])
        # The remaining data are the static fields.
        data_static = request_data

        # Define the PDF file path. For now, use a constant name, 
        # but in production you'd use a unique value (e.g., UUID or invoice_no).
        pdf_name = f"invoice_8cm.pdf"
        pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], pdf_name)

        # Call the PDF generation function.
        create_invoice_pdf(data_static, items, pdf_path)

        # Return a JSON response with the path to the generated file.
        # This will be used by JavaScript to trigger a download or display.
        return jsonify({'pdf_url': f'/download/{pdf_name}'}), 200

    except Exception as e:
        # Print errors to console for debugging and return an error response.
        print(f"Error: {e}")
        return jsonify({'error': 'Failed to generate PDF'}), 500

def generate_exact_pdf(data, filename):
    # Set exact 10cm width
    page_width = 100 * mm
    page_height = 200 * mm 
    doc = SimpleDocTemplate(filename, pagesize=(page_width, page_height),
                            rightMargin=5*mm, leftMargin=5*mm, 
                            topMargin=5*mm, bottomMargin=5*mm)
    
    styles = getSampleStyleSheet()
    elements = []

    # 1. Header Styles (Matches exact alignment)
    style_h = ParagraphStyle(name='H', alignment=TA_CENTER, fontSize=11, leading=12, fontName='Helvetica-Bold')
    style_a = ParagraphStyle(name='A', alignment=TA_CENTER, fontSize=9, leading=10)
    style_dot = ParagraphStyle(name='D', alignment=TA_CENTER, fontSize=10, leading=6)

    # Header Data
    elements.append(Paragraph(data['hotel_name'].upper(), style_h))
    elements.append(Paragraph(data['address_line1'], style_a))
    elements.append(Paragraph(data['address_line2'], style_a))
    elements.append(Paragraph(data['state_info'], style_a))
    elements.append(Paragraph(f"Ph.No.: {data['phone']}", style_a))
    
    # 2. Top Dotted Section
    elements.append(Spacer(1, 2*mm))
    elements.append(Paragraph("-" * 68, style_dot))
    elements.append(Paragraph("Tax Invoice", style_a))
    elements.append(Paragraph("-" * 68, style_dot))

    # 3. Info Table Alignment
    info_data = [
        [data['table_no'], f"Date: {data['date']}"],
        [f"Bill To: {data['bill_to']}", f"Time: {data['time']}"],
        [f"Ship To: {data['ship_to']}", f"Invoice No.: {data['invoice_no']}"]
    ]
    info_t = Table(info_data, colWidths=[55*mm, 35*mm])
    info_t.setStyle(TableStyle([
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('ALIGN', (1,0), (1,-1), 'RIGHT'),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))
    elements.append(info_t)
    
    # 4. Items Table (THE ALIGNMENT FIX)
    elements.append(Paragraph("-" * 68, style_dot))
    
    # Header Row
    item_rows = [['#', 'Name', 'Qty', 'Price', 'Amount']]
    for i, item in enumerate(data['items'], 1):
        item_rows.append([str(i), item['name'], item['qty'], item['price'], item['amount']])
    
    # Precise column widths for 10cm width
    t = Table(item_rows, colWidths=[8*mm, 42*mm, 10*mm, 15*mm, 15*mm])
    t.setStyle(TableStyle([
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('ALIGN', (2,0), (2,-1), 'CENTER'),
        ('ALIGN', (3,0), (-1,-1), 'RIGHT'),
        
        # KEY: This removes the gap causing the "floating" data
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        
        # Replicates the thermal printer dotted line precisely
        ('LINEBELOW', (0,0), (-1,0), 0.5, colors.black, 1, (1, 1)), 
    ]))
    elements.append(t)
    
    # 5. Footer and Totals
    elements.append(Paragraph("-" * 68, style_dot))
    
    footer_data = [
        [f"Total", data['total_qty'], "", f"{data['sub_total']}"],
        ["", "Sub Total", ":", f"{data['sub_total']}"],
        ["", "Total", ":", f"{data['grand_total']}"]
    ]
    
    # Aligns the colons (:) and values with the 'Amount' column above
    f_t = Table(footer_data, colWidths=[15*mm, 40*mm, 5*mm, 30*mm])
    f_t.setStyle(TableStyle([
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('ALIGN', (3,0), (3,-1), 'RIGHT'),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))
    elements.append(f_t)
    
    doc.build(elements)
    
@app.route('/download_pdf', methods=['POST'])
def download_pdf():
    data = request.json
    filename = os.path.join(UPLOAD_FOLDER, "exact_receipt.pdf")
    generate_exact_pdf(data, filename)
    return jsonify({"url": "/get_file/exact_receipt.pdf"})

@app.route('/get_file/<name>')
def get_file(name):
    return send_from_directory(UPLOAD_FOLDER, name)

@app.route('/download/<filename>')
def download_file(filename):
    """Provides the generated PDF as a downloadable file."""
    # Ensure the user is only downloading from our specific folder.
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)


if __name__ == '__main__':
    # Run the Flask app on localhost (port 5000 by default).
    app.run(debug=True)
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(5000))