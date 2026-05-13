import React, { useState, useEffect, useRef } from 'react';
import './App.css';

function App() {
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [reminders, setReminders] = useState([]);
  const [meetings, setMeetings] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [activeTab, setActiveTab] = useState('chat');
  const [loading, setLoading] = useState(false);
  const [userName, setUserName] = useState('');
  const [isListening, setIsListening] = useState(false);
  const [currentTime, setCurrentTime] = useState('');
  const messagesEndRef = useRef(null);
  const recognitionRef = useRef(null);

  const API_BASE_URL = 'http://localhost:5000/api';

  // Initialize voice recognition
  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      recognitionRef.current = new SpeechRecognition();
      recognitionRef.current.continuous = true;
      recognitionRef.current.interimResults = true;
      recognitionRef.current.lang = 'en-US';

      recognitionRef.current.onstart = () => {
        setIsListening(true);
      };

      recognitionRef.current.onend = () => {
        setIsListening(false);
      };

      recognitionRef.current.onresult = (event) => {
        let transcript = '';
        for (let i = event.resultIndex; i < event.results.length; i++) {
          transcript += event.results[i][0].transcript;
        }

        if (event.results[event.results.length - 1].isFinal) {
          if (transcript.toLowerCase().includes('hey ai') || transcript.toLowerCase().includes('hey assistant')) {
            const command = transcript.toLowerCase().replace('hey ai', '').replace('hey assistant', '').trim();
            if (command) {
              setInputValue(command);
              handleSendMessage(null, command);
            }
          }
        }
      };
    }
  }, []);

  // Fetch user info
  useEffect(() => {
    const fetchUser = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/user`);
        const data = await response.json();
        if (data.name) {
          setUserName(data.name);
          addBotMessage(`Welcome back, ${data.name}! 👋 How can I help you today?`);
        } else {
          addBotMessage('Hello! I\'m your AI Personal Assistant. What\'s your name?');
        }
      } catch (error) {
        addBotMessage('Hello! I\'m your AI Personal Assistant. What\'s your name?');
      }
    };

    fetchUser();
  }, []);

  // Update time every second
  useEffect(() => {
    const updateTime = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/time`);
        const data = await response.json();
        setCurrentTime(data.formatted_time);
      } catch (error) {
        console.error('Error fetching time:', error);
      }
    };

    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  const addBotMessage = (text) => {
    setMessages(prev => [...prev, {
      id: prev.length + 1,
      type: 'bot',
      text: text
    }]);
  };

  const fetchReminders = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/reminders`);
      const data = await response.json();
      setReminders(data);
    } catch (error) {
      console.error('Error fetching reminders:', error);
    }
  };

  const fetchMeetings = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/meetings`);
      const data = await response.json();
      setMeetings(data);
    } catch (error) {
      console.error('Error fetching meetings:', error);
    }
  };

  const fetchNotifications = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/notifications`);
      const data = await response.json();
      setNotifications(data);
    } catch (error) {
      console.error('Error fetching notifications:', error);
    }
  };

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    fetchReminders();
    fetchMeetings();
    fetchNotifications();

    const interval = setInterval(() => {
      fetchNotifications();
    }, 2000);

    return () => clearInterval(interval);
  }, []);

  // Start voice listening
  const startListening = () => {
    if (recognitionRef.current) {
      recognitionRef.current.start();
    }
  };

  const stopListening = () => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
    }
  };

  const handleSendMessage = async (e, messageText = null) => {
    if (e) e.preventDefault();
    
    const message = messageText || inputValue.trim();
    if (!message) return;

    // If no user name, save it
    if (!userName) {
      try {
        await fetch(`${API_BASE_URL}/user`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name: message, timezone: Intl.DateTimeFormat().resolvedOptions().timeZone })
        });
        setUserName(message);
        addBotMessage(`Nice to meet you, ${message}! 👋 I'm your AI assistant. How can I help you today?`);
        setInputValue('');
        return;
      } catch (error) {
        console.error('Error saving user:', error);
      }
    }

    const userMessage = {
      id: messages.length + 1,
      type: 'user',
      text: message
    };
    setMessages([...messages, userMessage]);
    setInputValue('');
    setLoading(true);

    try {
      const chatResponse = await fetch(`${API_BASE_URL}/assistant/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ input: message })
      });
      const chatData = await chatResponse.json();

      if (chatData.success) {
        addBotMessage(chatData.response);
        fetchReminders();
        fetchMeetings();
      } else {
        addBotMessage(`Sorry, ${userName}, I encountered an error. Please try again.`);
      }
    } catch (error) {
      console.error('Error:', error);
      addBotMessage(`Sorry, ${userName}, I encountered an error. Please try again.`);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteReminder = async (id) => {
    try {
      await fetch(`${API_BASE_URL}/reminders/${id}`, { method: 'DELETE' });
      fetchReminders();
      addBotMessage(`Reminder deleted, ${userName}!`);
    } catch (error) {
      console.error('Error deleting reminder:', error);
    }
  };

  const handleQuickReminder = async () => {
    const title = prompt('What do you want to be reminded about?');
    if (!title) return;

    const reminderTime = new Date();
    reminderTime.setHours(reminderTime.getHours() + 1);

    try {
      await fetch(`${API_BASE_URL}/reminders`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title,
          description: `Reminder set at ${new Date().toLocaleTimeString()}`,
          reminder_time: reminderTime.toISOString(),
          notification_before: 10
        })
      });
      fetchReminders();
      addBotMessage(`✅ Reminder set: "${title}" - You'll be notified 10 minutes before, ${userName}!`);
    } catch (error) {
      console.error('Error creating reminder:', error);
    }
  };

  const handleQuickMeeting = async () => {
    const title = prompt('What is the meeting about?');
    if (!title) return;

    const meetingTime = new Date();
    meetingTime.setHours(meetingTime.getHours() + 2);
    const endTime = new Date(meetingTime);
    endTime.setHours(endTime.getHours() + 1);

    try {
      await fetch(`${API_BASE_URL}/meetings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title,
          description: `Meeting scheduled at ${new Date().toLocaleTimeString()}`,
          start_time: meetingTime.toISOString(),
          end_time: endTime.toISOString(),
          location: ''
        })
      });
      fetchMeetings();
      addBotMessage(`📅 Meeting scheduled: "${title}" - I'll remind you 10 minutes before, ${userName}!`);
    } catch (error) {
      console.error('Error creating meeting:', error);
    }
  };

  const formatTime = (isoString) => {
    const date = new Date(isoString);
    return date.toLocaleString();
  };

  return (
    <div className="app-container">
      <header className="app-header">
        <div className="header-top">
          <h1>🤖 AI Personal Assistant</h1>
          <div className="header-info">
            <span className="time-display">🕐 {currentTime}</span>
            {userName && <span className="user-name">👤 {userName}</span>}
          </div>
        </div>
        <p>Your 24/7 Smart Schedule Manager • Say "Hey AI" to activate voice control</p>
      </header>

      <div className="voice-control">
        <button 
          className={`voice-btn ${isListening ? 'listening' : ''}`}
          onClick={isListening ? stopListening : startListening}
        >
          {isListening ? '🎤 Listening...' : '🎙️ Start Voice Control'}
        </button>
      </div>

      <div className="tab-navigation">
        <button
          className={`tab-btn ${activeTab === 'chat' ? 'active' : ''}`}
          onClick={() => setActiveTab('chat')}
        >
          💬 Chat
        </button>
        <button
          className={`tab-btn ${activeTab === 'reminders' ? 'active' : ''}`}
          onClick={() => setActiveTab('reminders')}
        >
          ⏰ Reminders ({reminders.length})
        </button>
        <button
          className={`tab-btn ${activeTab === 'meetings' ? 'active' : ''}`}
          onClick={() => setActiveTab('meetings')}
        >
          📅 Meetings ({meetings.length})
        </button>
        <button
          className={`tab-btn ${activeTab === 'notifications' ? 'active' : ''}`}
          onClick={() => setActiveTab('notifications')}
        >
          🔔 Notifications ({notifications.filter(n => !n.read).length})
        </button>
      </div>

      <div className="tab-content">
        {activeTab === 'chat' && (
          <div className="chat-container">
            <div className="messages-list">
              {messages.map((msg) => (
                <div key={msg.id} className={`message message-${msg.type}`}>
                  <div className="message-content">{msg.text}</div>
                </div>
              ))}
              {loading && (
                <div className="message message-bot">
                  <div className="message-content typing">Thinking...</div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            <form onSubmit={handleSendMessage} className="chat-input-form">
              <input
                type="text"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                placeholder="Type your message or say 'Hey AI'..."
                className="chat-input"
              />
              <button type="submit" className="send-btn" disabled={loading}>
                Send
              </button>
            </form>
          </div>
        )}

        {activeTab === 'reminders' && (
          <div className="reminders-container">
            <button onClick={handleQuickReminder} className="action-btn">
              ➕ Add Reminder
            </button>

            {reminders.length === 0 ? (
              <p className="empty-state">No reminders yet, {userName || 'friend'}!</p>
            ) : (
              <div className="items-list">
                {reminders.map((reminder) => (
                  <div key={reminder.id} className="item-card">
                    <div className="item-header">
                      <h3>{reminder.title}</h3>
                      <button
                        onClick={() => handleDeleteReminder(reminder.id)}
                        className="delete-btn"
                      >
                        ✕
                      </button>
                    </div>
                    <p className="item-description">{reminder.description}</p>
                    <p className="item-time">🕐 {formatTime(reminder.reminder_time)}</p>
                    <p className="item-meta">
                      Notify 10 minutes before • {reminder.notified ? 'Notified ✓' : 'Pending'}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === 'meetings' && (
          <div className="meetings-container">
            <button onClick={handleQuickMeeting} className="action-btn">
              ➕ Schedule Meeting
            </button>

            {meetings.length === 0 ? (
              <p className="empty-state">No upcoming meetings, {userName || 'friend'}!</p>
            ) : (
              <div className="items-list">
                {meetings.map((meeting) => (
                  <div key={meeting.id} className="item-card">
                    <div className="item-header">
                      <h3>{meeting.title}</h3>
                    </div>
                    {meeting.description && (
                      <p className="item-description">{meeting.description}</p>
                    )}
                    <p className="item-time">📅 {formatTime(meeting.start_time)}</p>
                    {meeting.location && (
                      <p className="item-meta">📍 {meeting.location}</p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === 'notifications' && (
          <div className="notifications-container">
            {notifications.length === 0 ? (
              <p className="empty-state">No notifications yet, {userName || 'friend'}!</p>
            ) : (
              <div className="items-list">
                {notifications.map((notif) => (
                  <div
                    key={notif.id}
                    className={`notification-card ${notif.read ? 'read' : 'unread'}`}
                  >
                    <p>{notif.message}</p>
                    <p className="notification-time">
                      {new Date(notif.sent_at).toLocaleTimeString()}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
