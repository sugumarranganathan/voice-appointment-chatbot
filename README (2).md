# 🎙️ AI Voice Assistant for Automated Appointment Scheduling

## AI-Powered Voice Appointment Scheduling System

A voice-enabled AI appointment scheduling application that allows users to manage appointments using natural-language voice commands.

The system converts speech into text, understands the request using an LLM, extracts structured appointment information, validates the request, performs the appointment operation, provides an AI voice response, and supports email confirmation and appointment reminders.

---

## 🌐 Live Demo

**Google Cloud Run:**  
https://voice-appointment-chatbot-reminder-498371403633.asia-south1.run.app/

## 📦 GitHub Repository

**Repository:**  
https://github.com/sugumarranganathan/voice-appointment-chatbot

---

# 🎯 Problem Statement

Traditional appointment scheduling systems often require users to manually:

- Open a booking application
- Enter their name
- Select a date
- Select a time
- Enter the appointment purpose
- Enter an email address
- Search for an existing appointment before cancelling
- Manually change details when rescheduling
- Check their appointments repeatedly
- Remember upcoming appointments

This can be time-consuming and inconvenient, particularly for users who prefer speaking rather than typing.

### The problem

**How can we build an AI-powered appointment scheduling system that understands natural human voice requests and automatically handles booking, cancellation, rescheduling, appointment listing, confirmation, voice responses, and reminders?**

---

# 💡 Solution

The **AI Voice Assistant for Automated Appointment Scheduling** provides a conversational, voice-first solution.

A user can simply say:

> "Book an appointment for Anusha tomorrow at 5 PM."

The application processes the request through the following pipeline:

```text
🎙️ Voice Input
      ↓
📝 Speech-to-Text
      ↓
🧠 AI Understanding
      ↓
📋 Structured Appointment JSON
      ↓
✅ Validation
      ↓
📅 Appointment Operation
      ↓
📧 Email Confirmation
      ↓
🔊 AI Voice Reply
      ↓
⏰ Appointment Reminder
```

The system supports four main appointment operations:

```text
BOOK
CANCEL
RESCHEDULE
LIST
```

In the user interface, these are presented as:

**Book • Cancel • Reschedule • View Appointments**

---

# ✨ Key Features

## 🎙️ 1. Voice Input

Users can record an appointment request directly through the browser microphone.

### Example

> "Show me all appointments."

The voice input area is presented to the user as:

**Tell us what you need**

---

## 📝 2. Speech-to-Text

The recorded voice is converted into text using **Whisper**.

```text
User Speech
    ↓
Whisper
    ↓
Text Transcription
```

The resulting request is displayed in the UI under:

**Your Request**

---

## 🧠 3. AI Understanding

The transcribed request is sent to **Groq** using **GPT-OSS-20B** to understand the user's intent and extract appointment information.

The model converts natural language into a predictable JSON structure.

---

## 📋 4. Structured Appointment JSON

Example:

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

The extracted information is then presented to the user in a **user-friendly appointment details format**, rather than requiring the user to interpret raw JSON.

### Supported intents

```text
book
cancel
reschedule
list
```

### Date format

```text
DD-MM-YYYY
```

### Time format

```text
HH:MM
```

### Relative date handling

The system supports natural expressions such as:

```text
today
tomorrow
```

Rules:

- `today` → use the current date
- `tomorrow` → calculate the next date based on the current date

---

# 📅 Appointment Operations

## Book

Example:

> "Book an appointment for Anusha tomorrow at 5 PM for a consultation."

The system extracts the appointment information, validates it, and creates the appointment.

---

## Cancel

Example:

> "Cancel appointment number 3."

The AI identifies the cancellation intent and appointment ID.

Example:

```json
{
  "intent": "cancel",
  "appointment_id": "3"
}
```

---

## Reschedule

Example:

> "Reschedule appointment number 2 to September 21 at 2:30 PM."

The system updates the appointment.

Example result:

```text
Appointment ID : 2
Date           : 21-09-2026
Time           : 14:30
```

---

## View Appointments

Example:

> "Show me all appointments."

The system retrieves and displays the available appointments.

The UI action is presented as:

**View Appointments**

---

# 📧 Email Confirmation

The application supports email confirmation for appointments.

If an email address is not included in the voice request, the interface provides a **Complete Appointment Details** section where the user can enter an email address before completing the booking.

### Example flow

```text
Voice Request
     ↓
Email provided?
    ↙       ↘
  Yes        No
  ↓           ↓
Continue   Enter email
    ↘       ↙
       ↓
Complete Booking
       ↓
Email Confirmation
```

> **Note:** SMTP (Simple Mail Transfer Protocol) is the standard mechanism used by applications to send email through an email server. The actual email configuration should be kept in environment variables or cloud secrets.

---

# 🔊 AI Voice Reply

After processing the appointment request, the chatbot generates an AI voice response.

Example:

> "Your appointment has been successfully rescheduled to September 21 at 2:30 PM."

This provides a conversational experience without requiring the user to read the result.

---

# ⏰ Automatic Reminders

Appointments can contain reminder information such as:

```text
Reminder       : 15 minutes before
Reminder Sent  : No
```

The application can use this information to support automated appointment reminders.

---

# 🏗️ System Architecture

```text
                    ┌──────────────────────┐
                    │        USER          │
                    │  Voice Appointment   │
                    │       Request        │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Browser Microphone   │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │       Whisper        │
                    │   Speech-to-Text     │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │       Groq API       │
                    │     GPT-OSS-20B      │
                    │  AI Understanding    │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Structured JSON      │
                    │ Appointment Data     │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │     Validation       │
                    │ Name / Date / Time   │
                    │ Intent / Email       │
                    └──────────┬───────────┘
                               │
                               ▼
              ┌────────────────┴────────────────┐
              │                                 │
              ▼                                 ▼
     ┌──────────────────┐             ┌──────────────────┐
     │ Appointment      │             │ Communication    │
     │ Operations       │             │                  │
     │                  │             │ Email            │
     │ Book             │             │ Voice Reply      │
     │ Cancel           │             │ Reminder         │
     │ Reschedule       │             │                  │
     │ List             │             │                  │
     └─────────┬────────┘             └──────────────────┘
               │
               ▼
         ┌───────────────┐
         │     USER      │
         │ Final Result  │
         └───────────────┘
```

---

# 🔄 End-to-End Application Workflow

```text
PHASE 1 — REQUIREMENTS
        ↓
Define BOOK / CANCEL / RESCHEDULE / LIST
        ↓
Define JSON Schema
        ↓
Define Date & Time Rules
        ↓
PHASE 2 — GROQ SETUP
        ↓
Configure Groq API Key
        ↓
Initialize Groq Client
        ↓
PHASE 3 — SPEECH-TO-TEXT
        ↓
Browser Microphone
        ↓
Whisper
        ↓
Transcription
        ↓
PHASE 4 — AI UNDERSTANDING
        ↓
GPT-OSS-20B
        ↓
Intent Detection
        ↓
Appointment JSON
        ↓
PHASE 5 — VALIDATION
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
        ↓
PHASE 6 — APPOINTMENT OPERATION
        ↓
Book / Cancel / Reschedule / List
        ↓
PHASE 7 — COMMUNICATION
        ↓
Email Confirmation
        ↓
AI Voice Reply
        ↓
PHASE 8 — REMINDER
        ↓
Scheduled Reminder
        ↓
Reminder Status
```

---

# 🖥️ User Interface

The application uses a voice-first Gradio interface.

### Main UI heading

**AI Voice Assistant for Automated Appointment Scheduling**

### Supported actions

**Book • Cancel • Reschedule • View Appointments**

### User request area

**Tell us what you need**

### Request display

**Your Request**

### Extracted details

**Extracted Appointment Details**

The extracted appointment information is displayed in a user-friendly format.

### Other interface components

- 🎙️ Voice recording component
- ▶️ Process Voice button
- Clear Request button
- 📌 Status section
- 🔊 AI Voice Reply section
- 📧 Email Address input
- ✅ Complete Booking button
- 📅 Appointments section

---

# 🛠️ Technology Stack

| Technology | Purpose |
|---|---|
| Python | Application/backend development |
| Gradio | Web-based user interface |
| Groq API | LLM inference |
| GPT-OSS-20B | Natural-language understanding |
| Whisper | Speech-to-text |
| Text-to-Speech | AI voice response |
| Email / SMTP | Email confirmation |
| Google Cloud Run | Cloud deployment |
| Docker | Containerization |
| GitHub | Source-code management |

---

# 🐙 GitHub Repository Workflow

The project source code is maintained in GitHub and the deployed application runs on Google Cloud Run.

```text
                 👨‍💻 Developer
                      │
                      ▼
                Local Project
                      │
                git add / commit
                      │
                      ▼
                  🐙 GitHub
                      │
                      ▼
              Source Code Repository
                      │
                      ▼
               ┌─────────────────┐
               │ Project Files   │
               │                 │
               │ app.py          │
               │ app_source.py   │
               │ Dockerfile      │
               │ requirements.txt│
               │ README.md       │
               └────────┬────────┘
                        │
                        ▼
                  ☁️ Google Cloud
                        │
                        ▼
                     Cloud Run
                        │
                        ▼
                  🌐 Live Web App
                        │
                        ▼
                      👤 User
```

### Current GitHub repository structure

```text
voice-appointment-chatbot/
│
├── Dockerfile
├── README.md
├── app.py
├── app_source.py
└── requirements.txt
```

---

# ☁️ Google Cloud Run Deployment Workflow

The application is containerized using Docker and deployed to Google Cloud Run.

```text
Source Code
    ↓
Dockerfile
    ↓
Docker Build
    ↓
Container Image
    ↓
Google Cloud
    ↓
Cloud Run Service
    ↓
Public HTTPS URL
```

The application uses the Cloud Run service:

```text
voice-appointment-chatbot-reminder
```

The current container image deployment uses the `appointment-v8` image.

---

# 📁 Project Structure

```text
voice-appointment-chatbot/
│
├── Dockerfile
├── README.md
├── app.py
├── app_source.py
└── requirements.txt
```

---

# 🔐 Environment Variables & Security

Never commit API keys, passwords, or email credentials to GitHub.

Example:

```env
GROQ_API_KEY=your_groq_api_key
EMAIL_ADDRESS=your_email@gmail.com
EMAIL_PASSWORD=your_email_app_password
```

Use environment variables or Google Cloud secrets for sensitive information.

Recommended `.gitignore`:

```gitignore
.env
__pycache__/
*.pyc
.venv/
venv/
```

---

# 🧪 Example End-to-End Interaction

### User says

> "Book an appointment for Anusha tomorrow at 5 PM."

### Step 1 — Transcription

```text
Book an appointment for Anusha tomorrow at 5 PM.
```

### Step 2 — AI Understanding

```json
{
  "intent": "book",
  "appointment_id": "",
  "name": "Anusha",
  "appointment_date": "05-09-2026",
  "appointment_time": "17:00",
  "purpose": "",
  "email": ""
}
```

### Step 3 — Validation

```text
Intent       → Valid
Name         → Valid
Date         → Valid
Time         → Valid
Email        → Required if confirmation is needed
```

### Step 4 — Complete Booking

If the email was missing, the user can enter it in the **Complete Appointment Details** section.

### Step 5 — Confirmation

The appointment is displayed in the appointment list and the system can provide an email confirmation and AI voice response.

---

# 🎯 Benefits

## For Users

- Hands-free appointment scheduling
- Natural-language interaction
- Faster booking
- Voice confirmation
- Email confirmation
- Easy cancellation
- Easy rescheduling
- Appointment listing
- Reminder support

## For Businesses

- Reduces manual scheduling work
- Automates repetitive appointment operations
- Improves customer experience
- Provides conversational AI interaction
- Can be deployed as a cloud application

---

# 🚀 Project Highlights

This project demonstrates an end-to-end **AI + Voice + Automation + Cloud** application.

```text
🎙️ Voice
   ↓
📝 Speech-to-Text
   ↓
🧠 Generative AI
   ↓
🎯 Intent Detection
   ↓
📋 Structured JSON
   ↓
✅ Validation
   ↓
📅 Appointment Management
   ↓
📧 Email Confirmation
   ↓
🔊 Voice Response
   ↓
⏰ Reminder
   ↓
🐙 GitHub
   ↓
🐳 Docker
   ↓
☁️ Google Cloud Run
   ↓
🌐 Live Application
```

The project demonstrates practical implementation of:

- Generative AI
- Large Language Models
- Speech-to-Text
- Natural-language understanding
- Structured JSON extraction
- Validation
- Appointment automation
- Email communication
- Voice response
- Docker containerization
- GitHub source-code management
- Google Cloud deployment

---

# 👨‍💻 Developed by

**R. Sugumar, M.B.A.**
