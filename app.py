from flask import Flask, render_template, request
from datetime import datetime, timedelta
import random

app = Flask(__name__)


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


@app.route("/", methods=["GET", "POST"])
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


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)