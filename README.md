# 🤖 AI Personal Assistant

A full-stack AI Personal Assistant with voice control, reminders, meetings, and real-time notifications.

## **Features** ✨

✅ Voice Control - Say "Hey AI" to activate  
✅ AI Chat - Talk to your AI assistant naturally  
✅ Reminders - Create and manage reminders with notifications  
✅ Meetings - Schedule and track meetings  
✅ Notifications - Real-time push notifications  
✅ Personalization - Remembers your name  

---

## **Quick Start** 🚀

### Terminal 1 - Backend:
```bash
cd ~/ai-assistant/backend
source venv/bin/activate
python app.py
```

### Terminal 2 - Frontend:
```bash
cd ~/ai-assistant/frontend
npm start
```

Open: http://localhost:3000 ✅

---

## **How to Use** 💬

1. Enter your name when app loads
2. Type messages in the chat box
3. Say "Hey AI" to use voice control
4. Create reminders and schedule meetings in the tabs

---

## **Tech Stack** 🛠️

**Backend:** Flask, SQLAlchemy, APScheduler, SQLite  
**Frontend:** React, Web Speech API, CSS3  

---

## **API Endpoints** 🔌

- POST `/api/assistant/chat` - Chat with AI
- GET `/api/user` - Get user info
- POST `/api/user` - Save user name
- GET `/api/time` - Get current time
- GET `/api/reminders` - Get reminders
- POST `/api/reminders` - Create reminder
- GET `/api/meetings` - Get meetings
- POST `/api/meetings` - Create meeting
- GET `/api/notifications` - Get notifications

---

## **Troubleshooting** 🔧

**Port already in use?**
```bash
lsof -ti:5000 | xargs kill -9  # Kill port 5000
lsof -ti:3000 | xargs kill -9  # Kill port 3000
```

**Reset database:**
```bash
cd ~/ai-assistant/backend
rm assistant.db
python app.py
```

---

## **Docker** 🐳

```bash
cd ~/ai-assistant
docker-compose build
docker-compose up
```

---

## **Environment Variables** 🔐

Create `.env` in backend folder:

```env
GROQ_API_KEY=your_key
HF_API_TOKEN=your_token
```

Get free keys:
- Groq: https://console.groq.com
- Hugging Face: https://huggingface.co

---

## **Project Structure**---

## **Version**

v1.0 - May 2026  
Status: ✅ Fully Working

Created by: Kalyan Reddy

---

**Enjoy your AI Personal Assistant!** 🎉
