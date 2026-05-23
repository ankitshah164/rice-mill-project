# Fixed `app.py` for Rice Mill Management System


from flask import Flask, render_template, request, redirect, session
from reportlab.pdfgen import canvas
from openpyxl import Workbook
from flask import send_file
from flask_mail import Mail, Message
import sqlite3


# =========================
# DATABASE SETUP
# =========================

def init_db():
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()

    # Purchase Table
    cur.execute('''
    CREATE TABLE IF NOT EXISTS purchase (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        farmer_name TEXT,
        quantity INTEGER,
        price INTEGER,
        date TEXT
    )
    ''')

    # Sales Table
    cur.execute('''
    CREATE TABLE IF NOT EXISTS sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_name TEXT,
        rice_type TEXT,
        quantity INTEGER,
        price INTEGER,
        date TEXT
    )
    ''')

    # Stock Table
    cur.execute('''
    CREATE TABLE IF NOT EXISTS stock (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rice_type TEXT,
        quantity INTEGER
    )
    ''')

    conn.commit()
    conn.close()


init_db()


# =========================
# FLASK APP
# =========================

app = Flask(__name__)
app.config['MAIL_SERVER']='smtp.gmail.com'
app.config['MAIL_PORT']=587
app.config['MAIL_USE_TLS']=True
app.config['MAIL_USERNAME']='your_email@gmail.com'
app.config['MAIL_PASSWORD']='your_app_password'

mail = Mail(app)
app.secret_key = 'rice_mill_secret'


# =========================
# LOGIN ROUTE
# =========================

@app.route('/login', methods=['GET', 'POST'])
def login():


    if request.method == 'POST':

        username = request.form['username']
        password = request.form['password']

        if username == 'admin' and password == '1234':

            session['user'] = username
            session['role'] = 'admin'

        elif username == 'staff' and password == '1234':

            session['user'] = username
            session['role'] = 'staff'

        else:
            return "Invalid username or password"

        return redirect('/')

    return render_template('login.html')
# =========================
# LOGOUT ROUTE
# =========================

@app.route('/logout')
def logout():

    session.pop('user', None)

    return redirect('/login')


# =========================
# HOME DASHBOARD
# =========================

@app.route('/')
def home():

    if 'user' not in session:
        return redirect('/login')

    conn = sqlite3.connect('database.db')
    cur = conn.cursor()

    # Total Purchase Amount
    cur.execute("SELECT SUM(price * quantity) FROM purchase")
    total_purchase = cur.fetchone()[0] or 0

    # Total Sales Amount
    cur.execute("SELECT SUM(price * quantity) FROM sales")
    total_sales = cur.fetchone()[0] or 0

    # Purchase Quantity
    cur.execute("SELECT SUM(quantity) FROM purchase")
    purchase_qty = cur.fetchone()[0] or 0

    # Sales Quantity
    cur.execute("SELECT SUM(quantity) FROM sales")
    sales_qty = cur.fetchone()[0] or 0

    stock_left = purchase_qty - sales_qty
    profit = total_sales - total_purchase

    conn.close()

    return render_template(
        'index.html',
        stock=stock_left,
        profit=profit,
        total_sales=total_sales,
        total_purchase=total_purchase
    )


# =========================
# PURCHASE ROUTE
# =========================

@app.route('/purchase', methods=['GET', 'POST'])
def purchase():

    if request.method == 'POST':

        name = request.form['farmer_name']
        quantity = request.form['quantity']
        price = request.form['price']
        date = request.form['date']

        conn = sqlite3.connect('database.db')
        cur = conn.cursor()

        # Insert Purchase
        cur.execute(
            "INSERT INTO purchase (farmer_name, quantity, price, date) VALUES (?, ?, ?, ?)",
            (name, quantity, price, date)
        )

        # Update Stock
        cur.execute("SELECT quantity FROM stock WHERE rice_type = 'default'")
        row = cur.fetchone()

        if row:
            new_qty = row[0] + int(quantity)
            cur.execute(
                "UPDATE stock SET quantity = ? WHERE rice_type = 'default'",
                (new_qty,)
            )
        else:
            cur.execute(
                "INSERT INTO stock (rice_type, quantity) VALUES (?, ?)",
                ('default', quantity)
            )

        conn.commit()
        conn.close()

        return redirect('/')

    return render_template('purchase.html')


# =========================
# SALES ROUTE
# =========================

@app.route('/sales', methods=['GET', 'POST'])
def sales():

    if request.method == 'POST':

        name = request.form['customer_name']
        rice = request.form['rice_type']
        quantity = request.form['quantity']
        price = request.form['price']
        date = request.form['date']

        conn = sqlite3.connect('database.db')
        cur = conn.cursor()

        # Insert Sales
        cur.execute(
            "INSERT INTO sales (customer_name, rice_type, quantity, price, date) VALUES (?, ?, ?, ?, ?)",
            (name, rice, quantity, price, date)
        )

        # Reduce Stock
        cur.execute("SELECT quantity FROM stock WHERE rice_type = 'default'")
        row = cur.fetchone()

        if row:
            new_qty = row[0] - int(quantity)

            if new_qty < 0:
                new_qty = 0

            cur.execute(
                "UPDATE stock SET quantity = ? WHERE rice_type = 'default'",
                (new_qty,)
            )

        conn.commit()
        conn.close()

        return redirect('/')

    return render_template('sales.html')


# =========================
# STOCK ROUTE
# =========================
@app.route('/stock')
def stock():

    conn = sqlite3.connect('database.db')
    cur = conn.cursor()

    cur.execute("SELECT * FROM stock")
    data = cur.fetchall()

    alerts=[]

    for row in data:

        quantity=row[2]

        if quantity < 20:
            alerts.append(
                f"{row[1]} stock is low ({quantity} remaining)"
            )

    conn.close()

    return render_template(
        'stock.html',
        data=data,
        alerts=alerts
    )
# =========================
# REPORT ROUTE
# =========================

@app.route('/report')
def report():

    start = request.args.get('start')
    end = request.args.get('end')

    conn = sqlite3.connect('database.db')
    cur = conn.cursor()

    if start and end:

        cur.execute(
            """
            SELECT SUM(price*quantity)
            FROM purchase
            WHERE date BETWEEN ? AND ?
            """,
            (start, end)
        )

        total_purchase = cur.fetchone()[0] or 0

        cur.execute(
            """
            SELECT SUM(price*quantity)
            FROM sales
            WHERE date BETWEEN ? AND ?
            """,
            (start, end)
        )

        total_sales = cur.fetchone()[0] or 0

    else:

        cur.execute(
            "SELECT SUM(price*quantity) FROM purchase"
        )
        total_purchase = cur.fetchone()[0] or 0

        cur.execute(
            "SELECT SUM(price*quantity) FROM sales"
        )
        total_sales = cur.fetchone()[0] or 0

    profit = total_sales - total_purchase

    conn.close()

    return render_template(
        'report.html',
        purchase=total_purchase,
        sales=total_sales,
        profit=profit
    )


# =========================
# VIEW PURCHASE HISTORY
# =========================

@app.route('/view_purchase')
def view_purchase():

    search = request.args.get('search', '')

    conn = sqlite3.connect('database.db')
    cur = conn.cursor()

    cur.execute(
        "SELECT * FROM purchase WHERE farmer_name LIKE ?",
        ('%' + search + '%',)
    )

    data = cur.fetchall()

    conn.close()

    return render_template(
        'view_purchase.html',
        data=data,
        search=search
    )


# =========================
# VIEW SALES HISTORY
# =========================

@app.route('/view_sales')
def view_sales():

    conn = sqlite3.connect('database.db')
    cur = conn.cursor()

    cur.execute("SELECT * FROM sales")
    data = cur.fetchall()

    conn.close()

    return render_template('view_sales.html', data=data)


# =========================
# DELETE PURCHASE
# =========================

@app.route('/delete_purchase/<int:id>')
def delete_purchase(id):

    conn = sqlite3.connect('database.db')
    cur = conn.cursor()

    cur.execute("DELETE FROM purchase WHERE id = ?", (id,))

    conn.commit()
    conn.close()

    return redirect('/view_purchase')


# =========================
# EDIT PURCHASE
# =========================

@app.route('/edit_purchase/<int:id>', methods=['GET', 'POST'])
def edit_purchase(id):

    conn = sqlite3.connect('database.db')
    cur = conn.cursor()

    if request.method == 'POST':

        name = request.form['farmer_name']
        quantity = request.form['quantity']
        price = request.form['price']
        date = request.form['date']

        cur.execute(
            """
            UPDATE purchase
            SET farmer_name=?, quantity=?, price=?, date=?
            WHERE id=?
            """,
            (name, quantity, price, date, id)
        )

        conn.commit()
        conn.close()

        return redirect('/view_purchase')

    cur.execute("SELECT * FROM purchase WHERE id=?", (id,))
    data = cur.fetchone()

    conn.close()

    return render_template('edit_purchase.html', data=data)
# invoice ko lagi chai 
@app.route('/invoice/<int:id>')
def invoice(id):

    conn = sqlite3.connect('database.db')
    cur = conn.cursor()

    cur.execute("SELECT * FROM sales WHERE id=?", (id,))
    sale = cur.fetchone()

    conn.close()

    filename = f"invoice_{id}.pdf"

    pdf = canvas.Canvas(filename)

    pdf.setFont("Helvetica-Bold", 20)
    pdf.drawString(200, 800, "Rice Mill Invoice")

    pdf.setFont("Helvetica", 12)

    pdf.drawString(100, 700, f"Customer Name: {sale[1]}")
    pdf.drawString(100, 670, f"Rice Type: {sale[2]}")
    pdf.drawString(100, 640, f"Quantity: {sale[3]}")
    pdf.drawString(100, 610, f"Price: {sale[4]}")
    pdf.drawString(100, 580, f"Date: {sale[5]}")

    total = sale[3] * sale[4]

    pdf.drawString(100, 520, f"Total Amount: {total}")

    pdf.save()

    return f"Invoice Generated: {filename}"
#yo chai excel ma export garna ko lagi 

@app.route('/export_sales')
def export_sales():

    conn = sqlite3.connect('database.db')
    cur = conn.cursor()

    cur.execute("SELECT * FROM sales")
    data = cur.fetchall()

    conn.close()

    wb = Workbook()
    ws = wb.active

    ws.append([
        'ID',
        'Customer Name',
        'Rice Type',
        'Quantity',
        'Price',
        'Date'
    ])

    for row in data:
        ws.append(row)

    filename = 'sales_report.xlsx'

    wb.save(filename)

    return send_file(filename, as_attachment=True)
#report send garna ko lagi 
@app.route('/send_report')
def send_report():

    msg = Message(
        'Rice Mill Report',
        sender='your_email@gmail.com',
        recipients=['receiver@gmail.com']
    )

    msg.body = 'Daily Rice Mill Report Generated.'

    mail.send(msg)

    return "Email Sent Successfully"


# =========================
# RUN APP
# =========================

if __name__ == '__main__':
    app.run(debug=True)


