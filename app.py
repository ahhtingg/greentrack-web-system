from flask import Flask, send_file, request, abort, send_from_directory, render_template, jsonify, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import qrcode
import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from datetime import datetime, timedelta
import socket
import random


app = Flask(__name__)
app.secret_key = "secret123"
app.permanent_session_lifetime = timedelta(hours=10)
DB_NAME = "certificates.db"


# =========================
# 自动获取局域网 IP
# =========================
def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_award_table():
    conn = get_db_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS award_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            date TEXT NOT NULL,
            time TEXT,
            location TEXT NOT NULL,
            description TEXT
        )
    """)
    conn.commit()
    conn.close()

def init_reset_logs_table():
    conn = get_db_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS reset_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            code TEXT NOT NULL,
            requested_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

@app.route("/monthly_summary")
def monthly_summary():
    return render_template("monthly_summary.html")

@app.route("/admin_reset_logs")
def admin_reset_logs():
    conn = get_db_connection()
    logs = conn.execute("""
        SELECT * FROM reset_logs
        ORDER BY id DESC
    """).fetchall()
    conn.close()

    return render_template("admin_reset_logs.html", logs=logs)



def init_users_table():
    conn = get_db_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            last_login TEXT,
            last_logout TEXT,
            is_logged_in INTEGER NOT NULL DEFAULT 0
        )
    """)
    conn.commit()

    columns = [row["name"] for row in conn.execute("PRAGMA table_info(users)").fetchall()]

    # 新增 Merchant / Officer 额外资料
    if "company_name" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN company_name TEXT")
        conn.commit()

    if "officer_name" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN officer_name TEXT")
        conn.commit()

    if "department" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN department TEXT")
        conn.commit()

    if "contact" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN contact TEXT")
        conn.commit()

    if "last_login" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN last_login TEXT")
        conn.commit()

    if "last_logout" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN last_logout TEXT")
        conn.commit()

    if "is_logged_in" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN is_logged_in INTEGER NOT NULL DEFAULT 0")
        conn.commit()

    conn.close()

def init_superadmin():
    conn = get_db_connection()

    existing = conn.execute(
        "SELECT * FROM users WHERE username = ?",
        ("superadmin",)
    ).fetchone()

    hashed_password = generate_password_hash("Admin123#")

    if not existing:
        conn.execute("""
            INSERT INTO users (username, email, password, role)
            VALUES (?, ?, ?, ?)
        """, ("superadmin", "superadmin@greentrack.com", hashed_password, "superadmin"))
    else:
        conn.execute("""
            UPDATE users
            SET email = ?, password = ?, role = ?
            WHERE username = ?
        """, ("superadmin@greentrack.com", hashed_password, "superadmin", "superadmin"))

    conn.commit()
    conn.close()
    
def get_current_user():
    if "user_id" not in session:
        return None

    conn = get_db_connection()
    user = conn.execute(
        "SELECT * FROM users WHERE id = ?",
        (session["user_id"],)
    ).fetchone()
    conn.close()

    return user

# =========================
# 初始化数据库
# =========================
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS certificates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cert_id TEXT UNIQUE,
        name TEXT,
        programme TEXT,
        location TEXT,
        date TEXT,
        remarks TEXT
    )
    """)

    c.execute("PRAGMA table_info(certificates)")
    columns = [row[1] for row in c.fetchall()]

    if "remarks" not in columns:
        c.execute("ALTER TABLE certificates ADD COLUMN remarks TEXT")

    conn.commit()
    conn.close()

@app.route("/images/<path:filename>")
def serve_images(filename):
    return send_from_directory("images", filename)

@app.route("/publish_event")
def publish_event():
    return render_template("publish_event.html")

@app.route("/user_events")
def user_events():
    return render_template("user_events.html")

@app.route("/user_list")
def user_list():
    return render_template("user_list.html")

@app.route("/ranking")
def ranking():
    return render_template("ranking.html")

@app.route("/education")
def education():
    return render_template("education.html")

# =========================
# 首页
# =========================
@app.route("/")
def home():
    user = get_current_user()
    return render_template("index.html", user=user)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    username = request.form.get("username", "").strip()
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "").strip()
    confirm_password = request.form.get("confirm_password", "").strip()

    # 基本验证
    if not username or not email or not password or not confirm_password:
        flash("Please fill in all required fields.")
        return redirect(url_for("register"))

    if password != confirm_password:
        flash("Passwords do not match.")
        return redirect(url_for("register"))

    # 可选：保留你原本的密码规则
    import re
    if len(password) < 8:
        flash("Password must be at least 8 characters.")
        return redirect(url_for("register"))
    if not re.search(r"[A-Z]", password):
        flash("Password must contain at least 1 uppercase letter.")
        return redirect(url_for("register"))
    if not re.search(r"[a-z]", password):
        flash("Password must contain at least 1 lowercase letter.")
        return redirect(url_for("register"))
    if not re.search(r"[0-9]", password):
        flash("Password must contain at least 1 number.")
        return redirect(url_for("register"))
    if not re.search(r"[#\$%&\*_\+\-/!@]", password):
        flash("Password must contain at least 1 special symbol.")
        return redirect(url_for("register"))

    hashed_password = generate_password_hash(password)

    conn = get_db_connection()

    # 检查 username / email 是否已存在
    existing_user = conn.execute(
        "SELECT * FROM users WHERE username = ? OR email = ?",
        (username, email)
    ).fetchone()

    if existing_user:
        conn.close()
        flash("Username or email already exists.")
        return redirect(url_for("register"))

    conn.execute("""
        INSERT INTO users (username, email, password, role)
        VALUES (?, ?, ?, ?)
    """, (username, email, hashed_password, "resident"))

    conn.commit()
    conn.close()

    return render_template("register_success.html")

# =========================
# 从 templates 提供 issued_certificates.html
# =========================
@app.route("/issued_certificates")
def issued_certificates_page():
    return render_template("issued_certificates.html")

@app.route("/api/certificates")
def api_certificates():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
        SELECT cert_id, name, programme, location, date
        FROM certificates
        ORDER BY id DESC
    """)
    rows = c.fetchall()
    conn.close()

    certificates = []
    base_url = "https://prance-excavator-unlivable.ngrok-free.dev"

    for row in rows:
        certificates.append({
            "id": row[0],
            "name": row[1],
            "programme": row[2],
            "location": row[3],
            "date": row[4],
            "baseUrl": base_url
        })

    return jsonify(certificates)

@app.route("/superadmin_dashboard")
def superadmin_dashboard():
    user = get_current_user()

    if not user or user["role"] != "superadmin":
        flash("Please login as Super Admin first.")
        return redirect(url_for("login"))

    return render_template("superadmin_dashboard.html")

@app.route("/admin_create_merchant")
def admin_create_merchant_page():
    user = get_current_user()

    if not user or user["role"] != "superadmin":
        flash("Please login as Super Admin first.")
        return redirect(url_for("login"))

    return render_template("admin_create_merchant.html")


@app.route("/admin_create_officer")
def admin_create_officer_page():
    user = get_current_user()

    if not user or user["role"] != "superadmin":
        flash("Please login as Super Admin first.")
        return redirect(url_for("login"))

    return render_template("admin_create_officer.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()
    selected_role = request.form.get("selected_role", "").strip()

    if not username or not password:
        flash("Please fill in all fields.")
        return redirect(url_for("login"))

    conn = get_db_connection()
    user = conn.execute(
        "SELECT * FROM users WHERE username = ?",
        (username,)
    ).fetchone()

    if not user:
        conn.close()
        flash("Invalid username or password.")
        return redirect(url_for("login"))

    if not check_password_hash(user["password"], password):
        conn.close()
        flash("Invalid username or password.")
        return redirect(url_for("login"))
    
    # 加在这里
    if selected_role and user["role"] != selected_role:
        conn.close()
        flash(f"This account cannot log in through the {selected_role.capitalize()} login page.")
        return redirect(url_for("login", role=selected_role))

    session.permanent = True
    session["user_id"] = user["id"]
    session["username"] = user["username"]
    session["role"] = user["role"]

    conn.execute("""
        UPDATE users
        SET last_login = ?, is_logged_in = 1
        WHERE id = ?
    """, (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user["id"]))
    conn.commit()
    conn.close()

    if user["role"] == "superadmin":
        return redirect("/superadmin_dashboard")

    elif user["role"] == "merchant":
      return redirect("/merchant_dashboard")

    elif user["role"] == "officer":
      return redirect("/officer_dashboard")

    else:
      return redirect("/user_dashboard")

@app.route("/merchant_dashboard")
def merchant_dashboard():
    user = get_current_user()

    if not user or user["role"] != "merchant":
        return redirect("/login")

    return render_template("merchant_dashboard.html")

@app.route("/officer_dashboard")
def officer_dashboard():
    user = get_current_user()
    if not user or user["role"] != "officer":
        return redirect("/login")
    return render_template("officer_dashboard.html")

@app.route("/user_dashboard")
def user_dashboard():
    user = get_current_user()

    if not user or user["role"] != "resident":
        return redirect("/login")

    return render_template("user_dashboard.html")

@app.route("/go/resident")
def go_resident():
    user = get_current_user()

    if not user:
        flash("Please log in first.")
        return redirect(url_for("login"))

    if user["role"] != "resident":
        flash("Access denied. Resident account required.")
        return redirect(url_for("home"))

    return redirect("/user_dashboard")


@app.route("/go/merchant")
def go_merchant():
    user = get_current_user()

    if not user:
        flash("Please log in first.")
        return redirect(url_for("login"))

    if user["role"] != "merchant":
        flash("Access denied. Merchant account required.")
        return redirect(url_for("home"))

    return redirect("/merchant_dashboard")


@app.route("/go/officer")
def go_officer():
    user = get_current_user()

    if not user:
        flash("Please log in first.")
        return redirect(url_for("login"))

    if user["role"] != "officer":
        flash("Access denied. Officer account required.")
        return redirect(url_for("home"))

    return redirect("/officer_dashboard")

# =========================
# 如需要，也可提供其他单独 html
# =========================
@app.route("/page/<path:filename>")
def serve_template_page(filename):
    templates_dir = "templates"
    full_path = os.path.join(templates_dir, filename)

    if filename.endswith(".html") and os.path.exists(full_path):
        return send_from_directory(templates_dir, filename)

    abort(404)

@app.route("/api/delete_certificate/<cert_id>", methods=["DELETE"])
def delete_certificate(cert_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # 先检查证书是否存在
    c.execute("SELECT * FROM certificates WHERE cert_id=?", (cert_id,))
    result = c.fetchone()

    if not result:
        conn.close()
        return jsonify({"success": False, "message": "Certificate not found"}), 404

    # 删除数据库记录
    c.execute("DELETE FROM certificates WHERE cert_id=?", (cert_id,))
    conn.commit()
    conn.close()

    # 可选：顺便删 QR 图片
    qr_path = f"qr_codes/{cert_id}.png"
    if os.path.exists(qr_path):
        os.remove(qr_path)

    # 可选：顺便删 PDF
    pdf_path = f"pdf/{cert_id}.pdf"
    if os.path.exists(pdf_path):
        os.remove(pdf_path)

    return jsonify({"success": True, "message": f"{cert_id} deleted successfully"})

@app.route('/manage_award')
def manage_award():
    conn = get_db_connection()
    awards = conn.execute("SELECT * FROM award_events ORDER BY date DESC, time DESC").fetchall()
    conn.close()
    return render_template('manage_award.html', awards=awards, edit_award=None)

@app.route('/save_award', methods=['POST'])
def save_award():
    award_id = request.form.get('editId')
    title = request.form.get('title', '').strip()
    date = request.form.get('date', '').strip()
    time = request.form.get('time', '').strip()
    location = request.form.get('location', '').strip()
    description = request.form.get('description', '').strip()

    if not title or not date or not location:
        flash("Title, date, and location are required.")
        return redirect(url_for('manage_award'))

    conn = get_db_connection()

    if award_id:
        conn.execute("""
            UPDATE award_events
            SET title = ?, date = ?, time = ?, location = ?, description = ?
            WHERE id = ?
        """, (title, date, time, location, description, award_id))
        flash("Award ceremony updated successfully.")
    else:
        conn.execute("""
            INSERT INTO award_events (title, date, time, location, description)
            VALUES (?, ?, ?, ?, ?)
        """, (title, date, time, location, description))
        flash("Award ceremony added successfully.")

    conn.commit()
    conn.close()

    return redirect(url_for('manage_award'))

@app.route('/edit_award/<int:award_id>')
def edit_award(award_id):
    conn = get_db_connection()
    awards = conn.execute("SELECT * FROM award_events ORDER BY date DESC, time DESC").fetchall()
    edit_award = conn.execute("SELECT * FROM award_events WHERE id = ?", (award_id,)).fetchone()
    conn.close()

    return render_template('manage_award.html', awards=awards, edit_award=edit_award)


@app.route('/delete_award/<int:award_id>', methods=['GET', 'POST'])
def delete_award(award_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM award_events WHERE id = ?", (award_id,))
    conn.commit()
    conn.close()

    flash("Award ceremony deleted successfully.")
    return redirect(url_for('manage_award'))

@app.route('/award')
def award():
    conn = get_db_connection()

    awards = conn.execute("""
        SELECT * FROM award_events
        ORDER BY date DESC, time DESC
    """).fetchall()

    ranking_rows = conn.execute("""
        SELECT
            substr(collection_date, 1, 4) AS year,
            resident_username,
            SUM(weight) AS total
        FROM recycling_records
        GROUP BY substr(collection_date, 1, 4), resident_username
        ORDER BY year DESC, total DESC
    """).fetchall()

    conn.close()

    rankings_by_year = {}
    for row in ranking_rows:
        year = str(row["year"])
        if year not in rankings_by_year:
            rankings_by_year[year] = []

        rankings_by_year[year].append({
            "username": row["resident_username"],
            "total": float(row["total"]),
            "year": int(row["year"])
        })

    user = get_current_user()

    return render_template(
        'award.html',
        awards=awards,
        rankings_by_year=rankings_by_year,
        current_username=user["username"] if user else ""
    )


@app.route("/generate", methods=["POST"])
def generate_certificate():
    name = request.form.get("name", "").strip()
    programme = request.form.get("programme", "").strip()
    location = request.form.get("location", "").strip()
    date_input = request.form.get("date", "").strip()
    remarks = request.form.get("remarks", "").strip()

    if not name or not programme or not location or not date_input:
        flash("Please fill in all required certificate fields.")
        return redirect("/generate_certificate")

    # 日期格式处理
    try:
        formatted_date = datetime.strptime(date_input, "%Y-%m-%d").strftime("%d %B %Y")
    except ValueError:
        flash("Invalid certificate date.")
        return redirect("/generate_certificate")

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    try:
                # 先插入一笔临时记录，让 SQLite 自动给 id
                c.execute("""
                    INSERT INTO certificates (cert_id, name, programme, location, date, remarks)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, ("TEMP", name, programme, location, formatted_date, remarks))

                new_id = c.lastrowid
                cert_id = f"GT2026-{new_id:04d}"

                # 再更新真正的 cert_id
                c.execute("""
                    UPDATE certificates
                    SET cert_id = ?
                    WHERE id = ?
                """, (cert_id, new_id))

                conn.commit()

    except sqlite3.IntegrityError:
                conn.rollback()
                conn.close()
                flash("Certificate ID conflict. Please try again.")
                return redirect("/generate_certificate")

    conn.close()

            # 生成 QR
    generate_qr(cert_id)

    return render_template(
                "certificate_result.html",
                cert_id=cert_id,
                name=name,
                programme=programme,
                location=location,
                formatted_date=formatted_date,
                remarks=remarks
            )

@app.route("/generate_certificate")
def generate_certificate_page():
    return render_template("generate_certificate.html")

# =========================
# 生成 QR
# =========================
def generate_qr(cert_id):
    base_url = "https://prance-excavator-unlivable.ngrok-free.dev"
    url = f"{base_url}/verify/{cert_id}"

    if not os.path.exists("qr_codes"):
        os.makedirs("qr_codes")

    path = f"qr_codes/{cert_id}.png"
    img = qrcode.make(url)
    img.save(path)

    return path


# =========================
# 显示 QR 图片
# =========================
@app.route("/qr/<cert_id>")
def show_qr(cert_id):
    path = f"qr_codes/{cert_id}.png"
    if not os.path.exists(path):
        abort(404)
    return send_file(path, mimetype="image/png")


# =========================
# 验证证书
# =========================
@app.route("/verify/<cert_id>")
def verify(cert_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("SELECT * FROM certificates WHERE cert_id = ?", (cert_id,))
    result = c.fetchone()
    conn.close()

    if result:
        return render_template(
        "certificate_verify.html",
        cert_id=result[1],
        name=result[2],
        programme=result[3],
        location=result[4],
        date=result[5],
        remarks=result[6] if len(result) > 6 and result[6] else ""
    )

    return render_template("certificate_invalid.html")


# =========================
# 下载 PDF
# =========================
@app.route("/download/<cert_id>")
def download(cert_id):
    pdf_path = generate_pdf(cert_id)
    return send_file(pdf_path, as_attachment=True)


# =========================
# 生成 PDF
# =========================
def generate_pdf(cert_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("SELECT * FROM certificates WHERE cert_id=?", (cert_id,))
    result = c.fetchone()
    conn.close()

    if not result:
        abort(404)

    name = result[2]
    programme = result[3]
    location = result[4]
    date = result[5]
    remarks = result[6] if len(result) > 6 and result[6] else ""

    if not os.path.exists("pdf"):
        os.makedirs("pdf")

    pdf_path = f"pdf/{cert_id}.pdf"
    pdf_canvas = canvas.Canvas(pdf_path, pagesize=A4)

    width, height = A4

    # =========================
    # Border（官方双框）
    # =========================
    pdf_canvas.setLineWidth(3)
    pdf_canvas.rect(40, 40, width - 80, height - 80)

    pdf_canvas.setLineWidth(1)
    pdf_canvas.rect(55, 55, width - 110, height - 110)

    # =========================
    # LOGO（正中上方）
    # =========================
    logo_path = os.path.join("images", "today_logoo.png")

    logo_size = 65
    logo_x = width / 2 - (logo_size / 2)
    logo_y = 725

    if os.path.exists(logo_path):
        pdf_canvas.drawImage(
            logo_path,
            logo_x,
            logo_y,
            width=logo_size,
            height=logo_size,
            mask="auto"
        )

    # =========================
    # TITLE（完全居中）
    # =========================
    pdf_canvas.setFont("Helvetica-Bold", 30)
    pdf_canvas.drawCentredString(width / 2, 710, "CERTIFICATE")

    pdf_canvas.setFont("Helvetica", 14)
    pdf_canvas.drawCentredString(width / 2, 680, "GreenTrack Recycling Recognition")

    # =========================
    # 内容
    # =========================
    pdf_canvas.setFont("Helvetica", 13)
    pdf_canvas.drawCentredString(width / 2, 625, "This certificate is proudly presented to")

    # Name（重点）
    pdf_canvas.setFont("Helvetica-Bold", 26)
    pdf_canvas.drawCentredString(width / 2, 585, name)

    pdf_canvas.setFont("Helvetica", 13)
    pdf_canvas.drawCentredString(width / 2, 550, "for participation in the")

    pdf_canvas.setFont("Helvetica-Bold", 16)
    pdf_canvas.drawCentredString(width / 2, 515, programme)

    # =========================
    # Details
    # =========================
    pdf_canvas.setFont("Helvetica", 12)
    pdf_canvas.drawCentredString(width / 2, 475, f"Location: {location}")
    pdf_canvas.drawCentredString(width / 2, 450, f"Date: {date}")

    if remarks:
        pdf_canvas.setFont("Helvetica-Oblique", 11)
        pdf_canvas.drawCentredString(width / 2, 425, f"Remarks: {remarks}")

    # =========================
    # QR Code
    # =========================
    qr_path = f"qr_codes/{cert_id}.png"
    if os.path.exists(qr_path):
        pdf_canvas.drawImage(qr_path, width/2 - 60, 300, width=120, height=120)

    # =========================
    # Verification text
    # =========================
    pdf_canvas.setFont("Helvetica-Bold", 11)
    pdf_canvas.drawCentredString(width / 2, 280, f"Certificate ID: {cert_id}")

    pdf_canvas.setFont("Helvetica", 10)
    pdf_canvas.drawCentredString(width / 2, 265, "Scan the QR code to verify this certificate.")

    # =========================
    # Signature（政府风）
    # =========================
    pdf_canvas.line(width/2 - 100, 170, width/2 + 100, 170)

    pdf_canvas.setFont("Helvetica-Oblique", 14)
    pdf_canvas.drawCentredString(width / 2, 190, "Vincent Ting")

    pdf_canvas.setFont("Helvetica-Bold", 11)
    pdf_canvas.drawCentredString(width / 2, 150, "Authorized Officer")

    pdf_canvas.setFont("Helvetica", 10)
    pdf_canvas.drawCentredString(width / 2, 135, "GreenTrack Recycling Programme")

    pdf_canvas.save()
    return pdf_path

def init_ranking_table():
    conn = get_db_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS recycling_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            resident_username TEXT NOT NULL,
            merchant_username TEXT NOT NULL,
            item_type TEXT NOT NULL,
            weight REAL NOT NULL,
            price_per_kg REAL NOT NULL,
            total_amount REAL NOT NULL,
            location TEXT NOT NULL,
            collection_date TEXT NOT NULL,
            collection_time TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()



@app.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "GET":
        return render_template("forgot_password.html")

    email = request.form.get("email", "").strip()

    if not email:
        flash("Please enter your email.")
        return redirect(url_for("forgot_password"))

    conn = get_db_connection()
    user = conn.execute(
        "SELECT * FROM users WHERE email = ?",
        (email,)
    ).fetchone()

    if not user:
        conn.close()
        flash("Email not found.")
        return redirect(url_for("forgot_password"))

    code = str(random.randint(1000, 9999))

    # 存进 reset_logs 数据表
    conn.execute("""
        INSERT INTO reset_logs (email, code, requested_at)
        VALUES (?, ?, ?)
    """, (email, code, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

    session["reset_email"] = email
    session["reset_code"] = code
    session["reset_verified"] = False

    print("\n\n===================================")
    print(f"[RESET CODE] {email} -> {code}")
    print("===================================\n\n")

    flash(f"Verification code sent. Demo code: {code}")
    return redirect(url_for("verify_code"))

@app.route("/delete_reset_log/<int:log_id>")
def delete_reset_log(log_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM reset_logs WHERE id = ?", (log_id,))
    conn.commit()
    conn.close()

    flash("Log deleted successfully.")
    return redirect(url_for("admin_reset_logs"))


@app.route("/verify_code", methods=["GET", "POST"])
def verify_code():
    if "reset_email" not in session:
        flash("Please request a verification code first.")
        return redirect(url_for("forgot_password"))

    if request.method == "GET":
        return render_template("verify_code.html")

    input_code = request.form.get("code", "").strip()
    saved_code = session.get("reset_code")

    if not input_code:
        flash("Please enter the verification code.")
        return redirect(url_for("verify_code"))

    if input_code != saved_code:
        flash("Wrong code. Try again.")
        return redirect(url_for("verify_code"))

    session["reset_verified"] = True
    flash("Code verified successfully. Please reset your password.")
    return redirect(url_for("reset_password"))

@app.route("/reset_password", methods=["GET", "POST"])
def reset_password():
    if "reset_email" not in session:
        flash("Please request password reset first.")
        return redirect(url_for("forgot_password"))

    if not session.get("reset_verified"):
        flash("Please verify your code first.")
        return redirect(url_for("verify_code"))

    if request.method == "GET":
        return render_template("reset_password.html")

    password = request.form.get("password", "").strip()
    confirm_password = request.form.get("confirm_password", "").strip()

    if not password or not confirm_password:
        flash("Please fill in all fields.")
        return redirect(url_for("reset_password"))

    if password != confirm_password:
        flash("Passwords do not match.")
        return redirect(url_for("reset_password"))

    import re
    if len(password) < 8:
        flash("Password must be at least 8 characters.")
        return redirect(url_for("reset_password"))
    if not re.search(r"[A-Z]", password):
        flash("Password must contain at least 1 uppercase letter.")
        return redirect(url_for("reset_password"))
    if not re.search(r"[a-z]", password):
        flash("Password must contain at least 1 lowercase letter.")
        return redirect(url_for("reset_password"))
    if not re.search(r"[0-9]", password):
        flash("Password must contain at least 1 number.")
        return redirect(url_for("reset_password"))
    if not re.search(r"[#\$%&\*_\+\-/!@]", password):
        flash("Password must contain at least 1 special symbol.")
        return redirect(url_for("reset_password"))

    hashed_password = generate_password_hash(password)

    conn = get_db_connection()
    conn.execute(
        "UPDATE users SET password = ? WHERE email = ?",
        (hashed_password, session["reset_email"])
    )
    conn.commit()
    conn.close()

    session.pop("reset_email", None)
    session.pop("reset_code", None)
    session.pop("reset_verified", None)

    return render_template("reset_pass_success.html")

@app.route("/create_merchant", methods=["POST"])
def create_merchant():
    user = get_current_user()
    if not user or user["role"] != "superadmin":
        flash("Access denied. Super Admin only.")
        return redirect(url_for("login"))

    company_name = request.form.get("company_name", "").strip()
    email = request.form.get("email", "").strip()
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()

    if not company_name or not email or not username or not password:
        flash("Please fill in all required merchant fields.")
        return redirect("/admin_create_merchant")

    import re
    if len(password) < 8:
        flash("Password must be at least 8 characters.")
        return redirect("/admin_create_merchant")
    if not re.search(r"[A-Z]", password):
        flash("Password must contain at least 1 uppercase letter.")
        return redirect("/admin_create_merchant")
    if not re.search(r"[a-z]", password):
        flash("Password must contain at least 1 lowercase letter.")
        return redirect("/admin_create_merchant")
    if not re.search(r"[0-9]", password):
        flash("Password must contain at least 1 number.")
        return redirect("/admin_create_merchant")

    conn = get_db_connection()

    existing_merchant = conn.execute(
        "SELECT * FROM users WHERE role = ?",
        ("merchant",)
    ).fetchone()

    if existing_merchant:
        conn.close()
        flash("Only ONE merchant account is allowed in this system.")
        return redirect("/admin_create_merchant")

    existing_user = conn.execute(
        "SELECT * FROM users WHERE username = ? OR email = ?",
        (username, email)
    ).fetchone()

    if existing_user:
        conn.close()
        flash("Username or email already exists.")
        return redirect("/admin_create_merchant")

    hashed_password = generate_password_hash(password)

    conn.execute("""
        INSERT INTO users (username, email, password, role, company_name)
        VALUES (?, ?, ?, ?, ?)
    """, (username, email, hashed_password, "merchant", company_name))

    conn.commit()
    conn.close()

    flash(f"Merchant account created successfully for {company_name}.")
    return redirect("/superadmin_dashboard")

@app.route("/reset_success")
def reset_success():
    return render_template("reset_pass_success.html")

@app.route("/create_officer", methods=["POST"])
def create_officer():
    user = get_current_user()
    if not user or user["role"] != "superadmin":
        flash("Access denied. Super Admin only.")
        return redirect(url_for("login"))

    name = request.form.get("name", "").strip()
    department = request.form.get("department", "").strip()
    contact = request.form.get("contact", "").strip()
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()
    confirm_password = request.form.get("confirm_password", "").strip()

    if not name or not department or not contact or not username or not password or not confirm_password:
        flash("Please fill in all required officer fields.")
        return redirect("/admin_create_officer")

    if password != confirm_password:
        flash("Passwords do not match.")
        return redirect("/admin_create_officer")

    import re
    if len(password) < 8:
        flash("Password must be at least 8 characters.")
        return redirect("/admin_create_officer")
    if not re.search(r"[A-Z]", password):
        flash("Password must contain at least 1 uppercase letter.")
        return redirect("/admin_create_officer")
    if not re.search(r"[a-z]", password):
        flash("Password must contain at least 1 lowercase letter.")
        return redirect("/admin_create_officer")
    if not re.search(r"[0-9]", password):
        flash("Password must contain at least 1 number.")
        return redirect("/admin_create_officer")
    if not re.search(r"[#\$%&\*_\+\-/!@]", password):
        flash("Password must contain at least 1 special symbol.")
        return redirect("/admin_create_officer")

    conn = get_db_connection()

    existing_officer = conn.execute(
        "SELECT * FROM users WHERE role = ?",
        ("officer",)
    ).fetchone()

    if existing_officer:
        conn.close()
        flash("Only ONE officer account is allowed in this system.")
        return redirect("/admin_create_officer")

    fake_email = f"{username}@officer.local"

    existing_user = conn.execute(
        "SELECT * FROM users WHERE username = ? OR email = ?",
        (username, fake_email)
    ).fetchone()

    if existing_user:
        conn.close()
        flash("Username already exists.")
        return redirect("/admin_create_officer")

    hashed_password = generate_password_hash(password)

    conn.execute("""
        INSERT INTO users (username, email, password, role, officer_name, department, contact)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (username, fake_email, hashed_password, "officer", name, department, contact))

    conn.commit()
    conn.close()

    flash(f"Officer account created successfully for {name}.")
    return redirect("/superadmin_dashboard")

@app.route("/login_as/<role>")
def login_as(role):
    user = get_current_user()

    # 只允许 superadmin 用这个功能
    if not user or user["role"] != "superadmin":
        flash("Access denied.")
        return redirect(url_for("login"))

    conn = get_db_connection()

    target_user = conn.execute(
        "SELECT * FROM users WHERE role = ?",
        (role,)
    ).fetchone()

    conn.close()

    if not target_user:
        flash(f"No {role} account found.")
        return redirect("/superadmin_dashboard")

    # 切换 session
    session["user_id"] = target_user["id"]
    session["username"] = target_user["username"]
    session["role"] = target_user["role"]

    flash(f"Now logged in as {role}")

    # 跳去对应 dashboard
    if role == "merchant":
     return redirect("/merchant_dashboard")
    elif role == "officer":
     return redirect("/officer_dashboard")

@app.route("/api/ranking_data")
def ranking_data():
    user = get_current_user()

    conn = get_db_connection()
    rows = conn.execute("""
        SELECT 
            r.resident_username,
            r.weight,
            r.collection_date
        FROM recycling_records r
        INNER JOIN users u
            ON r.resident_username = u.username
        WHERE u.role = 'resident'
        ORDER BY r.collection_date DESC, r.id DESC
    """).fetchall()
    conn.close()

    result = []

    for row in rows:
        date_text = row["collection_date"]  # example: 2026-04-28
        year = int(date_text.split("-")[0])
        month = int(date_text.split("-")[1])

        result.append({
            "username": row["resident_username"],
            "weight": float(row["weight"]),
            "count": 1,
            "year": year,
            "month": month
        })

    return jsonify({
        "success": True,
        "current_user": user["username"] if user else "",
        "current_role": user["role"] if user else "",
        "records": result
    })

@app.route("/api/add_record", methods=["POST"])
def add_record():
    data = request.json

    resident = data.get("resident_username", "").strip()
    item = data.get("item_type", "").strip()
    location = data.get("location", "").strip()
    collection_date = data.get("collection_date", "").strip()
    collection_time = data.get("collection_time", "").strip()

    try:
        weight = float(data.get("weight", 0))
        price = float(data.get("price_per_kg", 0))
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Invalid weight or price."}), 400

    if not resident or not item or not location or not collection_date or not collection_time:
        return jsonify({"success": False, "message": "Missing required fields."}), 400

    conn = get_db_connection()

    resident_user = conn.execute(
        "SELECT * FROM users WHERE username = ? AND role = ?",
        (resident, "resident")
    ).fetchone()

    if not resident_user:
        conn.close()
        return jsonify({"success": False, "message": "Resident username not found."}), 404

    merchant = session.get("username", "merchant")
    total = weight * price
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn.execute("""
        INSERT INTO recycling_records (
            resident_username,
            merchant_username,
            item_type,
            weight,
            price_per_kg,
            total_amount,
            location,
            collection_date,
            collection_time,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        resident,
        merchant,
        item,
        weight,
        price,
        total,
        location,
        collection_date,
        collection_time,
        now
    ))

    conn.commit()
    conn.close()

    return jsonify({"success": True})

@app.route("/api/recycling_records")
def api_recycling_records():
    conn = get_db_connection()
    rows = conn.execute("""
        SELECT *
        FROM recycling_records
        ORDER BY id DESC
    """).fetchall()
    conn.close()

    data = []
    for row in rows:
        data.append({
            "id": row["id"],
            "resident_username": row["resident_username"],
            "merchant_username": row["merchant_username"],
            "item_type": row["item_type"],
            "weight": row["weight"],
            "price_per_kg": row["price_per_kg"],
            "total_amount": row["total_amount"],
            "location": row["location"],
            "collection_date": row["collection_date"],
            "collection_time": row["collection_time"],
            "created_at": row["created_at"]
        })

    return jsonify(data)

@app.route("/api/delete_recycling_record/<int:record_id>", methods=["DELETE"])
def delete_recycling_record(record_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM recycling_records WHERE id = ?", (record_id,))
    conn.commit()
    conn.close()

    return jsonify({"success": True})

@app.route("/api/monthly_summary_data")
def api_monthly_summary_data():
    user = get_current_user()

    if not user:
        return jsonify({"success": False, "message": "Please log in first."}), 401

    conn = get_db_connection()
    rows = conn.execute("""
        SELECT resident_username, collection_date, weight
        FROM recycling_records
        ORDER BY collection_date DESC, id DESC
    """).fetchall()
    conn.close()

    records = []
    for row in rows:
        date_text = row["collection_date"]  # 例如 2026-04-22
        year = int(date_text.split("-")[0])
        month = int(date_text.split("-")[1])

        records.append({
            "username": row["resident_username"],
            "year": year,
            "month": month,
            "weight": float(row["weight"]),
            "count": 1
        })

    return jsonify({
        "success": True,
        "current_user": user["username"],
        "records": records
    })

@app.route("/api/user_dashboard_data")
def api_user_dashboard_data():
    user = get_current_user()

    if not user:
        return jsonify({"success": False, "message": "Please log in first."}), 401

    username = user["username"]

    conn = get_db_connection()

    rows = conn.execute("""
        SELECT resident_username, item_type, weight, collection_date, collection_time
        FROM recycling_records
        WHERE resident_username = ?
        ORDER BY collection_date DESC, collection_time DESC, id DESC
    """, (username,)).fetchall()

    all_rows = conn.execute("""
        SELECT resident_username, weight, collection_date
        FROM recycling_records
    """).fetchall()

    conn.close()

    records = []
    for row in rows:
        records.append({
            "item_type": row["item_type"],
            "weight": float(row["weight"]),
            "collection_date": row["collection_date"],
            "collection_time": row["collection_time"]
        })

    total_weight = sum(r["weight"] for r in records)
    participation_count = len(records)

    active_months = len(set(
        f"{r['collection_date'][:7]}" for r in records
    ))

    latest_contribution = None
    if records:
        latest_contribution = {
            "weight": records[0]["weight"],
            "item_type": records[0]["item_type"]
        }

    # 算 overall rank
    grouped = {}
    for row in all_rows:
        name = row["resident_username"]
        grouped[name] = grouped.get(name, 0) + float(row["weight"])

    sorted_users = sorted(grouped.items(), key=lambda x: x[1], reverse=True)

    community_rank = None
    for index, item in enumerate(sorted_users, start=1):
        if item[0] == username:
            community_rank = index
            break

    return jsonify({
        "success": True,
        "username": username,
        "total_weight": round(total_weight, 1),
        "participation_count": participation_count,
        "active_months": active_months,
        "latest_contribution": latest_contribution,
        "community_rank": community_rank,
        "recent_activity": records[:5]
    })

@app.route("/api/user_events")
def api_user_events():
    conn = get_db_connection()
    rows = conn.execute("""
        SELECT *
        FROM events
        ORDER BY pinned DESC, date DESC, start_time DESC, id DESC
    """).fetchall()
    conn.close()

    events = []
    for row in rows:
        events.append({
            "id": row["id"],
            "title": row["title"],
            "date": row["date"],
            "time": row["start_time"],   # ⚠️ 前端用 time
            "location": row["location"],
            "description": row["description"],
            "pinned": bool(row["pinned"])
        })

    return jsonify({
        "success": True,
        "events": events
    })

@app.route("/api/officer_dashboard_data")
def api_officer_dashboard_data():
    user = get_current_user()

    if not user:
        return jsonify({"success": False, "message": "Please log in first."}), 401

    conn = get_db_connection()

    rows = conn.execute("""
        SELECT resident_username, merchant_username, weight, collection_date
        FROM recycling_records
        ORDER BY collection_date DESC, id DESC
    """).fetchall()

    merchants = conn.execute("""
        SELECT COUNT(*) AS total
        FROM users
        WHERE role = 'merchant'
    """).fetchone()

    total_residents = conn.execute("""
        SELECT COUNT(*) AS total
        FROM users
        WHERE role = 'resident'
    """).fetchone()

    conn.close()

    total_recycled_month = 0.0
    latest_reporting_month = "-"
    grouped = {}

    if rows:
        latest_date = rows[0]["collection_date"]
        latest_month = latest_date[:7]
        latest_reporting_month = datetime.strptime(latest_date, "%Y-%m-%d").strftime("%B %Y")

        for row in rows:
            grouped[row["resident_username"]] = grouped.get(row["resident_username"], 0) + float(row["weight"])

            if row["collection_date"].startswith(latest_month):
                total_recycled_month += float(row["weight"])

    top_recycler_text = "-"
    if grouped:
        top_user, top_weight = sorted(grouped.items(), key=lambda x: x[1], reverse=True)[0]
        top_recycler_text = f"{top_user} ({top_weight:.1f} kg)"

    return jsonify({
        "success": True,
        "username": user["username"],
        "total_recycled_month": round(total_recycled_month, 1),
        "active_merchants": merchants["total"] if merchants else 0,
        "total_participants": total_residents["total"] if total_residents else 0,
        "latest_reporting_month": latest_reporting_month,
        "top_recycler_text": top_recycler_text
    })
def init_events_table():
    conn = get_db_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            date TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            location TEXT NOT NULL,
            description TEXT NOT NULL,
            pinned INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

@app.route("/api/events")
def api_events():
    conn = get_db_connection()
    rows = conn.execute("""
        SELECT *
        FROM events
        ORDER BY pinned DESC, date DESC, start_time DESC, id DESC
    """).fetchall()
    conn.close()

    events = []
    for row in rows:
        events.append({
            "id": row["id"],
            "title": row["title"],
            "date": row["date"],
            "startTime": row["start_time"],
            "endTime": row["end_time"],
            "location": row["location"],
            "desc": row["description"],
            "pinned": bool(row["pinned"])
        })

    return jsonify({"success": True, "events": events})

@app.route("/api/save_event", methods=["POST"])
def api_save_event():
    data = request.json or {}

    event_id = data.get("id")
    title = (data.get("title") or "").strip()
    date = (data.get("date") or "").strip()
    start_time = (data.get("startTime") or "").strip()
    end_time = (data.get("endTime") or "").strip()
    location = (data.get("location") or "").strip()
    desc = (data.get("desc") or "").strip()
    pinned = 1 if data.get("pinned") else 0

    if not title or not date or not start_time or not end_time or not location or not desc:
        return jsonify({"success": False, "message": "Please fill in all fields."}), 400

    if start_time >= end_time:
        return jsonify({"success": False, "message": "End time must be later than start time."}), 400

    conn = get_db_connection()

    if event_id:
        conn.execute("""
            UPDATE events
            SET title = ?, date = ?, start_time = ?, end_time = ?, location = ?, description = ?, pinned = ?
            WHERE id = ?
        """, (title, date, start_time, end_time, location, desc, pinned, event_id))
    else:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn.execute("""
            INSERT INTO events (title, date, start_time, end_time, location, description, pinned, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (title, date, start_time, end_time, location, desc, pinned, now))

    conn.commit()
    conn.close()

    return jsonify({"success": True})

@app.route("/api/toggle_event_pin/<int:event_id>", methods=["POST"])
def api_toggle_event_pin(event_id):
    conn = get_db_connection()
    row = conn.execute("SELECT pinned FROM events WHERE id = ?", (event_id,)).fetchone()

    if not row:
        conn.close()
        return jsonify({"success": False, "message": "Event not found."}), 404

    new_pinned = 0 if row["pinned"] else 1

    conn.execute("UPDATE events SET pinned = ? WHERE id = ?", (new_pinned, event_id))
    conn.commit()
    conn.close()

    return jsonify({"success": True, "pinned": bool(new_pinned)})

@app.route("/api/delete_event/<int:event_id>", methods=["DELETE"])
def api_delete_event(event_id):
    conn = get_db_connection()

    row = conn.execute(
        "SELECT id FROM events WHERE id = ?",
        (event_id,)
    ).fetchone()

    if not row:
        conn.close()
        return jsonify({"success": False, "message": "Event not found."}), 404

    conn.execute("DELETE FROM events WHERE id = ?", (event_id,))
    conn.commit()
    conn.close()

    return jsonify({"success": True})

@app.route("/api/user_list_data")
def api_user_list_data():
    user = get_current_user()

    if not user:
        return jsonify({"success": False, "message": "Please log in first."}), 401

    conn = get_db_connection()

    users = conn.execute("""
    SELECT id, username, email, role, last_login, last_logout, is_logged_in
    FROM users
    WHERE role = 'resident'
    ORDER BY username ASC
    """).fetchall()

    rows = conn.execute("""
        SELECT resident_username, weight, collection_date
        FROM recycling_records
        ORDER BY collection_date DESC, id DESC
    """).fetchall()

    conn.close()

    yearly_data = {}
    all_years = set()

    month_map = {
        1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr",
        5: "May", 6: "Jun", 7: "Jul", 8: "Aug",
        9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"
    }

    for row in rows:
        username = row["resident_username"]
        date_text = row["collection_date"]   # 例如 2026-04-22
        year = date_text[:4]
        month_num = int(date_text[5:7])
        month_name = month_map[month_num]
        weight = float(row["weight"])

        all_years.add(year)

        if username not in yearly_data:
            yearly_data[username] = {}

        if year not in yearly_data[username]:
            yearly_data[username][year] = {m: 0.0 for m in month_map.values()}

        yearly_data[username][year][month_name] += weight

    result_users = []
    for u in users:
        result_users.append({
        "username": u["username"],
        "email": u["email"],
        "role": u["role"],
        "lastLogin": u["last_login"] or "-",
        "lastLogout": u["last_logout"] or "-",
        "isLoggedIn": bool(u["is_logged_in"]),
        "data": yearly_data.get(u["username"], {})
     })

    if not all_years:
        all_years.add(str(datetime.now().year))

    return jsonify({
        "success": True,
        "users": result_users,
        "years": sorted(list(all_years))
    })

@app.route("/api/superadmin_overview")
def api_superadmin_overview():
    user = get_current_user()

    if not user or user["role"] != "superadmin":
        return jsonify({"success": False, "message": "Access denied"}), 403

    conn = get_db_connection()

    total_residents = conn.execute(
        "SELECT COUNT(*) AS total FROM users WHERE role = 'resident'"
    ).fetchone()["total"]

    total_merchants = conn.execute(
        "SELECT COUNT(*) AS total FROM users WHERE role = 'merchant'"
    ).fetchone()["total"]

    total_officers = conn.execute(
        "SELECT COUNT(*) AS total FROM users WHERE role = 'officer'"
    ).fetchone()["total"]

    conn.close()

    return jsonify({
        "success": True,
        "total_residents": total_residents,
        "total_merchants": total_merchants,
        "total_officers": total_officers,
        "system_status": "Active"
    })

@app.route("/logout")
def logout():
    user_id = session.get("user_id")

    if user_id:
        conn = get_db_connection()
        conn.execute("""
            UPDATE users
            SET last_logout = ?, is_logged_in = 0
            WHERE id = ?
        """, (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_id))
        conn.commit()
        conn.close()

    session.clear()
    return redirect(url_for("login"))

@app.route("/price_estimate")
def price_estimate():
    user = get_current_user()

    if user:
        role = user["role"]

        if role == "superadmin":
            back_url = "/superadmin_dashboard"
        elif role == "merchant":
            back_url = "/merchant_dashboard"
        elif role == "officer":
            back_url = "/officer_dashboard"
        else:
            back_url = "/user_dashboard"

        back_label = "← Back to Dashboard"
        header_mode = f"Logged in as {user['username']}"
        header_submode = f"Role: {role}"
    else:
        back_url = "/"
        back_label = "← Back to Home"
        header_mode = "Public Visitor"
        header_submode = "Reference Information Page"

    return render_template(
        "price_estimate.html",
        back_url=back_url,
        back_label=back_label,
        header_mode=header_mode,
        header_submode=header_submode
    )

@app.route("/api/online_users")
def api_online_users():
    user = get_current_user()

    if not user or user["role"] not in ["superadmin", "officer"]:
        return jsonify({"success": False, "message": "Access denied"}), 403

    conn = get_db_connection()

    rows = conn.execute("""
        SELECT username, email, role, last_login, last_logout, is_logged_in
        FROM users
        ORDER BY is_logged_in DESC, last_login DESC
    """).fetchall()

    conn.close()

    users = []
    for row in rows:
        users.append({
            "username": row["username"],
            "email": row["email"],
            "role": row["role"],
            "last_login": row["last_login"] or "-",
            "last_logout": row["last_logout"] or "-",
            "is_logged_in": row["is_logged_in"]
        })

    online_count = sum(1 for u in users if u["is_logged_in"] == 1)
    offline_count = len(users) - online_count

    return jsonify({
        "success": True,
        "users": users,
        "online_count": online_count,
        "offline_count": offline_count,
        "current_user": user["username"]
    })

@app.route("/online_users")
def online_users_page():
    user = get_current_user()

    if not user or user["role"] not in ["superadmin", "officer"]:
        flash("Access denied.")
        return redirect("/login")

    return render_template("online_users.html")

@app.route("/api/residents")
def api_residents():
    conn = get_db_connection()

    rows = conn.execute("""
        SELECT username
        FROM users
        WHERE role = 'resident'
        ORDER BY username ASC
    """).fetchall()

    conn.close()

    return jsonify({
        "success": True,
        "residents": [row["username"] for row in rows]
    })



@app.route("/api/my_certificates")
def my_certificates():
    user = get_current_user()

    if not user:
        return jsonify({"success": False}), 401

    username = user["username"]

    conn = get_db_connection()

    rows = conn.execute("""
        SELECT cert_id, programme, location, date
        FROM certificates
        WHERE name = ?
        ORDER BY id DESC
    """, (username,)).fetchall()

    conn.close()

    result = []

    for row in rows:
        result.append({
            "cert_id": row["cert_id"],
            "programme": row["programme"],
            "location": row["location"],
            "date": row["date"]
        })

    return jsonify({
        "success": True,
        "certificates": result
    })


if __name__ == "__main__":
    init_db()
    init_users_table()
    init_reset_logs_table()
    init_superadmin()
    init_award_table()
    init_ranking_table()
    init_events_table()
    app.run(host="0.0.0.0", port=5000, debug=True)