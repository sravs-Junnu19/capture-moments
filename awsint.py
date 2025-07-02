from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import boto3
from boto3.dynamodb.conditions import Key
import os
import smtplib
import random
import time

OTP_EXPIRY = 300
otp_cache = {}

SENDER_EMAIL = 'your_email@gmail.com'
APP_PASSWORD = 'your_app_password_from_google'

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'your-secret-key'

# Initialize DynamoDB resource with explicit region
dynamodb = boto3.resource('dynamodb', region_name='ap-south-1')
users_table = dynamodb.Table('Users')
support_table = dynamodb.Table('SupportMessages')
chat_table = dynamodb.Table('ChatMessages')

# Sample photographer and availability data
photographers = [
    {"id": "eshan", "name": "Eshan", "skills": ["Cinematic Edits", "Drone Shots", "Fashion Editorial", "360 Photography", "Concept Shoots"], "category": "Next-Gen Surprise Pro", "image": "eshan.jpg", "cost": 20000},
    {"id": "krish", "name": "Krish", "skills": ["Wedding", "Couple", "Beach"], "category": "Thematic Shoots", "image": "krish.jpg", "cost": 80000},
    {"id": "megha", "name": "Megha", "skills": ["Destination", "Luxury", "Palace"], "category": "Luxury & Destination Shoots", "image": "megha.jpg", "cost": 120000},
    {"id": "leo", "name": "Leo", "skills": ["Creative", "Conceptual", "Art"], "category": "Creative & Conceptual", "image": "leo.jpg", "cost": 95000}
]

availability_data = {
    "eshan": ["2025-07-03", "2025-07-07", "2025-07-12"],
    "krish": ["2025-06-20", "2025-06-23"],
    "megha": ["2025-06-19", "2025-06-22"],
    "leo": ["2025-06-21", "2025-06-24"]
}

def send_otp_via_email(to_email, otp):
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(SENDER_EMAIL, APP_PASSWORD)
    subject = 'Capture Moments - Password Reset OTP'
    body = f'Your OTP is: {otp}. It expires in 5 minutes.'
    message = f'Subject: {subject}\n\n{body}'
    server.sendmail(SENDER_EMAIL, to_email, message)
    server.quit()

# DynamoDB interactions for users
def load_user(login_id):
    response = users_table.get_item(Key={'login_id': login_id})
    return response.get('Item')

def save_user(email, user_id, password):
    users_table.put_item(Item={'login_id': email, 'password': password, 'user_id': user_id})
    users_table.put_item(Item={'login_id': user_id, 'password': password, 'email': email})

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
        email = request.form['email'].lower()
        user_id = request.form['user_id'].lower()
        password = request.form['password']

        if load_user(email) or load_user(user_id):
            return "User with same email or ID already exists!"

        save_user(email, user_id, password)
        session['user'] = email
        return redirect(url_for('home'))

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login_id = request.form['login_id'].lower()
        password = request.form['password']

        user = load_user(login_id)
        if user and user.get("password") == password:
            session['user'] = login_id
            return redirect(url_for('home'))

        return "Invalid credentials!"
    return render_template('login.html')

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        login_id = request.form['login_id'].lower()
        user = load_user(login_id)
        if not user:
            return "❌ User not found"

        otp = str(random.randint(100000, 999999))
        otp_cache[login_id] = {"otp": otp, "timestamp": time.time()}
        send_otp_via_email(user.get("email"), otp)
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

        user = load_user(login_id)
        if user:
            users_table.put_item(Item={**user, 'password': new_password})

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
        return render_template("booking_success.html", photographer_name=photographer['name'], date=date, cost=cost)
    return render_template('book.html')

@app.route('/show-photographers')
def show_photographers():
    if not session.get('user'):
        return redirect(url_for('login'))
    return render_template('photographers.html', photographers=photographers, availability_data=availability_data)

@app.route('/surprise')
def surprise():
    if not session.get('user'):
        return redirect(url_for('login'))
    surprise_id = "eshan"
    surprise_photographer = next((p for p in photographers if p["id"] == surprise_id), None)
    if not surprise_photographer:
        return "Photographer not found", 404
    dates = availability_data.get(surprise_id, [])
    return render_template("surprise.html", photographer=surprise_photographer, dates=dates)

@app.route('/location')
def location():
    if not session.get('user'):
        return redirect(url_for('login'))
    return render_template("location.html", locations=[])

@app.route('/support', methods=['GET', 'POST'])
def support():
    if not session.get('user'):
        return redirect(url_for('login'))
    email = session['user']
    if request.method == 'POST':
        issue = request.form['issue']
        support_table.put_item(Item={'email': email, 'message': issue, 'reply': ''})
        return redirect(url_for('support'))
    response = support_table.get_item(Key={'email': email})
    item = response.get('Item', {})
    return render_template('support.html', message=item.get('message'), reply=item.get('reply'))

@app.route('/admin/reply', methods=['GET', 'POST'])
def admin_reply():
    if request.method == 'POST':
        email = request.form['email']
        reply = request.form['reply']
        support_table.update_item(
            Key={'email': email},
            UpdateExpression='SET reply = :r',
            ExpressionAttributeValues={':r': reply}
        )
        return redirect(url_for('admin_reply'))
    all_queries = support_table.scan().get('Items', [])
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
    chat_table.put_item(Item={'timestamp': str(time.time()), 'sender': sender, 'message': message})
    return jsonify({'status': 'success'})

@app.route('/style-recommendation')
def style_recommendation():
    if not session.get('user'):
        return redirect(url_for('login'))
    return "<h2>Get Recommended Styles for Your Shoot (AI powered) – Coming soon!</h2>"

if __name__ == '__main__':
    app.run(debug=True)
