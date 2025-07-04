from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import json
import os
import smtplib           # ✅ Required for send_otp_via_email
import random            # ✅ Required for OTP generation
import time  
OTP_EXPIRY = 300  # seconds = 5 minutes
otp_cache = {}  # Stores temporary OTPs with timestamps

SENDER_EMAIL = 'your_email@gmail.com'             # ✅ Use your Gmail
APP_PASSWORD = 'your_app_password_from_google'    # ✅ App password (not normal password)

def send_otp_via_email(to_email, otp):
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(SENDER_EMAIL, APP_PASSWORD)
    subject = 'Capture Moments - Password Reset OTP'
    body = f'Your OTP is: {otp}. It expires in 5 minutes.'
    message = f'Subject: {subject}\n\n{body}'
    server.sendmail(SENDER_EMAIL, to_email, message)
    server.quit()


app = Flask(__name__)
app.secret_key = 'your-secret-key'

photographers = [

    {
        "id": "krish",
        "name": "Krish",
        "skills": ["Wedding", "Couple", "Beach"],
        "category": "Thematic Shoots",
        "image": "krish.jpg",
        "cost": 80000
    },
    {
        "id": "megha",
        "name": "Megha",
        "skills": ["Destination", "Luxury", "Palace"],
        "category": "Luxury & Destination Shoots",
        "image": "megha.jpg",
        "cost": 120000
    },
    {
        "id": "leo",
        "name": "Leo",
        "skills": ["Creative", "Conceptual", "Art"],
        "category": "Creative & Conceptual",
        "image": "leo.jpg",
        "cost": 95000
    }
]

availability_data = {

    "krish": ["2025-06-20", "2025-06-23"],
    "megha": ["2025-06-19", "2025-06-22"],
    "leo":   ["2025-06-21", "2025-06-24"]
}

def load_users():
    if os.path.exists('users.json'):
        with open('users.json', 'r') as f:
            return json.load(f)
    return {}

def save_users(users):
    with open('users.json', 'w') as f:
        json.dump(users, f, indent=4)

@app.route('/')
def index():
    if session.get('user'):
        return redirect(url_for('home'))
    return redirect(url_for('start'))

@app.route('/start')
def start():
    return render_template('start.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        users = load_users()
        email = request.form['email'].lower()
        user_id = request.form['user_id'].lower()
        password = request.form['password']

        if email in users or user_id in users:
            return "User with same email or ID already exists!"

        users[email] = {"password": password, "user_id": user_id}
        users[user_id] = {"password": password, "email": email}

        save_users(users)
        session['user'] = email
        return redirect(url_for('home'))

    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        users = load_users()
        login_id = request.form['login_id'].lower()
        password = request.form['password']

        if login_id in users and users[login_id].get("password") == password:
            session['user'] = login_id
            return redirect(url_for('home'))

        return "Invalid credentials!"
    return render_template('login.html')

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        login_id = request.form['login_id'].lower()
        users = load_users()

        user = users.get(login_id)
        if not user:
            user = next((v for k, v in users.items() if v.get("user_id") == login_id or v.get("email") == login_id), None)

        if not user or "email" not in user:
            return "❌ User not found or missing email."

        otp = str(random.randint(100000, 999999))
        otp_cache[login_id] = {"otp": otp, "timestamp": time.time()}

        send_otp_via_email(user["email"], otp)
        session['reset_id'] = login_id
        return redirect(url_for('verify_otp'))

    return render_template('forgot_password.html')

@app.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    login_id = session.get('reset_id')
    if not login_id:
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        entered_otp = request.form['otp']
        new_password = request.form['new_password']
        otp_info = otp_cache.get(login_id)

        if not otp_info or time.time() - otp_info["timestamp"] > OTP_EXPIRY:
            return "❌ OTP expired or invalid"

        if entered_otp != otp_info["otp"]:
            return "❌ Incorrect OTP"

        users = load_users()
        if login_id in users:
            users[login_id]['password'] = new_password
        else:
            for k, v in users.items():
                if v.get("user_id") == login_id or v.get("email") == login_id:
                    users[k]['password'] = new_password
                    break

        save_users(users)
        otp_cache.pop(login_id, None)
        return "✅ Password reset successful! <a href='/login'>Login now</a>"

    return render_template('verify_otp.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('start'))

@app.route('/home')
def home():
    if not session.get('user'):
        return redirect(url_for('login'))
    return render_template('home.html')

@app.route('/book', methods=['GET', 'POST'])
def book():
    if not session.get('user'):
        return redirect(url_for('login'))

    if request.method == 'POST':
        photographer_id = request.form.get('photographer_id')
        date = request.form.get('date')

        photographer = next((p for p in photographers if p['id'] == photographer_id), None)
        if not photographer:
            return "Photographer not found", 404

        cost = photographer.get('cost', 0)

        return render_template(
            "booking_success.html",
            photographer_name=photographer['name'],
            date=date,
            cost=cost
        )

    return render_template('book.html')

@app.route('/show-photographers')
def show_photographers():
    if not session.get('user'):
        return redirect(url_for('login'))
    return render_template('photographers.html', photographers=photographers, availability_data=availability_data)

@app.route('/location')
def location():
    if not session.get('user'):
        return redirect(url_for('login'))

    locations = [
        {
            "category": "Thematic Shoots",
            "places": [
                {
                    "name": "Golden Beach",
                    "city": "Puri, Odisha",
                    "image": "beach.jpg",
                    "desc": "Soft sand and glowing horizons for seaside couple shoots."
                },
                {
                    "name": "Couple's Hideout",
                    "city": "Lonavala",
                    "image": "couple.jpg",
                    "desc": "Private hills for dreamy couple portraits."
                },
                {
                    "name": "Temple Silhouettes",
                    "city": "Madurai",
                    "image": "temple.jpg",
                    "desc": "Capture divinity and tradition in colorful temple architecture."
                }
            ]
        },
        {
            "category": "Luxury & Destination Shoots",
            "places": [
                {
                    "name": "Maldives Bliss",
                    "city": "Male",
                    "image": "maldives.jpg",
                    "desc": "Crystal waters and luxury resorts — ideal for destination shoots."
                },
                {
                    "name": "Taj Mahal",
                    "city": "Agra",
                    "image": "tajmahal.jpg",
                    "desc": "Eternal symbol of love — perfect for proposals and memories."
                },
                {
                    "name": "Royal Wedding",
                    "city": "Udaipur",
                    "image": "wedding.jpg",
                    "desc": "Palace-style backdrops to frame your forever moments."
                }
            ]
        },
        {
            "category": "Creative & Conceptual",
            "places": [
                {
                    "name": "Under the Arc of Love",
                    "city": "Mumbai",
                    "image": "arc.jpg",
                    "desc": "Cinematic archway shots perfect for couple and wedding themes."
                }
            ]
        }
    ]
    return render_template("location.html", locations=locations)

@app.route('/support', methods=['GET', 'POST'])
def support():
    if not session.get('user'):
        return redirect(url_for('login'))

    message = ""
    reply = ""

    if request.method == 'POST':
        message = request.form.get('issue')
        # You can process or save the message here if needed
        reply = "Thank you for contacting us! Our team will respond shortly."

    return render_template("support.html", message=message, reply=reply)


@app.route('/admin/reply', methods=['GET', 'POST'])
def admin_reply():
    if request.method == 'POST':
        email = request.form['email']
        reply = request.form['reply']
        if os.path.exists('support_data.json'):
            with open('support_data.json', 'r') as f:
                data = json.load(f)
            if email in data:
                data[email]['reply'] = reply
                with open('support_data.json', 'w') as f:
                    json.dump(data, f, indent=4)
        return redirect(url_for('admin_reply'))
    all_queries = {}
    if os.path.exists('support_data.json'):
        with open('support_data.json', 'r') as f:
            all_queries = json.load(f)
    return render_template('admin_reply.html', queries=all_queries)

@app.route('/chat')
def chat():
    if not session.get('user'):
        return redirect(url_for('login'))
    return render_template('chat.html', user=session['user'])

@app.route('/send-message', methods=['POST'])
def send_message():
    data = request.get_json()
    message = data.get('message')
    sender = session.get('user') or 'admin'
    chat = []
    if os.path.exists('static/chat.json'):
        with open('static/chat.json', 'r') as f:
            chat = json.load(f)
    chat.append({'sender': sender, 'message': message})
    with open('static/chat.json', 'w') as f:
        json.dump(chat, f, indent=4)
    return jsonify({'status': 'success'})

@app.route('/style-recommendation')
def style_recommendation():
    if not session.get('user'):
        return redirect(url_for('login'))
    return "<h2>Get Recommended Styles for Your Shoot (AI powered) – Coming soon!</h2>"

if __name__ == '__main__':
    app.run(debug=True)
