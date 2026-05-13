from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import os
import json
from apscheduler.schedulers.background import BackgroundScheduler
import atexit
import pytz
from dotenv import load_dotenv
import requests

load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///assistant.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# API Keys
GROQ_API_KEY = os.getenv('GROQ_API_KEY', '')
HF_API_TOKEN = os.getenv('HF_API_TOKEN', '')

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(100), unique=True, default='user1')
    name = db.Column(db.String(255))
    timezone = db.Column(db.String(50), default='UTC')
    ai_provider = db.Column(db.String(50), default='groq')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'timezone': self.timezone,
            'ai_provider': self.ai_provider
        }

class Reminder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(100), default='user1')
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    reminder_time = db.Column(db.DateTime, nullable=False)
    notification_before = db.Column(db.Integer, default=10)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    notified = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'reminder_time': self.reminder_time.isoformat(),
            'notification_before': self.notification_before,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'notified': self.notified
        }

class Meeting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(100), default='user1')
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime)
    location = db.Column(db.String(255))
    source = db.Column(db.String(50), default='manual')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'location': self.location,
            'source': self.source,
            'created_at': self.created_at.isoformat()
        }

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(100), default='user1')
    reminder_id = db.Column(db.Integer, db.ForeignKey('reminder.id'))
    meeting_id = db.Column(db.Integer, db.ForeignKey('meeting.id'))
    message = db.Column(db.Text, nullable=False)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    read = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {
            'id': self.id,
            'message': self.message,
            'sent_at': self.sent_at.isoformat(),
            'read': self.read
        }

with app.app_context():
    db.create_all()

scheduler = BackgroundScheduler()

def check_reminders():
    with app.app_context():
        now = datetime.utcnow()
        reminders = Reminder.query.filter_by(is_active=True, notified=False).all()
        for reminder in reminders:
            notification_time = reminder.reminder_time - timedelta(minutes=reminder.notification_before)
            if now >= notification_time and now < reminder.reminder_time:
                notification = Notification(user_id=reminder.user_id, reminder_id=reminder.id, message=f"⏰ Reminder: {reminder.title} - Due at {reminder.reminder_time.strftime('%I:%M %p')}")
                db.session.add(notification)
                reminder.notified = True
                db.session.commit()

def check_meetings():
    with app.app_context():
        now = datetime.utcnow()
        meetings = Meeting.query.filter(Meeting.start_time > now, Meeting.start_time <= now + timedelta(hours=24)).all()
        for meeting in meetings:
            notification_time = meeting.start_time - timedelta(minutes=10)
            if now >= notification_time and now < meeting.start_time:
                notification = Notification(user_id=meeting.user_id, meeting_id=meeting.id, message=f"📅 Meeting Reminder: {meeting.title} at {meeting.start_time.strftime('%I:%M %p')}")
                db.session.add(notification)
                db.session.commit()

scheduler.add_job(func=check_reminders, trigger="interval", seconds=10)
scheduler.add_job(func=check_meetings, trigger="interval", seconds=10)
scheduler.start()

atexit.register(lambda: scheduler.shutdown())

# AI Functions
def get_groq_response_with_prompt(system_prompt):
    """Get response from Groq with full custom prompt"""
    try:
        if not GROQ_API_KEY:
            return None
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": system_prompt}],
            "temperature": 0.7,
            "max_tokens": 200
        }
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if 'choices' in data and len(data['choices']) > 0:
                return data['choices'][0]['message']['content']
        return None
    except Exception as e:
        print(f"Groq Error: {str(e)}")
        return None

def get_groq_response(message, user_name):
    """Get response from Groq API"""
    try:
        if not GROQ_API_KEY:
            return None
        
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        
        from datetime import datetime
        import pytz
        current_time = datetime.now().strftime("%I:%M %p")
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {
                    "role": "user",
                    "content": f"You are a helpful AI personal assistant for {user_name}. The current time is {current_time}. Be friendly and conversational. Keep responses short (under 150 words). User: {message}"
                }
            ],
            "temperature": 0.7,
            "max_tokens": 150
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if 'choices' in data and len(data['choices']) > 0:
                return data['choices'][0]['message']['content']
        return None
    except Exception as e:
        print(f"Groq Error: {str(e)}")
        return None

def get_huggingface_response(message, user_name):
    """Get response from Hugging Face API"""
    try:
        if not HF_API_TOKEN:
            return None
        
        headers = {"Authorization": f"Bearer {HF_API_TOKEN}"}
        API_URL = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.1"
        
        payload = {
            "inputs": f"You are a helpful AI assistant for {user_name}. Be friendly and helpful. Keep responses short (under 150 words). User: {message}",
            "parameters": {"max_length": 150}
        }
        
        response = requests.post(API_URL, headers=headers, json=payload, timeout=10)
        if response.status_code == 200:
            result = response.json()
            if result and len(result) > 0:
                text = result[0].get('generated_text', '')
                if text:
                    return text.split("User:")[-1].strip() if "User:" in text else text
        return None
    except Exception as e:
        print(f"HF Error: {str(e)}")
        return None

# Routes
@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'message': 'AI Assistant Backend is running'}), 200

@app.route('/api/user', methods=['GET'])
def get_user():
    user = User.query.filter_by(user_id='user1').first()
    if user:
        return jsonify(user.to_dict()), 200
    return jsonify({'name': None, 'timezone': 'UTC', 'ai_provider': 'groq'}), 200

@app.route('/api/user', methods=['POST'])
def save_user():
    data = request.json
    user = User.query.filter_by(user_id='user1').first()
    if not user:
        user = User(
            user_id='user1', 
            name=data.get('name'), 
            timezone=data.get('timezone', 'UTC'),
            ai_provider=data.get('ai_provider', 'groq')
        )
        db.session.add(user)
    else:
        user.name = data.get('name', user.name)
        user.timezone = data.get('timezone', user.timezone)
        user.ai_provider = data.get('ai_provider', user.ai_provider)
    db.session.commit()
    return jsonify({'success': True, 'user': user.to_dict()}), 200

@app.route('/api/time', methods=['GET'])
def get_current_time():
    user = User.query.filter_by(user_id='user1').first()
    tz = user.timezone if user else 'UTC'
    try:
        local_tz = pytz.timezone(tz)
        now = datetime.now(local_tz)
        return jsonify({
            'current_time': now.isoformat(),
            'timezone': tz,
            'formatted_time': now.strftime('%I:%M %p'),
            'formatted_date': now.strftime('%A, %B %d, %Y')
        }), 200
    except:
        now = datetime.utcnow()
        return jsonify({
            'current_time': now.isoformat(),
            'timezone': 'UTC',
            'formatted_time': now.strftime('%I:%M %p'),
            'formatted_date': now.strftime('%A, %B %d, %Y')
        }), 200

@app.route('/api/reminders', methods=['GET'])
def get_reminders():
    reminders = Reminder.query.filter_by(user_id='user1', is_active=True).order_by(Reminder.reminder_time).all()
    return jsonify([r.to_dict() for r in reminders]), 200

@app.route('/api/reminders', methods=['POST'])
def create_reminder():
    data = request.json
    try:
        reminder = Reminder(
            user_id='user1',
            title=data.get('title', 'Untitled Reminder'),
            description=data.get('description', ''),
            reminder_time=datetime.fromisoformat(data.get('reminder_time')),
            notification_before=data.get('notification_before', 10),
            is_active=True
        )
        db.session.add(reminder)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Reminder created successfully', 'reminder': reminder.to_dict()}), 201
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/reminders/<int:reminder_id>', methods=['DELETE'])
def delete_reminder(reminder_id):
    reminder = Reminder.query.get(reminder_id)
    if not reminder:
        return jsonify({'success': False, 'error': 'Reminder not found'}), 404
    reminder.is_active = False
    db.session.commit()
    return jsonify({'success': True, 'message': 'Reminder deleted'}), 200

@app.route('/api/meetings', methods=['GET'])
def get_meetings():
    meetings = Meeting.query.filter(Meeting.start_time > datetime.utcnow()).order_by(Meeting.start_time).all()
    return jsonify([m.to_dict() for m in meetings]), 200

@app.route('/api/meetings', methods=['POST'])
def create_meeting():
    data = request.json
    try:
        meeting = Meeting(
            user_id='user1',
            title=data.get('title', 'Untitled Meeting'),
            description=data.get('description', ''),
            start_time=datetime.fromisoformat(data.get('start_time')),
            end_time=datetime.fromisoformat(data.get('end_time')) if data.get('end_time') else None,
            location=data.get('location', ''),
            source='manual'
        )
        db.session.add(meeting)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Meeting created successfully', 'meeting': meeting.to_dict()}), 201
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/notifications', methods=['GET'])
def get_notifications():
    notifications = Notification.query.filter_by(user_id='user1').order_by(Notification.sent_at.desc()).all()
    return jsonify([n.to_dict() for n in notifications]), 200

@app.route('/api/notifications/<int:notification_id>/read', methods=['PUT'])
def mark_notification_read(notification_id):
    notification = Notification.query.get(notification_id)
    if not notification:
        return jsonify({'success': False, 'error': 'Notification not found'}), 404
    notification.read = True
    db.session.commit()
    return jsonify({'success': True, 'message': 'Notification marked as read'}), 200

@app.route('/api/assistant/chat', methods=['POST'])
def assistant_chat():
    """Main AI chat endpoint"""
    data = request.json
    user_message = data.get('input', '')
    
    if not user_message:
        return jsonify({'success': False, 'error': 'No message provided'}), 400
    
    try:
        user = User.query.filter_by(user_id='user1').first()
        user_name = user.name if user else 'friend'

        # Get real reminders and meetings from database
        reminders = Reminder.query.filter_by(user_id='user1', is_active=True).all()
        meetings = Meeting.query.filter(Meeting.start_time > datetime.utcnow()).all()

        reminders_text = "No reminders." if not reminders else ", ".join([f"{r.title} at {r.reminder_time.strftime('%I:%M %p on %b %d')}" for r in reminders])
        meetings_text = "No meetings." if not meetings else ", ".join([f"{m.title} at {m.start_time.strftime('%I:%M %p on %b %d')}" for m in meetings])

        current_time = datetime.now().strftime("%I:%M %p")
        current_date = datetime.now().strftime("%A, %B %d, %Y")

        system_prompt = f"""You are a smart personal assistant for {user_name}.
Current time: {current_time}
Current date: {current_date}
Real reminders: {reminders_text}
Real meetings: {meetings_text}

RULES:
1. NEVER make up fake reminders or meetings. Only use the real ones above.
2. If user asks to set a reminder, reply EXACTLY in this format:
   SAVE_REMINDER: title="<title>" time="<YYYY-MM-DD HH:MM>"
3. If user asks to set a meeting, reply EXACTLY in this format:
   SAVE_MEETING: title="<title>" time="<YYYY-MM-DD HH:MM>"
4. Answer any general question normally.
5. Keep replies short and friendly.

User: {user_message}"""

        ai_response = get_groq_response_with_prompt(system_prompt)

        if not ai_response:
            ai_response = f"Sorry {user_name}, I had trouble processing that. Please try again."

        # Check if AI wants to save a reminder
        if 'SAVE_REMINDER:' in ai_response:
            try:
                import re
                title_match = re.search(r'title="([^"]+)"', ai_response)
                time_match = re.search(r'time="([^"]+)"', ai_response)
                if title_match and time_match:
                    title = title_match.group(1)
                    reminder_time = datetime.fromisoformat(time_match.group(1))
                    reminder = Reminder(
                        user_id='user1',
                        title=title,
                        description='',
                        reminder_time=reminder_time,
                        notification_before=10,
                        is_active=True
                    )
                    db.session.add(reminder)
                    db.session.commit()
                    ai_response = f"Got it {user_name}! Reminder set: '{title}' at {reminder_time.strftime('%I:%M %p on %b %d')} ✅"
            except Exception as ex:
                print(f"Reminder save error: {ex}")

        # Check if AI wants to save a meeting
        if 'SAVE_MEETING:' in ai_response:
            try:
                import re
                title_match = re.search(r'title="([^"]+)"', ai_response)
                time_match = re.search(r'time="([^"]+)"', ai_response)
                if title_match and time_match:
                    title = title_match.group(1)
                    start_time = datetime.fromisoformat(time_match.group(1))
                    end_time = start_time.replace(hour=start_time.hour+1)
                    meeting = Meeting(
                        user_id='user1',
                        title=title,
                        description='',
                        start_time=start_time,
                        end_time=end_time,
                        source='voice'
                    )
                    db.session.add(meeting)
                    db.session.commit()
                    ai_response = f"Done {user_name}! Meeting scheduled: '{title}' at {start_time.strftime('%I:%M %p on %b %d')} 📅"
            except Exception as ex:
                print(f"Meeting save error: {ex}")

        return jsonify({
            'success': True,
            'response': ai_response,
            'user_name': user_name
        }), 200
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
