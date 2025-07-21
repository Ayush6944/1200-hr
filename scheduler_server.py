import time
import subprocess
from datetime import datetime, timedelta
import pytz
import threading
from flask import Flask, send_file, request, redirect, url_for, session, render_template_string
import os
import requests
from typing import Optional

# ===================== CONFIGURATION =====================
SCHEDULE_HOUR = 11  # 10 AM (used after first run)
SCHEDULE_MINUTE = 20  # 20 minutes (used after first run)
IST = pytz.timezone('Asia/Kolkata')
LOG_FILE = 'scheduler_audit.log'
LOGIN_LOG_FILE = 'login_audit.log'
SECRET_KEY = 'supersecretkey'  # Change this in production
USERNAME = 'admin'
PASSWORD = 'ayush'
# ========================================================

app = Flask(__name__)
app.secret_key = SECRET_KEY

last_run_info: dict[str, Optional[str]] = {'start': None, 'end': None, 'error': None}

def log_login_event(username, success):
    with open(LOGIN_LOG_FILE, 'a', encoding='utf-8') as f:
        status = 'SUCCESS' if success else 'FAIL'
        f.write(f"{datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S')} - {username} - {status}\n")

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == USERNAME and password == PASSWORD:
            session['logged_in'] = True
            session['username'] = username
            log_login_event(username, True)
            # Show Kali OS-style animation before redirect
            return render_template_string('''
            <html>
            <head>
                <title>Logging In...</title>
                <style>
                    body { background: #181c20; color: #39ff14; margin: 0; height: 100vh; overflow: hidden; }
                    .terminal {
                        font-family: 'Fira Mono', 'Consolas', monospace;
                        background: #181c20;
                        color: #39ff14;
                        width: 100vw;
                        height: 100vh;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        flex-direction: column;
                        font-size: 1.3em;
                    }
                    .blink {
                        animation: blink 1s steps(2, start) infinite;
                    }
                    @keyframes blink {
                        to { visibility: hidden; }
                    }
                </style>
                <script>
                    let lines = [
                        'Welcome, {{ username }}',
                        'Initializing secure session...',
                        'Loading dashboard modules...',
                        'Access granted. Redirecting...'
                    ];
                    let idx = 0;
                    function typeLine() {
                        if (idx < lines.length) {
                            let term = document.getElementById('term');
                            let p = document.createElement('div');
                            p.textContent = lines[idx];
                            term.appendChild(p);
                            idx++;
                            setTimeout(typeLine, 900);
                        } else {
                            setTimeout(function() { window.location = "/"; }, 1200);
                        }
                    }
                    window.onload = typeLine;
                </script>
            </head>
            <body>
                <div class="terminal" id="term">
                    <span class="blink">root@hr-emailer:~#</span>
                </div>
            </body>
            </html>
            ''', username=username)
        else:
            log_login_event(username or '', False)
            error = 'Invalid username or password.'
    return render_template_string('''
    <html>
    <head>
        <title>Login - Email Campaign Scheduler</title>
        <style>
            body { font-family: Arial, sans-serif; background: #181c20; }
            .login-container {
                max-width: 350px; margin: 6em auto; background: #23272e;
                border-radius: 10px; box-shadow: 0 4px 24px rgba(44,62,80,0.18);
                padding: 2.5em 2.5em; text-align: center;
            }
            h2 { color: #39ff14; letter-spacing: 1px; }
            input[type=text], input[type=password] {
                width: 90%; padding: 0.7em; margin: 1em 0 1.5em 0; border: 1px solid #444; border-radius: 4px; background: #181c20; color: #39ff14;
            }
            button { background: linear-gradient(90deg, #39ff14 0%, #00c3ff 100%); color: #181c20; border: none; padding: 0.7em 2em; border-radius: 4px; font-size: 1em; cursor: pointer; font-weight: bold; }
            button:hover { background: #39ff14; color: #23272e; }
            .error { color: #e74c3c; margin-bottom: 1em; }
        </style>
    </head>
    <body>
        <div class="login-container">
            <h2>Login</h2>
            {% if error %}<div class="error">{{ error }}</div>{% endif %}
            <form method="post">
                <input type="text" name="username" placeholder="Username" required><br>
                <input type="password" name="password" placeholder="Password" required><br>
                <button type="submit">Login</button>
            </form>
        </div>
    </body>
    </html>
    ''', error=error)

@app.route('/logout', methods=['GET', 'POST'])
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/logged_out')
def logged_out():
    return render_template_string('''
    <html>
    <head>
        <title>Logged Out</title>
        <style>
            body { font-family: Arial, sans-serif; background: #f7f7f7; }
            .logout-container {
                max-width: 350px; margin: 6em auto; background: #fff;
                border-radius: 8px; box-shadow: 0 2px 8px rgba(44,62,80,0.08);
                padding: 2em 2.5em; text-align: center;
            }
            h2 { color: #2c3e50; }
            button { background: #2c3e50; color: #fff; border: none; padding: 0.7em 2em; border-radius: 4px; font-size: 1em; cursor: pointer; margin-top: 2em; }
            button:hover { background: #e74c3c; }
        </style>
        <script>
            function closeTab() {
                window.open('', '_self', '');
                window.close();
            }
        </script>
    </head>
    <body>
        <div class="logout-container">
            <h2>You have been logged out.</h2>
            <p>For your security, please close this tab.</p>
            <button onclick="closeTab()">Close Tab</button>
        </div>
    </body>
    </html>
    ''')

@app.route('/')
@login_required
def home():
    return render_template_string('''
    <html>
    <head>
        <title>Email Campaign Scheduler</title>
        <link href="https://fonts.googleapis.com/css?family=Fira+Mono:400,700&display=swap" rel="stylesheet">
        <style>
            body {
                font-family: 'Fira Mono', 'Consolas', monospace;
                background: linear-gradient(135deg, #181c20 0%, #23272e 100%);
                margin: 0;
                min-height: 100vh;
            }
            .navbar {
                background: #181c20;
                padding: 1.2em 2em;
                display: flex;
                align-items: center;
                box-shadow: 0 2px 8px rgba(44,62,80,0.18);
            }
            .navbar a {
                color: #39ff14;
                text-decoration: none;
                margin-right: 2em;
                font-weight: bold;
                font-size: 1.1em;
                transition: color 0.2s;
                letter-spacing: 1px;
            }
            .navbar a:hover {
                color: #00c3ff;
            }
            .container {
                max-width: 700px;
                margin: 4em auto;
                background: #23272e;
                border-radius: 12px;
                box-shadow: 0 4px 24px rgba(44,62,80,0.18);
                padding: 2.5em 2.5em;
                text-align: center;
                color: #fff;
            }
            h1 {
                color: #39ff14;
                font-size: 2.2em;
                margin-bottom: 0.5em;
            }
            p { color: #b2becd; }
            .logout-btn {
                float: right; background: #e74c3c; color: #fff; border: none; padding: 0.5em 1.2em; border-radius: 4px; cursor: pointer; margin-left: auto; font-weight: bold;
            }
            .logout-btn:hover { background: #c0392b; }
            .download-link {
                color: #00c3ff; text-decoration: underline; font-weight: bold;
            }
            .download-link:hover { color: #39ff14; }
            hr { border: 0; border-top: 1px solid #333; margin: 2em 0; }
            .footer { margin-top: 2em; color: #888; font-size: 0.95em; }
        </style>
    </head>
    <body>
        <div class="navbar">
            <a href="/">Home</a>
            <a href="/status">Status Log</a>
            <a href="/dashboard">Dashboard</a>
            <a href="/download_log">Download Log</a>
            <form action="/logout" method="get" style="margin-left:auto;display:inline;">
                <button class="logout-btn" type="submit">Logout</button>
            </form>
        </div>
        <div class="container">
            <h1>Welcome to the Email Campaign Scheduler</h1>
            <p>Use the navigation bar above to view campaign status, logs, and analytics.</p>
            <p style="color:#888; font-size:0.95em;">Server is running and ready to manage your automated email campaigns.</p>
            <hr>
            <p><b>Download your full email send log as a CSV file:</b><br>
            <a class="download-link" href="/download_log">Download send_log.csv</a></p>
            <div class="footer">
                <h4>Created By - Ayush Srivastava | <a href="https://portfolio-ayush6944s-projects.vercel.app/" style="color:#00c3ff;">Portfolio</a></h4>
            </div>
        </div>
    </body>
    </html>
    ''')

@app.route('/status')
@login_required
def status():
    log_lines = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            log_lines = f.readlines()[-10:]
    html = '''
    <html>
    <head>
        <title>Status Log - Email Campaign Scheduler</title>
        <link href="https://fonts.googleapis.com/css?family=Fira+Mono:400,700&display=swap" rel="stylesheet">
        <style>
            body {
                font-family: 'Fira Mono', 'Consolas', monospace;
                background: linear-gradient(135deg, #181c20 0%, #23272e 100%);
                margin: 0;
                min-height: 100vh;
            }
            .navbar {
                background: #181c20;
                padding: 1.2em 2em;
                display: flex;
                align-items: center;
                box-shadow: 0 2px 8px rgba(44,62,80,0.18);
            }
            .navbar a {
                color: #39ff14;
                text-decoration: none;
                margin-right: 2em;
                font-weight: bold;
                font-size: 1.1em;
                transition: color 0.2s;
                letter-spacing: 1px;
            }
            .navbar a:hover {
                color: #00c3ff;
            }
            .container {
                max-width: 700px;
                margin: 4em auto;
                background: #23272e;
                border-radius: 12px;
                box-shadow: 0 4px 24px rgba(44,62,80,0.18);
                padding: 2.5em 2.5em;
                color: #fff;
            }
            h1 {
                color: #39ff14;
                font-size: 2em;
                margin-bottom: 1em;
            }
            .log-card {
                background: #181c20;
                border-radius: 8px;
                box-shadow: 0 2px 8px rgba(44,62,80,0.18);
                padding: 1.5em 2em;
                margin: 2em 0;
                font-size: 1.1em;
                color: #00c3ff;
                min-height: 180px;
                white-space: pre-line;
            }
            .empty-log { color: #e74c3c; }
        </style>
    </head>
    <body>
        <div class="navbar">
            <a href="/">Home</a>
            <a href="/status">Status Log</a>
            <a href="/dashboard">Dashboard</a>
            <a href="/download_log">Download Log</a>
            <form action="/logout" method="get" style="margin-left:auto;display:inline;">
                <button class="logout-btn" type="submit">Logout</button>
            </form>
        </div>
        <div class="container">
            <h1>Status Log</h1>
            <div class="log-card">'''
    if log_lines:
        html += ''.join(line + '<br>' for line in log_lines)
    else:
        html += '<span class="empty-log">No audit log found.</span>'
    html += '''</div>
        </div>
    </body>
    </html>
    '''
    return html

@app.route('/dashboard')
@login_required
def dashboard():
    import sqlite3
    from datetime import datetime, timedelta
    db_path = os.path.join(os.path.dirname(__file__), 'data/companies.db')
    total_sent = 0
    total_pending = 0
    last_3_days = []
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            # Total sent
            cursor.execute("SELECT COUNT(*) FROM companies WHERE sent_timestamp IS NOT NULL")
            total_sent = cursor.fetchone()[0]
            # Total pending
            cursor.execute("SELECT COUNT(*) FROM companies WHERE sent_timestamp IS NULL")
            total_pending = cursor.fetchone()[0]
            # Last 3 days sent
            today = datetime.now().date()
            for i in range(3):
                day = today - timedelta(days=i)
                cursor.execute("SELECT COUNT(*) FROM companies WHERE date(sent_timestamp) = ?", (day.isoformat(),))
                count = cursor.fetchone()[0]
                last_3_days.append({'date': day.strftime('%Y-%m-%d'), 'count': count})
    except Exception as e:
        return f"<h2>Error loading dashboard: {e}</h2>"
    html = f"""
    <html>
    <head><title>Email Campaign Dashboard</title>
    <link href='https://fonts.googleapis.com/css?family=Fira+Mono:400,700&display=swap' rel='stylesheet'>
    <style>
        body {{
            font-family: 'Fira Mono', 'Consolas', monospace;
            background: linear-gradient(135deg, #181c20 0%, #23272e 100%);
            margin: 0;
            min-height: 100vh;
        }}
        .navbar {{
            background: #181c20;
            padding: 1.2em 2em;
            display: flex;
            align-items: center;
            box-shadow: 0 2px 8px rgba(44,62,80,0.18);
        }}
        .navbar a {{
            color: #39ff14;
            text-decoration: none;
            margin-right: 2em;
            font-weight: bold;
            font-size: 1.1em;
            transition: color 0.2s;
            letter-spacing: 1px;
        }}
        .navbar a:hover {{
            color: #00c3ff;
        }}
        .logout-btn {{
            float: right; background: #e74c3c; color: #fff; border: none; padding: 0.5em 1.2em; border-radius: 4px; cursor: pointer; margin-left: auto; font-weight: bold;
        }}
        .logout-btn:hover {{ background: #c0392b; }}
        .dashboard-container {{
            max-width: 800px;
            margin: 4em auto;
            background: #23272e;
            border-radius: 12px;
            box-shadow: 0 4px 24px rgba(44,62,80,0.18);
            padding: 2.5em 2.5em;
            color: #fff;
        }}
        h1 {{ color: #39ff14; font-size: 2em; margin-bottom: 1em; }}
        .stats {{ display: flex; justify-content: space-around; margin-bottom: 2em; }}
        .stat-card {{ background: #181c20; border-radius: 8px; padding: 1.5em 2em; box-shadow: 0 2px 8px rgba(44,62,80,0.18); text-align: center; }}
        .stat-label {{ color: #00c3ff; font-size: 1.1em; margin-bottom: 0.5em; }}
        .stat-value {{ color: #39ff14; font-size: 2em; font-weight: bold; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 2em; background: #181c20; border-radius: 8px; overflow: hidden; }}
        th, td {{ padding: 1em; text-align: center; }}
        th {{ background: #23272e; color: #00c3ff; }}
        tr:nth-child(even) {{ background: #23272e; }}
        tr:nth-child(odd) {{ background: #181c20; }}
        button {{ background: #e74c3c; color: #fff; border: none; padding: 0.7em 2em; border-radius: 4px; font-size: 1em; cursor: pointer; margin-top: 2em; font-weight: bold; }}
        button:hover {{ background: #c0392b; }}
    </style>
    </head>
    <body>
        <div class='navbar'>
            <a href="/">Home</a>
            <a href="/status">Status Log</a>
            <a href="/dashboard">Dashboard</a>
            <a href="/download_log">Download Log</a>
            <form action="/logout" method="get" style="margin-left:auto;display:inline;">
                <button class="logout-btn" type="submit">Logout</button>
            </form>
        </div>
        <div class='dashboard-container'>
            <h1>Email Campaign Dashboard</h1>
            <div class='stats'>
                <div class='stat-card'>
                    <div class='stat-label'>Total Sent Emails</div>
                    <div class='stat-value'>{total_sent}</div>
                </div>
                <div class='stat-card'>
                    <div class='stat-label'>Total Pending Emails</div>
                    <div class='stat-value'>{total_pending}</div>
                </div>
            </div>
            <h2 style='color:#00c3ff;'>Last 3 Days Email Sent</h2>
            <table>
                <tr><th>Date</th><th>Emails Sent</th></tr>
                {''.join(f'<tr><td>{d["date"]}</td><td>{d["count"]}</td></tr>' for d in last_3_days)}
            </table>
            <form action="/stop_campaign" method="post">
                <button type="submit">Stop Campaign</button>
            </form>
        </div>
    </body>
    </html>
    """
    return html

@app.route('/download_log')
@login_required
def download_log():
    import os
    log_path = os.path.join(os.path.dirname(__file__), 'data/send_log.csv')
    if not os.path.exists(log_path):
        return '<h2>send_log.csv not found.</h2>', 404
    return send_file(log_path, as_attachment=True, download_name='send_log.csv')

@app.route('/stop_campaign', methods=['POST'])
@login_required
def stop_campaign():
    # This is a placeholder. You should implement logic to stop the running campaign process.
    # For now, just log the event.
    log_audit('Campaign STOP requested by user.')
    # You may want to use a process manager or set a flag checked by the campaign loop.
    return redirect(url_for('dashboard'))

def keep_alive():
    """Keep the server alive by pinging itself every minute"""
    while True:
        try:
            base_url = os.environ.get('RENDER_EXTERNAL_URL', 'http://localhost:10000')
            requests.get(f"{base_url}/", timeout=10)
        except Exception as e:
            print(f"[Keep-Alive] Error pinging server: {e}")
        time.sleep(60)

def seconds_until_next_scheduled_time():
    now = datetime.now(IST)
    next_run = now.replace(hour=SCHEDULE_HOUR, minute=SCHEDULE_MINUTE, second=0, microsecond=0)
    if now >= next_run:
        next_run += timedelta(days=1)
    return (next_run - now).total_seconds()

def log_audit(message):
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(f"{datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")

def run_campaign():
    last_run_info['start'] = datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S')
    last_run_info['error'] = None
    log_audit('Campaign STARTED')
    try:
        subprocess.run([
            "python", "src/main.py",
            "--resume", "data/Ayush_Srivastava.pdf",
            "--batch-size", "5",
            "--daily-limit", "1001"
        ], check=True)
    except Exception as e:
        last_run_info['error'] = str(e)
        log_audit(f'Campaign ERROR: {e}')
    last_run_info['end'] = datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S')
    log_audit('Campaign ENDED')

def scheduler_loop():
    while True:
        wait_seconds = seconds_until_next_scheduled_time()
        # Check if the next run is on a weekend (Saturday=5, Sunday=6)
        from datetime import datetime, timedelta
        now = datetime.now(IST)
        next_run = now.replace(hour=SCHEDULE_HOUR, minute=SCHEDULE_MINUTE, second=0, microsecond=0)
        if now >= next_run:
            next_run += timedelta(days=1)
        # If next_run is Saturday or Sunday, skip to Monday
        while next_run.weekday() in (5, 6):
            next_run += timedelta(days=1)
        wait_seconds = (next_run - now).total_seconds()
        print(f"[Scheduler] Waiting {wait_seconds/3600:.2f} hours until next run at {next_run.strftime('%A %H:%M:%S')} IST...")
        time.sleep(wait_seconds)
        # Double-check it's not weekend before running
        if datetime.now(IST).weekday() not in (5, 6):
            print(f"[Scheduler] Starting campaign at {datetime.now(IST).strftime('%A %H:%M:%S')} IST!")
            run_campaign()
        else:
            print("[Scheduler] Skipping campaign run on weekend.")
        time.sleep(60)

if __name__ == "__main__":
    # Start the keep-alive thread
    keep_alive_thread = threading.Thread(target=keep_alive, daemon=True)
    keep_alive_thread.start()
    # Start the scheduler in a background thread
    scheduler_thread = threading.Thread(target=scheduler_loop, daemon=True)
    scheduler_thread.start()
    # Start the Flask status server
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port) 