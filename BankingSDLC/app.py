import os, sqlite3, logging
from pathlib import Path
from functools import wraps
from decimal import Decimal, InvalidOperation
from flask import Flask, g, request, redirect, url_for, session, flash, render_template_string
from werkzeug.security import generate_password_hash, check_password_hash

ROOT = Path(__file__).resolve().parent
DB_PATH = os.environ.get("BANKING_DATABASE", str(ROOT / "banking.db"))
app = Flask(__name__)
app.secret_key = os.environ.get("BANKING_SECRET_KEY", "local-demo-key-change-before-deployment")
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")
logging.basicConfig(filename=str(ROOT / "banking.log"), level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH, timeout=10)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys=ON")
    return g.db

@app.teardown_appcontext
def close_db(exc=None):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users(
      id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL,
      role TEXT NOT NULL CHECK(role IN ('customer','admin')), full_name TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS accounts(
      id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id),
      account_number TEXT UNIQUE NOT NULL, account_type TEXT NOT NULL DEFAULT 'Savings',
      balance_cents INTEGER NOT NULL DEFAULT 0 CHECK(balance_cents>=0));
    CREATE TABLE IF NOT EXISTS transactions(
      id INTEGER PRIMARY KEY, account_id INTEGER NOT NULL REFERENCES accounts(id),
      related_account_id INTEGER REFERENCES accounts(id),
      tx_type TEXT NOT NULL, amount_cents INTEGER NOT NULL CHECK(amount_cents>0),
      description TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS loans(
      id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id),
      amount_cents INTEGER NOT NULL CHECK(amount_cents>0), purpose TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'Pending' CHECK(status IN ('Pending','Approved','Rejected')),
      created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
    """)
    if not conn.execute("SELECT id FROM users WHERE username='admin'").fetchone():
        conn.execute("INSERT INTO users(username,password_hash,role,full_name) VALUES(?,?,?,?)",
                     ("admin", generate_password_hash("Admin123!"), "admin", "Demo Administrator"))
    if not conn.execute("SELECT id FROM users WHERE username='customer'").fetchone():
        cur = conn.execute("INSERT INTO users(username,password_hash,role,full_name) VALUES(?,?,?,?)",
                           ("customer", generate_password_hash("Customer123!"), "customer", "Demo Customer"))
        conn.execute("INSERT INTO accounts(user_id,account_number,balance_cents) VALUES(?,?,?)",
                     (cur.lastrowid, "1000000001", 1250000))
    conn.commit(); conn.close()

def logged_in(fn):
    @wraps(fn)
    def inner(*a, **kw):
        if not session.get("user_id"):
            flash("Please sign in first.", "warning")
            return redirect(url_for("login"))
        return fn(*a, **kw)
    return inner

def admin_only(fn):
    @wraps(fn)
    def inner(*a, **kw):
        if session.get("role") != "admin":
            flash("Administrator access required.", "danger")
            return redirect(url_for("dashboard"))
        return fn(*a, **kw)
    return inner

def cents(raw):
    try: val = Decimal(raw).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError): raise ValueError("Enter a valid amount.")
    if not val.is_finite() or val <= 0: raise ValueError("Amount must be greater than zero.")
    if val > Decimal("100000000"): raise ValueError("Amount exceeds demo limit.")
    return int(val * 100)

@app.template_filter("money")
def money(v): return f"{int(v)/100:,.2f}"

BASE = """<!doctype html><html lang=en><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>
<title>{{ title or 'BankSphere' }}</title><link href='https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css' rel=stylesheet>
<style>body{background:#f3f6fb;color:#1e293b}.navbar{background:#102a56}.hero{background:linear-gradient(120deg,#102a56,#2463a6);color:white;border-radius:20px;padding:42px}.panel,.cardx{background:white;border:1px solid #e1e8f0;border-radius:16px;padding:22px;box-shadow:0 6px 24px #0f172a08}.btn{border-radius:9px}.eyebrow{font-size:.75rem;letter-spacing:.15em;color:#4774a8;font-weight:bold}footer{color:#64748b}</style></head><body>
<nav class='navbar navbar-dark'><div class='container'><a class='navbar-brand fw-bold' href='/'>BankSphere</a>{% if session.get('user_id') %}<span class=text-white>{{ session.get('full_name') }} · {{ session.get('role') }}</span><form method=post action='/logout'><button class='btn btn-outline-light btn-sm'>Sign out</button></form>{% endif %}</div></nav>
<main class='container py-4'>{% with msgs=get_flashed_messages(with_categories=true) %}{% for cat,msg in msgs %}<div class='alert alert-{{cat}}'>{{msg}}</div>{% endfor %}{% endwith %}{{ body|safe }}</main>
<footer class='container text-center py-4 small'>Academic demo only — no real funds or banking services.</footer></body></html>"""

def page(body, title="BankSphere"):
    return render_template_string(BASE, body=body, title=title)

@app.route("/")
def home():
    if session.get("user_id"): return redirect(url_for("dashboard"))
    return page("""<section class=hero><span class='badge bg-light text-dark mb-3'>SDLC Major Project</span><h1 class='display-5 fw-bold'>Banking made simple.</h1><p class=lead>Manage demo accounts, transactions, and loan applications.</p><a class='btn btn-light btn-lg me-2' href=/login>Sign in</a><a class='btn btn-outline-light btn-lg' href=/register>Create account</a></section><div class='alert alert-warning mt-4'>Educational simulation only. Transactions do not move real money.</div>""", "Welcome")

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        name=request.form.get("full_name","").strip(); user=request.form.get("username","").strip().lower(); pw=request.form.get("password","")
        if len(name)<2 or len(user)<3 or not user.replace("_","").isalnum() or len(pw)<10:
            flash("Enter a name, username (3+ letters/numbers/underscores), and password of at least 10 characters.","danger")
        else:
            try:
                cur=db().execute("INSERT INTO users(username,password_hash,role,full_name) VALUES(?,?,?,?)",(user,generate_password_hash(pw),"customer",name))
                db().execute("INSERT INTO accounts(user_id,account_number,balance_cents) VALUES(?,?,0)",(cur.lastrowid,str(1000000000+cur.lastrowid)))
                db().commit(); log.info("Customer registered user_id=%s",cur.lastrowid)
                flash("Registration complete. Please sign in.","success"); return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                db().rollback(); flash("Username already exists.","danger")
    return page("""<div class='panel mx-auto' style='max-width:480px'><h2>Create customer account</h2><form method=post><label class=form-label>Full name</label><input class='form-control mb-3' name=full_name required maxlength=100><label class=form-label>Username</label><input class='form-control mb-3' name=username required minlength=3 maxlength=40><label class=form-label>Password (10+ characters)</label><input class='form-control mb-3' type=password name=password required minlength=10><button class='btn btn-primary w-100'>Register</button></form></div>""","Register")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method=="POST":
        user=db().execute("SELECT * FROM users WHERE username=?",(request.form.get("username","").strip().lower(),)).fetchone()
        if user and check_password_hash(user["password_hash"],request.form.get("password","")):
            session.clear(); session.update(user_id=user["id"],username=user["username"],full_name=user["full_name"],role=user["role"])
            log.info("Login user_id=%s",user["id"]); return redirect(url_for("dashboard"))
        log.warning("Failed login username=%s",request.form.get("username","")[:40]); flash("Invalid username or password.","danger")
    return page("""<div class='panel mx-auto' style='max-width:480px'><h2>Sign in</h2><form method=post><label class=form-label>Username</label><input class='form-control mb-3' name=username required><label class=form-label>Password</label><input class='form-control mb-3' name=password type=password required><button class='btn btn-primary w-100'>Sign in</button></form><p class='small text-secondary mt-3'>Demo admin: admin / Admin123!<br>Demo customer: customer / Customer123!</p><a href=/register>Create account</a></div>""","Sign in")

@app.route("/logout",methods=["POST"])
def logout():
    session.clear(); flash("Signed out.","info"); return redirect(url_for("home"))

@app.route("/dashboard")
@logged_in
def dashboard():
    if session["role"]=="admin":
        accounts=db().execute("SELECT a.*,u.full_name,u.username FROM accounts a JOIN users u ON u.id=a.user_id ORDER BY a.id DESC").fetchall()
        return page("<p class=eyebrow>ADMINISTRATION</p><h1>Banking overview</h1><div class=panel><a class='btn btn-primary mb-3' href=/loans>Review loans</a> <a class='btn btn-outline-primary mb-3' href=/transactions>Transactions</a><div class=table-responsive><table class='table'><tr><th>Customer</th><th>Username</th><th>Account</th><th>Balance</th></tr>"+ "".join(f"<tr><td>{a['full_name']}</td><td>{a['username']}</td><td>{a['account_number']}</td><td>₹{a['balance_cents']/100:,.2f}</td></tr>" for a in accounts)+"</table></div></div>","Admin dashboard")
    accounts=db().execute("SELECT * FROM accounts WHERE user_id=?",(session["user_id"],)).fetchall()
    loans=db().execute("SELECT * FROM loans WHERE user_id=? ORDER BY id DESC",(session["user_id"],)).fetchall()
    cards="".join(f"<div class='col-md-6'><div class=cardx><span class=text-secondary>{a['account_type']} account</span><h2 class='mt-3'>₹{a['balance_cents']/100:,.2f}</h2><span class=text-secondary>Account no. {a['account_number']}</span></div></div>" for a in accounts)
    loanrows="".join(f"<li class=list-group-item>{l['purpose']} — ₹{l['amount_cents']/100:,.2f} <span class='badge bg-secondary'>{l['status']}</span></li>" for l in loans) or "<li class=list-group-item>No loan applications yet.</li>"
    body=f"""<div class='d-flex justify-content-between align-items-end mb-4'><div><p class=eyebrow>CUSTOMER OVERVIEW</p><h1>Hello, {session['full_name']}</h1></div><a class='btn btn-outline-primary' href=/transactions>Transaction history</a></div><div class='row g-3 mb-4'>{cards}</div><div class='row g-4'><div class=col-lg-7><div class=panel><h4>Demo transaction</h4><form method=post action=/transaction><label class=form-label>Account</label><select class='form-select mb-3' name=account_id>{''.join(f"<option value='{a['id']}'>{a['account_number']}</option>" for a in accounts)}</select><label class=form-label>Type</label><select class='form-select mb-3' name=kind><option value=deposit>Deposit</option><option value=withdrawal>Withdrawal</option><option value=transfer>Transfer</option></select><label class=form-label>Destination account (transfer only)</label><input class='form-control mb-3' name=target_account><label class=form-label>Amount (₹)</label><input class='form-control mb-3' type=number step=.01 min=.01 name=amount required><button class='btn btn-primary'>Submit</button></form><p class='small text-secondary mt-2'>Simulated transaction only.</p></div></div><div class=col-lg-5><div class=panel><h4>Loan applications</h4><ul class=list-group list-group-flush>{loanrows}</ul><a class='btn btn-outline-primary mt-3' href=/loans>Manage loans</a></div></div></div>"""
    return page(body,"Dashboard")

@app.route("/transaction",methods=["POST"])
@logged_in
def transaction():
    if session["role"]!="customer": flash("Use a customer account.","warning"); return redirect(url_for("dashboard"))
    try:
        amount=cents(request.form.get("amount","")); aid=request.form.get("account_id",type=int); kind=request.form.get("kind")
        source=db().execute("SELECT * FROM accounts WHERE id=? AND user_id=?",(aid,session["user_id"])).fetchone()
        if not source: raise ValueError("Account not found.")
        if kind=="deposit":
            db().execute("UPDATE accounts SET balance_cents=balance_cents+? WHERE id=?",(amount,aid))
            db().execute("INSERT INTO transactions(account_id,tx_type,amount_cents,description) VALUES(?,?,?,?)",(aid,"deposit",amount,"Simulated deposit"))
        elif kind in ("withdrawal","transfer"):
            cur=db().execute("UPDATE accounts SET balance_cents=balance_cents-? WHERE id=? AND balance_cents>=?",(amount,aid,amount))
            if cur.rowcount!=1: raise ValueError("Insufficient funds.")
            if kind=="withdrawal":
                db().execute("INSERT INTO transactions(account_id,tx_type,amount_cents,description) VALUES(?,?,?,?)",(aid,"withdrawal",amount,"Simulated withdrawal"))
            else:
                target=db().execute("SELECT * FROM accounts WHERE account_number=?",(request.form.get("target_account","").strip(),)).fetchone()
                if not target or target["id"]==aid: raise ValueError("Enter a valid different destination account.")
                db().execute("UPDATE accounts SET balance_cents=balance_cents+? WHERE id=?",(amount,target["id"]))
                db().execute("INSERT INTO transactions(account_id,related_account_id,tx_type,amount_cents,description) VALUES(?,?,?,?,?)",(aid,target["id"],"transfer_out",amount,"Demo transfer out"))
                db().execute("INSERT INTO transactions(account_id,related_account_id,tx_type,amount_cents,description) VALUES(?,?,?,?,?)",(target["id"],aid,"transfer_in",amount,"Demo transfer in"))
        else: raise ValueError("Invalid transaction type.")
        db().commit(); log.info("Transaction user_id=%s kind=%s cents=%s",session["user_id"],kind,amount); flash("Transaction completed.","success")
    except ValueError as e:
        db().rollback(); flash(str(e),"danger")
    except Exception:
        db().rollback(); log.exception("Transaction failed"); flash("Transaction failed; see local log.","danger")
    return redirect(url_for("dashboard"))

@app.route("/transactions")
@logged_in
def transactions():
    if session["role"]=="admin":
        rows=db().execute("SELECT t.*,a.account_number,u.full_name FROM transactions t JOIN accounts a ON a.id=t.account_id JOIN users u ON u.id=a.user_id ORDER BY t.id DESC LIMIT 100").fetchall()
    else:
        rows=db().execute("SELECT t.*,a.account_number FROM transactions t JOIN accounts a ON a.id=t.account_id WHERE a.user_id=? ORDER BY t.id DESC LIMIT 100",(session["user_id"],)).fetchall()
    extra="<th>Customer</th>" if session["role"]=="admin" else ""
    rows_html="".join("<tr><td>"+r["created_at"]+"</td>"+(f"<td>{r['full_name']}</td>" if session["role"]=="admin" else "")+f"<td>{r['account_number']}</td><td>{r['tx_type']}</td><td>{r['description']}</td><td>₹{r['amount_cents']/100:,.2f}</td></tr>" for r in rows)
    return page(f"<h1>Transaction history</h1><div class=panel><div class=table-responsive><table class=table><tr><th>Date</th>{extra}<th>Account</th><th>Type</th><th>Description</th><th>Amount</th></tr>{rows_html}</table></div><a href=/dashboard>Back to dashboard</a></div>","Transactions")

@app.route("/loans",methods=["GET","POST"])
@logged_in
def loans():
    if request.method=="POST" and session["role"]=="customer":
        try:
            amount=cents(request.form.get("amount","")); purpose=request.form.get("purpose","").strip()
            if not 5<=len(purpose)<=250: raise ValueError("Purpose must be 5–250 characters.")
            db().execute("INSERT INTO loans(user_id,amount_cents,purpose) VALUES(?,?,?)",(session["user_id"],amount,purpose)); db().commit()
            log.info("Loan application user_id=%s",session["user_id"]); flash("Loan application submitted.","success")
        except ValueError as e: flash(str(e),"danger")
    if session["role"]=="admin":
        rows=db().execute("SELECT l.*,u.full_name,u.username FROM loans l JOIN users u ON u.id=l.user_id ORDER BY l.id DESC").fetchall()
    else: rows=db().execute("SELECT * FROM loans WHERE user_id=? ORDER BY id DESC",(session["user_id"],)).fetchall()
    admin=session["role"]=="admin"
    body="<h1>Loan applications</h1>"
    if not admin: body+="""<div class=panel><h4>Apply for a loan</h4><form method=post><label class=form-label>Amount (₹)</label><input class='form-control mb-3' type=number name=amount min=.01 step=.01 required><label class=form-label>Purpose</label><input class='form-control mb-3' name=purpose minlength=5 maxlength=250 required><button class='btn btn-primary'>Submit application</button></form></div>"""
    body+="<div class='panel mt-4'><div class=table-responsive><table class=table><tr>"+("<th>Customer</th>" if admin else "")+"<th>Amount</th><th>Purpose</th><th>Status</th><th>Action</th></tr>"
    for l in rows:
        action=""
        if admin and l["status"]=="Pending":
            action=f"""<form method=post action='/loans/{l['id']}/status' class='d-flex gap-2'><button class='btn btn-sm btn-success' name=status value=Approved>Approve</button><button class='btn btn-sm btn-outline-danger' name=status value=Rejected>Reject</button></form>"""
        body+="<tr>"+(f"<td>{l['full_name']}</td>" if admin else "")+f"<td>₹{l['amount_cents']/100:,.2f}</td><td>{l['purpose']}</td><td>{l['status']}</td><td>{action}</td></tr>"
    body+="</table></div></div><a href=/dashboard>Back to dashboard</a>"
    return page(body,"Loans")

@app.route("/loans/<int:loan_id>/status",methods=["POST"])
@logged_in
@admin_only
def loan_status(loan_id):
    status=request.form.get("status")
    if status not in ("Approved","Rejected"): flash("Invalid decision.","danger")
    else:
        cur=db().execute("UPDATE loans SET status=? WHERE id=? AND status='Pending'",(status,loan_id)); db().commit()
        flash("Loan decision saved." if cur.rowcount else "Loan not found or already reviewed.","success" if cur.rowcount else "warning")
    return redirect(url_for("loans"))

@app.errorhandler(404)
def not_found(e): return page("<h1>404 — Page not found</h1><a href=/>Home</a>","Not found"),404

@app.cli.command("init-db")
def init_db_command():
    init_db(); print("Database initialized. Demo logins: admin/Admin123! and customer/Customer123!")

if __name__=="__main__":
    init_db()
    app.run(debug=False)
