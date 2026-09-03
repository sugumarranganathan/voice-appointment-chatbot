# 🎙️ Voice Appointment Chatbot

## AI-Powered Appointment Scheduling System

A voice-enabled AI appointment scheduling application that allows users to manage appointments using natural language and voice commands.

The system converts a user's speech into text, understands the appointment request using an LLM, validates the extracted information, performs the requested appointment operation, sends email confirmations, generates an AI voice response, and supports automatic appointment reminders.

### 🌐 Live Demo

**Google Cloud Run:**  
https://voice-appointment-chatbot-6zrnqgkk7q-el.a.run.app

---

## 📌 Problem Statement

Traditional appointment scheduling systems usually require users to:

- Open a booking website or application
- Manually enter their name
- Select a date and time
- Enter the purpose of the appointment
- Provide an email address
- Repeat the process when cancelling or rescheduling
- Manually check their appointments
- Remember upcoming appointments themselves

This process can be time-consuming and inconvenient, especially when users prefer speaking instead of typing.

### The main problem

**How can we build an AI-powered appointment system that understands natural human voice requests and automatically handles booking, cancellation, rescheduling, appointment listing, email confirmation, voice responses, and reminders?**

---

## 💡 Solution

The **Voice Appointment Chatbot** provides a conversational, voice-first solution.

The user simply speaks a request such as:

> "Book an appointment for Anusha tomorrow at 5 PM."

The application:

1. 🎙️ Records the user's voice
2. 📝 Converts speech to text using Whisper
3. 🧠 Uses an LLM to understand the request
4. 📋 Converts the request into structured appointment JSON
5. ✅ Validates the required fields and date/time formats
6. 📅 Performs the requested appointment operation
7. 📧 Sends an email confirmation when applicable
8. 🔊 Generates an AI voice response
9. ⏰ Supports appointment reminders

The chatbot supports four primary appointment intents:

- `book`
- `cancel`
- `reschedule`
- `list`

---

## 🚀 Key Features

### 🎙️ Voice Input
Users can record appointment requests directly through the browser microphone.

### 📝 Speech-to-Text
Voice input is transcribed into text using **Whisper**.

### 🧠 AI Understanding
The application uses **Groq + GPT-OSS-20B** to understand natural-language appointment requests.

### 📅 Appointment Management

| Operation | Description |
|---|---|
| Book | Create a new appointment |
| Cancel | Cancel an existing appointment |
| Reschedule | Change an existing appointment |
| List | Display booked appointments |

### 📋 Structured Appointment Data

The AI converts natural language into structured JSON:

```json
{
  "intent": "book",
  "appointment_id": "",
  "name": "Anusha",
  "appointment_date": "04-09-2026",
  "appointment_time": "17:00",
  "purpose": "Consultation",
  "email": "example@gmail.com"
}
```

### 📧 Email Confirmation

When an email address is available, the application can use it for appointment confirmation.

If an email address was not included in the voice request, the interface provides a **Complete Appointment Details** section where the user can enter an email address before completing the booking.

### 🔊 AI Voice Reply

After processing the request, the chatbot generates a spoken response so the user does not need to read the result.

### ⏰ Automatic Reminders

Appointments support reminders such as:

> 15 minutes before the appointment

The appointment status also displays whether the reminder has been sent.

### ☁️ Cloud Deployment

The application is deployed on **Google Cloud Run**, providing a publicly accessible web application.

---

# 🏗️ System Architecture

```text
                    ┌──────────────────────┐
                    │       User           │
                    │  Natural Voice Input │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Browser Microphone   │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │      Whisper         │
                    │  Speech-to-Text      │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │     Groq API         │
                    │    GPT-OSS-20B       │
                    │   AI Understanding   │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ JSON Appointment     │
                    │       Schema         │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │      Validation      │
                    │ Name / Date / Time   │
                    │ Intent / Email       │
                    └──────────┬───────────┘
                               │
                               ▼
              ┌────────────────┴────────────────┐
              │                                 │
              ▼                                 ▼
     ┌──────────────────┐             ┌──────────────────┐
     │ Appointment      │             │ Email / Reminder │
     │ Operations       │             │ Processing       │
     │                  │             │                  │
     │ Book             │             │ Confirmation     │
     │ Cancel           │             │ Reminder         │
     │ Reschedule       │             │                  │
     │ List             │             │                  │
     └─────────┬────────┘             └──────────────────┘
               │
               ▼
     ┌──────────────────────┐
     │    AI Voice Reply    │
     │  Text-to-Speech      │
     └──────────┬───────────┘
                │
                ▼
        ┌───────────────┐
        │     User      │
        └───────────────┘
```

---

# 🔄 Application Workflow

```text
PHASE 1 — Requirements
        ↓
Define BOOK / CANCEL / RESCHEDULE / LIST
        ↓
Define JSON Schema
        ↓
Define Date / Time Rules

PHASE 2 — Groq Setup
        ↓
Configure API Key
        ↓
Initialize Groq Client

PHASE 3 — Speech-to-Text
        ↓
Browser Microphone
        ↓
Whisper
        ↓
Transcription

PHASE 4 — AI Understanding
        ↓
GPT-OSS-20B
        ↓
Intent Detection
        ↓
Appointment JSON

PHASE 5 — Validation
        ↓
Name
        ↓
Date
        ↓
Time
        ↓
Email
        ↓
Intent

PHASE 6 — Appointment Operation
        ↓
Book / Cancel / Reschedule / List

PHASE 7 — Communication
        ↓
Email Confirmation
        ↓
AI Voice Reply

PHASE 8 — Reminder
        ↓
Scheduled Reminder
        ↓
Reminder Status
```

---

# 🧠 AI Appointment Understanding

The AI is instructed to return a predictable JSON structure instead of free-form text.

## Supported Intent Values

```text
book
cancel
reschedule
list
```

## Date Format

```text
DD-MM-YYYY
```

Example:

```text
04-09-2026
```

## Time Format

```text
HH:MM
```

Example:

```text
17:00
```

## Relative Date Rules

The AI understands common natural-language date expressions.

Examples:

```text
today
tomorrow
```

- **today** → use today's date
- **tomorrow** → calculate tomorrow's date based on the current date

---

# 🧪 Example Voice Requests

### 1. Book an Appointment

**User:**

> "Book an appointment for Anusha tomorrow at 5 PM for a consultation."

**AI Output:**

```json
{
  "intent": "book",
  "appointment_id": "",
  "name": "Anusha",
  "appointment_date": "04-09-2026",
  "appointment_time": "17:00",
  "purpose": "Consultation",
  "email": ""
}
```

If the email was not provided, the application can request it through the **Complete Appointment Details** section.

---

### 2. List Appointments

**User:**

> "Show me all appointments."

**AI Output:**

```json
{
  "intent": "list",
  "appointment_id": "",
  "name": "",
  "appointment_date": "",
  "appointment_time": "",
  "purpose": "",
  "email": ""
}
```

The application then displays the booked appointments.

---

### 3. Cancel an Appointment

**User:**

> "Cancel appointment number 3."

The AI identifies:

```json
{
  "intent": "cancel",
  "appointment_id": "3"
}
```

The application then processes the cancellation.

---

### 4. Reschedule an Appointment

**User:**

> "Reschedule appointment number 2 to September 21 at 2:30 PM."

The application updates the appointment date and time.

Example:

```text
Appointment ID : 2
Date           : 21-09-2026
Time           : 14:30
```

---

# 🖥️ User Interface

The application provides a simple voice-based interface containing:

- 🎙️ Voice recording component
- 🟠 Process Voice button
- 🗑️ Clear button
- 📝 Transcription section
- 🧠 AI Understanding section
- 📢 Status section
- 🔊 AI Voice Reply section
- 📧 Complete Appointment Details section
- 📋 Appointments section

The interface allows the user to see both the original transcription and the structured AI interpretation before viewing the final appointment status.

---

# 🛠️ Technology Stack

| Technology | Purpose |
|---|---|
| Python | Backend application |
| Gradio | Web-based user interface |
| Groq | Fast LLM inference |
| GPT-OSS-20B | Natural-language understanding |
| Whisper | Speech-to-text |
| Text-to-Speech | AI voice response |
| Email / SMTP | Appointment confirmation |
| Google Cloud Run | Cloud deployment |
| GitHub | Source-code management |

---

# 📁 Suggested Project Structure

```text
voice-appointment-chatbot/
│
├── app.py
├── requirements.txt
├── Dockerfile
├── README.md
├── .gitignore
│
├── services/
│   ├── speech_to_text.py
│   ├── ai_understanding.py
│   ├── appointment_service.py
│   ├── email_service.py
│   ├── voice_reply.py
│   └── reminder_service.py
│
├── data/
│   └── appointments.json
│
└── screenshots/
    ├── voice-input.png
    ├── ai-understanding.png
    ├── appointment-status.png
    ├── ai-voice-reply.png
    └── appointments-list.png
```

> Adjust the filenames above to match the actual files in your repository.

---

# 🔐 Environment Variables

Never commit API keys, passwords, or email credentials to GitHub.

Example:

```env
GROQ_API_KEY=your_groq_api_key
EMAIL_ADDRESS=your_email@gmail.com
EMAIL_PASSWORD=your_email_app_password
```

Add secrets through the deployment environment rather than hard-coding them in Python.

Example `.gitignore`:

```gitignore
.env
__pycache__/
*.pyc
.venv/
venv/
```

---

# ☁️ Google Cloud Run Deployment

The application can be containerized and deployed to Google Cloud Run.

General deployment flow:

```text
Local Application
       ↓
Dockerfile
       ↓
Container Image
       ↓
Google Cloud
       ↓
Cloud Run
       ↓
Public HTTPS URL
```

The deployed application is available at:

**https://voice-appointment-chatbot-6zrnqgkk7q-el.a.run.app**

---

# ▶️ Run Locally

## 1. Clone the repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd voice-appointment-chatbot
```

## 2. Create a virtual environment

```bash
python -m venv venv
```

### Windows

```bash
venv\Scripts\activate
```

### Linux / macOS

```bash
source venv/bin/activate
```

## 3. Install dependencies

```bash
pip install -r requirements.txt
```

## 4. Configure environment variables

Create a `.env` file:

```env
GROQ_API_KEY=your_groq_api_key
EMAIL_ADDRESS=your_email@gmail.com
EMAIL_PASSWORD=your_email_app_password
```

## 5. Start the application

```bash
python app.py
```

Then open the local Gradio URL displayed in the terminal.

---

# 🔒 Security Considerations

- Store API keys in environment variables or Google Cloud Secret Manager.
- Do not commit `.env` files.
- Do not expose email passwords in source code.
- Validate user-provided appointment information.
- Validate email addresses before sending confirmation messages.
- Restrict appointment IDs and operations to valid records.
- Use HTTPS in production.

---

# 🎯 Benefits

### For Users

- Hands-free appointment scheduling
- Natural-language interaction
- Faster booking workflow
- Voice confirmation
- Email confirmation
- Appointment reminders
- Easy cancellation and rescheduling

### For Businesses

- Reduces manual scheduling work
- Provides a conversational interface
- Automates appointment communication
- Improves user experience
- Can be deployed as a cloud-based application

---

# 🔮 Future Enhancements

Possible future improvements include:

- 👤 User authentication
- 🗄️ PostgreSQL / Cloud SQL database
- 📅 Google Calendar integration
- 📱 SMS / WhatsApp reminders
- 🔐 Role-based access
- 🌍 Multi-language voice support
- 📊 Admin dashboard
- 📈 Appointment analytics
- 🔄 Recurring appointments
- 🏢 Multiple staff calendars
- 🧑‍💼 Business-specific working hours
- 🚫 Automatic conflict detection
- 🧠 More advanced conversational memory

---

# 📸 Screenshots

Add the project screenshots to a `screenshots/` directory and reference them here.

Example:

```markdown
## Voice Appointment

![Voice Appointment](screenshots/voice-input.png)

## AI Understanding

![AI Understanding](screenshots/ai-understanding.png)

## Appointment Status

![Appointment Status](screenshots/appointment-status.png)

## AI Voice Reply

![AI Voice Reply](screenshots/ai-voice-reply.png)

## Appointment List

![Appointment List](screenshots/appointments-list.png)
```

---

# 📌 Project Highlights

This project demonstrates an end-to-end **AI + Voice + Cloud** application:

```text
Voice
  ↓
Speech-to-Text
  ↓
LLM
  ↓
Intent Detection
  ↓
Structured JSON
  ↓
Validation
  ↓
Appointment Management
  ↓
Email Confirmation
  ↓
Voice Response
  ↓
Reminder
  ↓
Cloud Deployment
```

It combines **Generative AI, speech processing, structured data extraction, application logic, email automation, and cloud deployment** into a practical real-world appointment scheduling solution.

---

# 👨‍💻 Author

**Sugumar R**

AI / Data Science / Generative AI Project

---

## ⭐ If you find this project useful

Consider giving the repository a ⭐ on GitHub.
