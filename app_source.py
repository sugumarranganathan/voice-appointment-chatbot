
# ============================================================
# ORIGINAL NOTEBOOK CODE CELL 1
# ============================================================

# ============================================================
# INSTALL REQUIRED LIBRARIES
# ============================================================

!pip -q install groq gradio pandas python-dotenv


# ============================================================
# ORIGINAL NOTEBOOK CODE CELL 2
# ============================================================

# ============================================================
# CONFIGURE API KEYS
# ============================================================

import os
from google.colab import userdata

GROQ_API_KEY = userdata.get("GROQ_API_KEY_V1")

if not GROQ_API_KEY:
    raise ValueError(
        "❌ GROQ_API_KEY not found in Colab Secrets."
    )

os.environ["GROQ_API_KEY"] = GROQ_API_KEY

print("✅ Groq API key loaded successfully.")


# ============================================================
# ORIGINAL NOTEBOOK CODE CELL 3
# ============================================================

# ============================================================
# INITIALIZE GROQ CLIENT
# ============================================================

from groq import Groq

groq_client = Groq(api_key=GROQ_API_KEY)

print("✅ Groq client initialized successfully.")


# ============================================================
# ORIGINAL NOTEBOOK CODE CELL 4
# ============================================================

# ============================================================
# INSTALL SPEECH RECOGNITION SUPPORT
# ============================================================

!pip -q install openai-whisper

print("✅ Whisper installed successfully.")


# ============================================================
# ORIGINAL NOTEBOOK CODE CELL 5
# ============================================================

# ============================================================
# SPEECH-TO-TEXT FUNCTION
# ============================================================

def transcribe_audio(audio_file):
    """
    Convert recorded/uploaded audio into text
    using Groq Whisper.
    """

    if not audio_file:
        return ""

    try:
        with open(audio_file, "rb") as file:
            transcription = groq_client.audio.transcriptions.create(
                file=file,
                model="whisper-large-v3-turbo",
                response_format="json",
                language="en",
                temperature=0.0
            )

        text = transcription.text.strip()

        print("🎤 Transcription:")
        print(text)

        return text

    except Exception as e:
        print(f"❌ Transcription error: {e}")
        return ""


print("✅ Speech-to-text function created successfully.")


# ============================================================
# ORIGINAL NOTEBOOK CODE CELL 6
# ============================================================

# ============================================================
# AI APPOINTMENT UNDERSTANDING
# ============================================================

import json


AI_MODEL = "openai/gpt-oss-20b"


def understand_appointment(user_text):
    """
    Convert natural-language appointment requests
    into structured appointment information.
    """

    if not user_text or not user_text.strip():
        return None

    system_prompt = """
You are an appointment scheduling assistant.

Extract appointment information from the user's request.

Return ONLY valid JSON with exactly these fields:

{
    "intent": "book | cancel | reschedule | list",
    "name": "",
    "appointment_date": "",
    "appointment_time": "",
    "purpose": "",
    "email": ""
}

Rules:

1. intent must be one of:
   book, cancel, reschedule, list

2. appointment_date must use:
   DD-MM-YYYY

3. appointment_time must use:
   HH:MM in 24-hour format

4. If the user says "tomorrow", calculate tomorrow's
   date based on today's date.

5. If the user says "today", use today's date.

6. If information is missing, keep that field as "".

7. Do not invent missing information.

8. Extract the person's name carefully.

9. Extract the email address if provided.

10. Extract the purpose if provided.

11. Return ONLY valid JSON.
"""

    try:

        response = groq_client.chat.completions.create(
            model=AI_MODEL,

            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_text
                }
            ],

            temperature=0,

            response_format={
                "type": "json_object"
            }
        )

        raw_response = response.choices[0].message.content

        print("🤖 Raw AI Response:")
        print(raw_response)

        result = json.loads(raw_response)

        print("\n🤖 AI Understanding:")
        print(json.dumps(result, indent=2))

        return result

    except Exception as e:

        print("\n❌ AI Understanding Error:")
        print(type(e).__name__)
        print(str(e))

        return None


print("✅ AI appointment understanding updated successfully.")
print(f"🤖 AI Model: {AI_MODEL}")


# ============================================================
# ORIGINAL NOTEBOOK CODE CELL 7
# ============================================================

# ============================================================
# INITIALIZE SQLITE DATABASE
# ============================================================

import sqlite3
import os

DB_NAME = "appointments.db"


# Remove the database if it was created with the previous format
if os.path.exists(DB_NAME):
    os.remove(DB_NAME)


def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


conn = get_db_connection()

cursor = conn.cursor()

cursor.execute("""
CREATE TABLE appointments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    appointment_date TEXT NOT NULL,
    appointment_time TEXT NOT NULL,
    purpose TEXT,
    email TEXT NOT NULL,
    reminder_minutes INTEGER DEFAULT 15,
    reminder_sent INTEGER DEFAULT 0,
    reminder_sent_at TEXT
)
""")

conn.commit()
conn.close()

print("✅ SQLite database initialized successfully.")
print(f"📁 Database: {DB_NAME}")
print("📅 Date format: DD-MM-YYYY")


# ============================================================
# ORIGINAL NOTEBOOK CODE CELL 8
# ============================================================

# ============================================================
# DATE AND TIME HANDLING
# ============================================================

from datetime import datetime, date


def validate_date(date_text):
    """
    Validate appointment date in DD-MM-YYYY format.
    """

    try:
        appointment_date = datetime.strptime(
            date_text.strip(),
            "%d-%m-%Y"
        ).date()

        if appointment_date < date.today():
            return False

        return True

    except (ValueError, TypeError):
        return False


def validate_time(time_text):
    """
    Validate time in HH:MM 24-hour format.
    """

    try:
        datetime.strptime(
            time_text.strip(),
            "%H:%M"
        )
        return True

    except (ValueError, TypeError):
        return False


def format_time(time_text):
    """
    Convert common time formats into HH:MM.
    """

    if not time_text:
        return ""

    formats = [
        "%H:%M",
        "%I:%M %p",
        "%I %p",
        "%I:%M%p",
        "%I%p"
    ]

    for fmt in formats:
        try:
            return datetime.strptime(
                time_text.strip().upper(),
                fmt
            ).strftime("%H:%M")

        except ValueError:
            continue

    return ""


print("✅ Date and time functions created successfully.")
print("📅 Date format: DD-MM-YYYY")
print("⏰ Time format: HH:MM")


# ============================================================
# ORIGINAL NOTEBOOK CODE CELL 9
# ============================================================

# ============================================================
# BOOK APPOINTMENT
# ============================================================

import re


def is_valid_email(email):
    """Validate email address."""

    if not email:
        return False

    pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"

    return re.match(
        pattern,
        email.strip()
    ) is not None


def book_appointment(
    name,
    appointment_date,
    appointment_time,
    purpose,
    email
):
    """
    Book a new appointment.

    Date format: DD-MM-YYYY
    Time format: HH:MM
    """

    # --------------------------------------------------------
    # Validate name
    # --------------------------------------------------------

    if not name or not name.strip():
        return {
            "success": False,
            "message": "❌ Name is required."
        }

    # --------------------------------------------------------
    # Validate date
    # --------------------------------------------------------

    if not appointment_date:
        return {
            "success": False,
            "message": "❌ Appointment date is required."
        }

    if not validate_date(appointment_date):
        return {
            "success": False,
            "message": (
                "❌ Invalid date. "
                "Please use DD-MM-YYYY format."
            )
        }

    # --------------------------------------------------------
    # Format time
    # --------------------------------------------------------

    if not appointment_time:
        return {
            "success": False,
            "message": "❌ Appointment time is required."
        }

    appointment_time = format_time(
        appointment_time
    )

    if not appointment_time:
        return {
            "success": False,
            "message": (
                "❌ Invalid time. "
                "Example: 10:30 AM"
            )
        }

    # --------------------------------------------------------
    # Validate email
    # --------------------------------------------------------

    if not is_valid_email(email):
        return {
            "success": False,
            "message": "❌ Please provide a valid email address."
        }

    # --------------------------------------------------------
    # Check duplicate appointment
    # --------------------------------------------------------

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id
        FROM appointments
        WHERE appointment_date = ?
        AND appointment_time = ?
    """, (
        appointment_date.strip(),
        appointment_time
    ))

    existing = cursor.fetchone()

    if existing:
        conn.close()

        return {
            "success": False,
            "message": (
                f"❌ This time slot is already booked.\n\n"
                f"📅 {appointment_date}\n"
                f"⏰ {appointment_time}"
            )
        }

    # --------------------------------------------------------
    # Insert appointment
    # --------------------------------------------------------

    cursor.execute("""
        INSERT INTO appointments (
            name,
            appointment_date,
            appointment_time,
            purpose,
            email,
            reminder_minutes,
            reminder_sent,
            reminder_sent_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        name.strip(),
        appointment_date.strip(),
        appointment_time,
        purpose.strip() if purpose else "",
        email.strip(),
        15,
        0,
        None
    ))

    appointment_id = cursor.lastrowid

    conn.commit()
    conn.close()

    # --------------------------------------------------------
    # Return success
    # --------------------------------------------------------

    return {
        "success": True,
        "appointment_id": appointment_id,
        "message": (
            "✅ Appointment booked successfully!\n\n"
            f"🆔 Appointment ID: {appointment_id}\n"
            f"👤 Name: {name.strip()}\n"
            f"📅 Date: {appointment_date.strip()}\n"
            f"⏰ Time: {appointment_time}\n"
            f"📝 Purpose: {purpose.strip() if purpose else 'Not specified'}\n"
            f"📧 Email: {email.strip()}\n"
            f"🔔 Reminder: 15 minutes before"
        )
    }


print("✅ Book appointment function created successfully.")


# ============================================================
# ORIGINAL NOTEBOOK CODE CELL 10
# ============================================================

# ============================================================
# TEST BOOKING FUNCTION
# ============================================================

test_result = book_appointment(
    name="Test User",
    appointment_date="15-09-2026",
    appointment_time="10:30 AM",
    purpose="Test Appointment",
    email="test@example.com"
)

print(test_result["message"])


# ============================================================
# ORIGINAL NOTEBOOK CODE CELL 11
# ============================================================

# ============================================================
# CANCEL APPOINTMENT
# ============================================================

def cancel_appointment(appointment_id):
    """
    Cancel an existing appointment using Appointment ID.
    """

    if not appointment_id:
        return {
            "success": False,
            "message": "❌ Appointment ID is required."
        }

    try:
        appointment_id = int(appointment_id)
    except (ValueError, TypeError):
        return {
            "success": False,
            "message": "❌ Invalid Appointment ID."
        }

    conn = get_db_connection()
    cursor = conn.cursor()

    # --------------------------------------------------------
    # Check appointment exists
    # --------------------------------------------------------

    cursor.execute("""
        SELECT *
        FROM appointments
        WHERE id = ?
    """, (appointment_id,))

    appointment = cursor.fetchone()

    if not appointment:
        conn.close()

        return {
            "success": False,
            "message": (
                f"❌ Appointment ID {appointment_id} "
                "was not found."
            )
        }

    # --------------------------------------------------------
    # Delete appointment
    # --------------------------------------------------------

    cursor.execute("""
        DELETE FROM appointments
        WHERE id = ?
    """, (appointment_id,))

    conn.commit()
    conn.close()

    # --------------------------------------------------------
    # Return cancellation result
    # --------------------------------------------------------

    return {
        "success": True,
        "message": (
            "✅ Appointment cancelled successfully!\n\n"
            f"🆔 Appointment ID: {appointment_id}\n"
            f"👤 Name: {appointment['name']}\n"
            f"📅 Date: {appointment['appointment_date']}\n"
            f"⏰ Time: {appointment['appointment_time']}"
        )
    }


print("✅ Cancel appointment function created successfully.")


# ============================================================
# ORIGINAL NOTEBOOK CODE CELL 12
# ============================================================

# ============================================================
# RESCHEDULE APPOINTMENT
# ============================================================

def reschedule_appointment(
    appointment_id,
    new_date,
    new_time
):
    """
    Reschedule an existing appointment.

    Date format: DD-MM-YYYY
    Time format: HH:MM
    """

    # --------------------------------------------------------
    # Validate Appointment ID
    # --------------------------------------------------------

    if not appointment_id:
        return {
            "success": False,
            "message": "❌ Appointment ID is required."
        }

    try:
        appointment_id = int(appointment_id)
    except (ValueError, TypeError):
        return {
            "success": False,
            "message": "❌ Invalid Appointment ID."
        }

    # --------------------------------------------------------
    # Validate new date
    # --------------------------------------------------------

    if not new_date:
        return {
            "success": False,
            "message": "❌ New appointment date is required."
        }

    if not validate_date(new_date):
        return {
            "success": False,
            "message": (
                "❌ Invalid date. "
                "Please use DD-MM-YYYY format."
            )
        }

    # --------------------------------------------------------
    # Format new time
    # --------------------------------------------------------

    if not new_time:
        return {
            "success": False,
            "message": "❌ New appointment time is required."
        }

    new_time = format_time(new_time)

    if not new_time:
        return {
            "success": False,
            "message": "❌ Invalid time."
        }

    # --------------------------------------------------------
    # Connect to database
    # --------------------------------------------------------

    conn = get_db_connection()
    cursor = conn.cursor()

    # --------------------------------------------------------
    # Find existing appointment
    # --------------------------------------------------------

    cursor.execute("""
        SELECT *
        FROM appointments
        WHERE id = ?
    """, (appointment_id,))

    appointment = cursor.fetchone()

    if not appointment:
        conn.close()

        return {
            "success": False,
            "message": (
                f"❌ Appointment ID {appointment_id} "
                "was not found."
            )
        }

    # --------------------------------------------------------
    # Check whether new slot is already booked
    # --------------------------------------------------------

    cursor.execute("""
        SELECT id
        FROM appointments
        WHERE appointment_date = ?
        AND appointment_time = ?
        AND id != ?
    """, (
        new_date.strip(),
        new_time,
        appointment_id
    ))

    existing = cursor.fetchone()

    if existing:
        conn.close()

        return {
            "success": False,
            "message": (
                "❌ The new appointment slot is already booked.\n\n"
                f"📅 {new_date}\n"
                f"⏰ {new_time}"
            )
        }

    # --------------------------------------------------------
    # Update appointment
    # --------------------------------------------------------

    cursor.execute("""
        UPDATE appointments
        SET appointment_date = ?,
            appointment_time = ?,
            reminder_sent = 0,
            reminder_sent_at = NULL
        WHERE id = ?
    """, (
        new_date.strip(),
        new_time,
        appointment_id
    ))

    conn.commit()
    conn.close()

    # --------------------------------------------------------
    # Return result
    # --------------------------------------------------------

    return {
        "success": True,
        "message": (
            "✅ Appointment rescheduled successfully!\n\n"
            f"🆔 Appointment ID: {appointment_id}\n"
            f"👤 Name: {appointment['name']}\n"
            f"📅 New Date: {new_date.strip()}\n"
            f"⏰ New Time: {new_time}\n"
            f"📧 Email: {appointment['email']}"
        )
    }


print("✅ Reschedule appointment function created successfully.")


# ============================================================
# ORIGINAL NOTEBOOK CODE CELL 13
# ============================================================

# ============================================================
# LIST APPOINTMENTS
# ============================================================

def get_appointments():
    """
    Retrieve all booked appointments.
    """

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            name,
            appointment_date,
            appointment_time,
            purpose,
            email,
            reminder_minutes,
            reminder_sent
        FROM appointments
        ORDER BY id
    """)

    appointments = cursor.fetchall()

    conn.close()

    return [dict(appointment) for appointment in appointments]


def display_appointments():
    """
    Display all appointments in a readable format.
    """

    appointments = get_appointments()

    if not appointments:
        return "📭 No appointments found."

    output = "📋 BOOKED APPOINTMENTS\n"
    output += "=" * 60 + "\n\n"

    for appointment in appointments:

        output += (
            f"🆔 Appointment ID : {appointment['id']}\n"
            f"👤 Name           : {appointment['name']}\n"
            f"📅 Date           : {appointment['appointment_date']}\n"
            f"⏰ Time           : {appointment['appointment_time']}\n"
            f"📝 Purpose        : {appointment['purpose'] or 'Not specified'}\n"
            f"📧 Email          : {appointment['email']}\n"
            f"🔔 Reminder       : {appointment['reminder_minutes']} minutes before\n"
            f"📨 Reminder Sent  : {'Yes' if appointment['reminder_sent'] else 'No'}\n"
            + "-" * 60 + "\n"
        )

    return output


print("✅ List appointments functions created successfully.")


# ============================================================
# ORIGINAL NOTEBOOK CODE CELL 14
# ============================================================

# ============================================================
# GMAIL CONFIGURATION
# ============================================================

import os
import smtplib
from email.message import EmailMessage
from google.colab import userdata


GMAIL_ADDRESS = "dailyscheduletest@gmail.com"

GMAIL_APP_PASSWORD = userdata.get("GMAIL_APP_PASSWORD")

if not GMAIL_APP_PASSWORD:
    raise ValueError(
        "❌ GMAIL_APP_PASSWORD not found in Colab Secrets."
    )

os.environ["GMAIL_APP_PASSWORD"] = GMAIL_APP_PASSWORD

print("✅ Gmail configuration loaded successfully.")
print(f"📧 Sender: {GMAIL_ADDRESS}")


# ============================================================
# ORIGINAL NOTEBOOK CODE CELL 15
# ============================================================

# ============================================================
# SEND APPOINTMENT CONFIRMATION EMAIL
# ============================================================

def send_confirmation_email(
    name,
    appointment_date,
    appointment_time,
    purpose,
    customer_email,
    appointment_id
):
    """
    Send appointment confirmation email using Gmail SMTP.
    """

    try:
        message = EmailMessage()

        message["From"] = GMAIL_ADDRESS
        message["To"] = customer_email
        message["Subject"] = "Appointment Confirmation"

        email_body = f"""
Hello {name},

Your appointment has been successfully booked.

Appointment Details
-------------------
Appointment ID : {appointment_id}
Name           : {name}
Date           : {appointment_date}
Time           : {appointment_time}
Purpose        : {purpose if purpose else "Not specified"}

Reminder
--------
You will receive a reminder 15 minutes before your appointment.

Thank you.

Best regards,
Appointment Scheduling Assistant
"""

        message.set_content(email_body)

        # Connect to Gmail SMTP server
        with smtplib.SMTP_SSL(
            "smtp.gmail.com",
            465
        ) as smtp:

            smtp.login(
                GMAIL_ADDRESS,
                GMAIL_APP_PASSWORD
            )

            smtp.send_message(message)

        print(
            f"✅ Confirmation email sent successfully "
            f"to {customer_email}"
        )

        return True

    except Exception as e:

        print(
            f"❌ Error sending confirmation email: {e}"
        )

        return False


print("✅ Confirmation email function created successfully.")


# ============================================================
# ORIGINAL NOTEBOOK CODE CELL 16
# ============================================================

# ============================================================
# TEST CONFIRMATION EMAIL
# ============================================================

test_email_result = send_confirmation_email(
    name="Test User",
    appointment_date="15-09-2026",
    appointment_time="10:30",
    purpose="Test Appointment",
    customer_email=GMAIL_ADDRESS,
    appointment_id=1
)

if test_email_result:
    print("✅ Test confirmation email sent successfully.")
else:
    print("❌ Test confirmation email failed.")


# ============================================================
# ORIGINAL NOTEBOOK CODE CELL 17
# ============================================================

# ============================================================
# SEND APPOINTMENT REMINDER EMAIL
# ============================================================

def send_reminder_email(
    name,
    appointment_date,
    appointment_time,
    purpose,
    customer_email,
    appointment_id
):
    """
    Send appointment reminder email using Gmail SMTP.
    """

    try:
        message = EmailMessage()

        message["From"] = GMAIL_ADDRESS
        message["To"] = customer_email
        message["Subject"] = "Appointment Reminder"

        email_body = f"""
Hello {name},

This is a reminder about your upcoming appointment.

Appointment Details
-------------------
Appointment ID : {appointment_id}
Name           : {name}
Date           : {appointment_date}
Time           : {appointment_time}
Purpose        : {purpose if purpose else "Not specified"}

Your appointment is coming up soon.

Please make sure you are available at the scheduled time.

Thank you.

Best regards,
Appointment Scheduling Assistant
"""

        message.set_content(email_body)

        # Connect to Gmail SMTP server
        with smtplib.SMTP_SSL(
            "smtp.gmail.com",
            465
        ) as smtp:

            smtp.login(
                GMAIL_ADDRESS,
                GMAIL_APP_PASSWORD
            )

            smtp.send_message(message)

        print(
            f"✅ Reminder email sent successfully "
            f"to {customer_email}"
        )

        return True

    except Exception as e:

        print(
            f"❌ Error sending reminder email: {e}"
        )

        return False


print("✅ Reminder email function created successfully.")


# ============================================================
# ORIGINAL NOTEBOOK CODE CELL 18
# ============================================================

# ============================================================
# TEST REMINDER EMAIL
# ============================================================

test_reminder_result = send_reminder_email(
    name="Test User",
    appointment_date="15-09-2026",
    appointment_time="10:30",
    purpose="Test Appointment",
    customer_email=GMAIL_ADDRESS,
    appointment_id=1
)

if test_reminder_result:
    print("✅ Test reminder email sent successfully.")
else:
    print("❌ Test reminder email failed.")


# ============================================================
# ORIGINAL NOTEBOOK CODE CELL 19
# ============================================================

# ============================================================
# AUTOMATIC REMINDER CHECKER
# ============================================================

from datetime import datetime, timedelta


def check_and_send_reminders():
    """
    Check upcoming appointments and send reminders.

    Reminder is sent 15 minutes before the appointment.
    """

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM appointments
        WHERE reminder_sent = 0
    """)

    appointments = cursor.fetchall()

    reminders_sent = 0

    for appointment in appointments:

        try:
            # ------------------------------------------------
            # Convert appointment date and time to datetime
            # ------------------------------------------------

            appointment_datetime = datetime.strptime(
                f"{appointment['appointment_date']} "
                f"{appointment['appointment_time']}",
                "%d-%m-%Y %H:%M"
            )

            # ------------------------------------------------
            # Calculate reminder time
            # ------------------------------------------------

            reminder_datetime = (
                appointment_datetime
                - timedelta(
                    minutes=appointment["reminder_minutes"]
                )
            )

            current_datetime = datetime.now()

            # ------------------------------------------------
            # Check whether reminder should be sent
            # ------------------------------------------------

            if (
                current_datetime >= reminder_datetime
                and current_datetime < appointment_datetime
            ):

                success = send_reminder_email(
                    name=appointment["name"],
                    appointment_date=appointment["appointment_date"],
                    appointment_time=appointment["appointment_time"],
                    purpose=appointment["purpose"],
                    customer_email=appointment["email"],
                    appointment_id=appointment["id"]
                )

                # --------------------------------------------
                # Mark reminder as sent only if email succeeds
                # --------------------------------------------

                if success:

                    cursor.execute("""
                        UPDATE appointments
                        SET reminder_sent = 1,
                            reminder_sent_at = ?
                        WHERE id = ?
                    """, (
                        datetime.now().strftime(
                            "%d-%m-%Y %H:%M:%S"
                        ),
                        appointment["id"]
                    ))

                    conn.commit()

                    reminders_sent += 1

                    print(
                        f"🔔 Reminder sent for "
                        f"Appointment ID {appointment['id']}"
                    )

        except Exception as e:

            print(
                f"❌ Error processing Appointment "
                f"ID {appointment['id']}: {e}"
            )

    conn.close()

    print(
        f"✅ Reminder check completed. "
        f"Reminders sent: {reminders_sent}"
    )

    return reminders_sent


print("✅ Automatic reminder checker created successfully.")


# ============================================================
# ORIGINAL NOTEBOOK CODE CELL 20
# ============================================================

# ============================================================
# AUTOMATIC REMINDER BACKGROUND LOOP
# ============================================================

import threading
import time


reminder_loop_running = False


def reminder_loop():
    """
    Run the reminder checker every 60 seconds.
    """

    global reminder_loop_running

    while reminder_loop_running:

        try:
            check_and_send_reminders()

        except Exception as e:
            print(f"❌ Reminder loop error: {e}")

        time.sleep(60)


def start_reminder_loop():
    """
    Start the automatic reminder background loop.
    """

    global reminder_loop_running

    if reminder_loop_running:
        print("⚠️ Reminder loop is already running.")
        return

    reminder_loop_running = True

    reminder_thread = threading.Thread(
        target=reminder_loop,
        daemon=True
    )

    reminder_thread.start()

    print("🔔 Automatic reminder loop started.")
    print("⏱️ Checking appointments every 60 seconds.")


def stop_reminder_loop():
    """
    Stop the automatic reminder background loop.
    """

    global reminder_loop_running

    reminder_loop_running = False

    print("🛑 Automatic reminder loop stopped.")


print("✅ Automatic reminder background loop created successfully.")


# ============================================================
# ORIGINAL NOTEBOOK CODE CELL 21
# ============================================================

# ============================================================
# VOICE PROCESSING PIPELINE
# ============================================================

def process_voice(audio_file):
    """
    Process voice input:
    Audio → Speech-to-Text → AI Understanding
    """

    if not audio_file:
        return {
            "success": False,
            "message": "🎤 Please record your voice first.",
            "transcription": "",
            "data": None
        }

    # --------------------------------------------------------
    # Speech to Text
    # --------------------------------------------------------

    transcription = transcribe_audio(audio_file)

    if not transcription:
        return {
            "success": False,
            "message": "❌ Could not understand the audio.",
            "transcription": "",
            "data": None
        }

    # --------------------------------------------------------
    # AI Appointment Understanding
    # --------------------------------------------------------

    appointment_data = understand_appointment(
        transcription
    )

    if not appointment_data:
        return {
            "success": False,
            "message": "❌ Could not understand the appointment request.",
            "transcription": transcription,
            "data": None
        }

    # --------------------------------------------------------
    # Return complete result
    # --------------------------------------------------------

    return {
        "success": True,
        "message": "✅ Voice processed successfully.",
        "transcription": transcription,
        "data": appointment_data
    }


print("✅ Voice processing pipeline created successfully.")


# ============================================================
# ORIGINAL NOTEBOOK CODE CELL 22
# ============================================================

# ============================================================
# VALIDATE APPOINTMENT INFORMATION
# ============================================================

def validate_appointment_data(data):
    """
    Check whether the AI extracted all required
    appointment information.
    """

    if not data:
        return {
            "valid": False,
            "missing": [],
            "message": "❌ No appointment information found."
        }

    required_fields = {
        "name": "Name",
        "appointment_date": "Appointment date",
        "appointment_time": "Appointment time",
        "email": "Email address"
    }

    missing = []

    for field, display_name in required_fields.items():

        value = data.get(field, "")

        if not value or not str(value).strip():
            missing.append(display_name)

    if missing:

        return {
            "valid": False,
            "missing": missing,
            "message": (
                "⚠️ Missing information: "
                + ", ".join(missing)
            )
        }

    return {
        "valid": True,
        "missing": [],
        "message": "✅ All required appointment information is available."
    }


print("✅ Appointment validation function created successfully.")


# ============================================================
# ORIGINAL NOTEBOOK CODE CELL 23
# ============================================================

# ============================================================
# COMPLETE APPOINTMENT BOOKING WORKFLOW
# ============================================================

def process_booking(data):
    """
    Complete booking workflow:

    AI data
        ↓
    Validation
        ↓
    Database booking
        ↓
    Confirmation email
    """

    # --------------------------------------------------------
    # Validate appointment information
    # --------------------------------------------------------

    validation = validate_appointment_data(data)

    if not validation["valid"]:
        return {
            "success": False,
            "message": validation["message"],
            "appointment_id": None
        }

    # --------------------------------------------------------
    # Book appointment in database
    # --------------------------------------------------------

    booking_result = book_appointment(
        name=data["name"],
        appointment_date=data["appointment_date"],
        appointment_time=data["appointment_time"],
        purpose=data.get("purpose", ""),
        email=data["email"]
    )

    if not booking_result["success"]:
        return {
            "success": False,
            "message": booking_result["message"],
            "appointment_id": None
        }

    appointment_id = booking_result["appointment_id"]

    # --------------------------------------------------------
    # Send confirmation email
    # --------------------------------------------------------

    email_sent = send_confirmation_email(
        name=data["name"],
        appointment_date=data["appointment_date"],
        appointment_time=data["appointment_time"],
        purpose=data.get("purpose", ""),
        customer_email=data["email"],
        appointment_id=appointment_id
    )

    # --------------------------------------------------------
    # Final result
    # --------------------------------------------------------

    if email_sent:

        return {
            "success": True,
            "appointment_id": appointment_id,
            "message": (
                booking_result["message"]
                + "\n\n📧 Confirmation email sent successfully."
            )
        }

    else:

        return {
            "success": True,
            "appointment_id": appointment_id,
            "message": (
                booking_result["message"]
                + "\n\n⚠️ Appointment was booked, "
                  "but confirmation email could not be sent."
            )
        }


print("✅ Complete appointment booking workflow created successfully.")


# ============================================================
# ORIGINAL NOTEBOOK CODE CELL 24
# ============================================================

# ============================================================
# APPOINTMENT ACTION HANDLER
# ============================================================

def handle_appointment_action(data):
    """
    Handle appointment actions based on AI intent.

    Supported intents:
    - book
    - cancel
    - reschedule
    - list
    """

    if not data:
        return {
            "success": False,
            "message": "❌ No appointment information available."
        }

    intent = data.get("intent", "").lower().strip()

    # --------------------------------------------------------
    # BOOK
    # --------------------------------------------------------

    if intent == "book":

        result = process_booking(data)

        return result

    # --------------------------------------------------------
    # LIST
    # --------------------------------------------------------

    elif intent == "list":

        appointments = get_appointments()

        if not appointments:
            return {
                "success": True,
                "message": "📭 No appointments found."
            }

        return {
            "success": True,
            "message": display_appointments()
        }

    # --------------------------------------------------------
    # CANCEL
    # --------------------------------------------------------

    elif intent == "cancel":

        appointment_id = data.get("appointment_id")

        if not appointment_id:

            return {
                "success": False,
                "message": (
                    "⚠️ Please provide the Appointment ID "
                    "you want to cancel."
                )
            }

        return cancel_appointment(
            appointment_id
        )

    # --------------------------------------------------------
    # RESCHEDULE
    # --------------------------------------------------------

    elif intent == "reschedule":

        appointment_id = data.get("appointment_id")
        new_date = data.get("appointment_date")
        new_time = data.get("appointment_time")

        if not appointment_id:

            return {
                "success": False,
                "message": (
                    "⚠️ Please provide the Appointment ID "
                    "you want to reschedule."
                )
            }

        if not new_date or not new_time:

            return {
                "success": False,
                "message": (
                    "⚠️ Please provide the new "
                    "appointment date and time."
                )
            }

        return reschedule_appointment(
            appointment_id,
            new_date,
            new_time
        )

    # --------------------------------------------------------
    # UNKNOWN INTENT
    # --------------------------------------------------------

    else:

        return {
            "success": False,
            "message": (
                f"❌ Unsupported appointment action: {intent}"
            )
        }


print("✅ Appointment action handler created successfully.")


# ============================================================
# ORIGINAL NOTEBOOK CODE CELL 25
# ============================================================

# ============================================================
# AI APPOINTMENT UNDERSTANDING
# ============================================================

import json
from datetime import datetime


AI_MODEL = "openai/gpt-oss-20b"


def understand_appointment(user_text):
    """
    Convert natural-language appointment requests
    into structured appointment information.
    """

    if not user_text or not user_text.strip():
        return None

    # --------------------------------------------------------
    # Current date for relative-date understanding
    # --------------------------------------------------------

    today_date = datetime.now().strftime("%d-%m-%Y")

    system_prompt = f"""
You are an appointment scheduling assistant.

Today's date is {today_date}.

Extract appointment information from the user's request.

Return ONLY valid JSON with exactly these fields:

{{
    "intent": "book | cancel | reschedule | list",
    "appointment_id": "",
    "name": "",
    "appointment_date": "",
    "appointment_time": "",
    "purpose": "",
    "email": ""
}}

Rules:

1. intent must be one of:
   book, cancel, reschedule, list

2. appointment_id:
   - Extract the appointment ID when the user provides one.
   - For example: "cancel appointment 5" → "5"
   - If not provided, use "".

3. appointment_date must use:
   DD-MM-YYYY

4. appointment_time must use:
   HH:MM in 24-hour format.

5. If the user says "today", use today's date.

6. If the user says "tomorrow", calculate the date
   based on today's date ({today_date}).

7. If information is missing, keep that field as "".

8. Do not invent missing information.

9. Extract the person's name carefully.

10. Extract the email address if provided.

11. Extract the purpose if provided.

12. For cancellation:
    - Extract appointment_id if provided.
    - Do not invent an appointment ID.

13. For rescheduling:
    - Extract appointment_id.
    - Extract the new appointment date.
    - Extract the new appointment time.

14. For listing appointments:
    - intent should be "list".

15. Return ONLY valid JSON.
"""

    try:

        response = groq_client.chat.completions.create(
            model=AI_MODEL,

            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_text
                }
            ],

            temperature=0,

            response_format={
                "type": "json_object"
            }
        )

        raw_response = response.choices[0].message.content

        print("🤖 Raw AI Response:")
        print(raw_response)

        result = json.loads(raw_response)

        print("\n🤖 AI Understanding:")
        print(json.dumps(result, indent=2))

        return result

    except Exception as e:

        print("\n❌ AI Understanding Error:")
        print(type(e).__name__)
        print(str(e))

        return None


print("✅ AI appointment understanding updated successfully.")
print(f"🤖 AI Model: {AI_MODEL}")


# ============================================================
# ORIGINAL NOTEBOOK CODE CELL 26
# ============================================================

# ============================================================
# TEST CANCEL INTENT
# ============================================================

test_text = "Cancel appointment number 1."

result = understand_appointment(test_text)

print("\n🤖 Final Result:")
print(result)


# ============================================================
# ORIGINAL NOTEBOOK CODE CELL 27
# ============================================================

# ============================================================
# TEST CANCEL APPOINTMENT
# ============================================================

cancel_test = handle_appointment_action({
    "intent": "cancel",
    "appointment_id": "1"
})

print(cancel_test["message"])


# ============================================================
# ORIGINAL NOTEBOOK CODE CELL 28
# ============================================================

# ============================================================
# TEST RESCHEDULE APPOINTMENT
# ============================================================

# Create a test appointment
test_booking = book_appointment(
    name="Reschedule Test",
    appointment_date="20-09-2026",
    appointment_time="11:00 AM",
    purpose="Reschedule Test",
    email=GMAIL_ADDRESS
)

print("📌 Original Booking:")
print(test_booking["message"])


# Get the appointment ID
test_appointment_id = test_booking.get("appointment_id")


# Reschedule it
if test_booking["success"]:

    reschedule_test = reschedule_appointment(
        appointment_id=test_appointment_id,
        new_date="21-09-2026",
        new_time="02:30 PM"
    )

    print("\n📌 Reschedule Result:")
    print(reschedule_test["message"])


# ============================================================
# ORIGINAL NOTEBOOK CODE CELL 29
# ============================================================

# ============================================================
# FIX PENDING APPOINTMENT STATE
# ============================================================

def process_voice_for_ui(audio_file):

    result = process_voice_action(audio_file)

    transcription = result.get("transcription", "")
    ai_data = result.get("ai_data")

    # --------------------------------------------------------
    # No AI data
    # --------------------------------------------------------

    if not ai_data:
        return (
            transcription,
            "",
            result.get("message", "❌ Unable to understand appointment."),
            "",
            display_appointments(),
            None
        )

    # --------------------------------------------------------
    # BOOKING REQUEST
    # --------------------------------------------------------

    if ai_data.get("intent") == "book":

        validation = validate_appointment_data(ai_data)

        # Missing information
        if not validation["valid"]:

            missing = validation["missing"]

            return (
                transcription,
                json.dumps(ai_data, indent=2),
                f"⚠️ Missing information: {', '.join(missing)}\n\n"
                f"Please enter the missing information below.",
                "",
                display_appointments(),

                # IMPORTANT:
                # Keep the appointment data in Gradio State
                ai_data
            )

        # All information available
        booking_result = process_booking(ai_data)

        return (
            transcription,
            json.dumps(ai_data, indent=2),
            booking_result["message"],
            "",
            display_appointments(),
            None
        )

    # --------------------------------------------------------
    # CANCEL / RESCHEDULE / LIST
    # --------------------------------------------------------

    return (
        transcription,
        json.dumps(ai_data, indent=2),
        result.get("message", ""),
        "",
        display_appointments(),
        None
    )


def complete_booking_with_email(email, pending_data):

    # --------------------------------------------------------
    # CHECK PENDING DATA
    # --------------------------------------------------------

    if not pending_data:

        return (
            "❌ No pending appointment found. Please process the voice request again.",
            display_appointments(),
            None
        )

    # --------------------------------------------------------
    # ADD EMAIL
    # --------------------------------------------------------

    pending_data = pending_data.copy()

    pending_data["email"] = (
        email.strip()
        if email
        else ""
    )

    # --------------------------------------------------------
    # VALIDATE
    # --------------------------------------------------------

    validation = validate_appointment_data(pending_data)

    if not validation["valid"]:

        return (
            f"⚠️ Missing information: {', '.join(validation['missing'])}",
            display_appointments(),
            pending_data
        )

    # --------------------------------------------------------
    # BOOK APPOINTMENT
    # --------------------------------------------------------

    result = process_booking(pending_data)

    if result["success"]:

        return (
            result["message"],
            display_appointments(),
            None
        )

    return (
        result["message"],
        display_appointments(),
        pending_data
    )


# ============================================================
# ORIGINAL NOTEBOOK CODE CELL 30
# ============================================================

# ============================================================
# FINAL VOICE ACTION WORKFLOW
# ============================================================

def process_voice_action(audio_file):
    """
    Complete voice appointment workflow.

    Audio
      ↓
    Speech-to-Text
      ↓
    AI Understanding
      ↓
    Appointment Action
    """

    # --------------------------------------------------------
    # Check audio
    # --------------------------------------------------------

    if not audio_file:
        return {
            "success": False,
            "transcription": "",
            "ai_data": None,
            "message": "🎤 Please record your request."
        }

    # --------------------------------------------------------
    # Speech to Text
    # --------------------------------------------------------

    transcription = transcribe_audio(audio_file)

    if not transcription:

        return {
            "success": False,
            "transcription": "",
            "ai_data": None,
            "message": "❌ Could not understand the audio."
        }

    # --------------------------------------------------------
    # AI Understanding
    # --------------------------------------------------------

    ai_data = understand_appointment(
        transcription
    )

    if not ai_data:

        return {
            "success": False,
            "transcription": transcription,
            "ai_data": None,
            "message": (
                "❌ Could not understand "
                "the appointment request."
            )
        }

    # --------------------------------------------------------
    # Execute Appointment Action
    # --------------------------------------------------------

    action_result = handle_appointment_action(
        ai_data
    )

    # --------------------------------------------------------
    # Return complete result
    # --------------------------------------------------------

    return {
        "success": action_result["success"],
        "transcription": transcription,
        "ai_data": ai_data,
        "message": action_result["message"]
    }


print("✅ Final voice action workflow created successfully.")


# ============================================================
# ORIGINAL NOTEBOOK CODE CELL 31
# ============================================================

# ============================================================
# FINAL GRADIO APPOINTMENT INTERFACE
# ============================================================

import gradio as gr
import json


def process_voice_for_ui(audio_file):
    result = process_voice_action(audio_file)

    transcription = result.get("transcription", "")
    ai_data = result.get("ai_data")

    if not result["success"]:
        return (
            transcription,
            json.dumps(ai_data, indent=2) if ai_data else "",
            result["message"],
            "",
            display_appointments(),
            ai_data
        )

    # If booking needs more information
    if ai_data and ai_data.get("intent") == "book":

        validation = validate_appointment_data(ai_data)

        if not validation["valid"]:
            missing = validation["missing"]

            return (
                transcription,
                json.dumps(ai_data, indent=2),
                f"⚠️ Missing information: {', '.join(missing)}\n\n"
                f"Please enter the missing information below.",
                "",
                display_appointments(),
                ai_data
            )

    return (
        transcription,
        json.dumps(ai_data, indent=2),
        result["message"],
        "",
        display_appointments(),
        ai_data
    )


def complete_booking_with_email(email, pending_data):
    if not pending_data:
        return (
            "❌ No pending appointment found.",
            display_appointments(),
            pending_data
        )

    # Add email entered by user
    pending_data = pending_data.copy()
    pending_data["email"] = email.strip() if email else ""

    # Validate again
    validation = validate_appointment_data(pending_data)

    if not validation["valid"]:
        return (
            f"⚠️ Missing information: {', '.join(validation['missing'])}",
            display_appointments(),
            pending_data
        )

    # Book appointment
    result = process_booking(pending_data)

    return (
        result["message"],
        display_appointments(),
        None if result["success"] else pending_data
    )


def clear_interface():
    return (
        None,   # audio
        "",     # transcription
        "",     # AI understanding
        "",     # status
        "",     # email
        display_appointments(),
        None    # pending data
    )


with gr.Blocks(title="Voice Appointment Chatbot") as app:

    gr.Markdown(
        """
        # 🎤 Voice Appointment Chatbot

        ### AI-Powered Appointment Scheduling System

        **Book • Cancel • Reschedule • List • Email Confirmation • Reminders**
        """
    )

    # --------------------------------------------------------
    # VOICE INPUT
    # --------------------------------------------------------

    gr.Markdown("## 🎤 Voice Appointment")

    audio_input = gr.Audio(
        sources=["microphone"],
        type="filepath",
        label="Record your appointment request"
    )

    with gr.Row():
        process_button = gr.Button(
            "🎤 Process Voice",
            variant="primary"
        )

        clear_button = gr.Button(
            "🗑️ Clear"
        )

    # --------------------------------------------------------
    # OUTPUTS
    # --------------------------------------------------------

    transcription_output = gr.Textbox(
        label="📝 Transcription",
        lines=3
    )

    ai_output = gr.Textbox(
        label="🤖 AI Understanding",
        lines=10
    )

    status_output = gr.Textbox(
        label="📢 Status",
        lines=5
    )

    # --------------------------------------------------------
    # MISSING INFORMATION
    # --------------------------------------------------------

    gr.Markdown("## 📧 Complete Appointment Details")

    email_input = gr.Textbox(
        label="Email Address",
        placeholder="Enter email address for confirmation",
        type="email"
    )

    complete_booking_button = gr.Button(
        "✅ Complete Booking",
        variant="primary"
    )

    # --------------------------------------------------------
    # APPOINTMENTS
    # --------------------------------------------------------

    gr.Markdown("## 📋 Appointments")

    appointments_output = gr.Textbox(
        label="Booked Appointments",
        lines=15
    )

    # --------------------------------------------------------
    # INTERNAL STATE
    # --------------------------------------------------------

    pending_data = gr.State(None)

    # --------------------------------------------------------
    # PROCESS VOICE
    # --------------------------------------------------------

    process_button.click(
        fn=process_voice_for_ui,
        inputs=audio_input,
        outputs=[
            transcription_output,
            ai_output,
            status_output,
            email_input,
            appointments_output,
            pending_data
        ]
    )

    # --------------------------------------------------------
    # COMPLETE BOOKING
    # --------------------------------------------------------

    complete_booking_button.click(
        fn=complete_booking_with_email,
        inputs=[
            email_input,
            pending_data
        ],
        outputs=[
            status_output,
            appointments_output,
            pending_data
        ]
    )

    # --------------------------------------------------------
    # CLEAR
    # --------------------------------------------------------

    clear_button.click(
        fn=clear_interface,
        inputs=[],
        outputs=[
            audio_input,
            transcription_output,
            ai_output,
            status_output,
            email_input,
            appointments_output,
            pending_data
        ]
    )


# ============================================================
# START AUTOMATIC REMINDER SYSTEM
# ============================================================

start_reminder_loop()


# ============================================================
# LAUNCH APPLICATION
# ============================================================

app.launch(
    share=True,
    debug=True
)


# ============================================================
# ORIGINAL NOTEBOOK CODE CELL 32
# ============================================================

# ============================================================
# GROQ TEXT-TO-SPEECH VOICE REPLY
# ============================================================

import os

TTS_MODEL = "canopylabs/orpheus-v1-english"
TTS_VOICE = "troy"


def generate_voice_reply(text):
    """
    Convert chatbot text response into a WAV audio file.
    """

    if not text or not text.strip():
        return None

    try:
        # Keep the spoken response concise
        speech_text = text.strip()

        # Orpheus supports input up to 200 characters
        if len(speech_text) > 200:
            speech_text = speech_text[:197] + "..."

        speech_file = "voice_reply.wav"

        response = groq_client.audio.speech.create(
            model=TTS_MODEL,
            voice=TTS_VOICE,
            input=speech_text,
            response_format="wav"
        )

        response.write_to_file(speech_file)

        print("🔊 Voice reply generated successfully.")
        print(f"📁 Audio file: {speech_file}")

        return speech_file

    except Exception as e:
        print("❌ Voice reply error:")
        print(type(e).__name__)
        print(str(e))
        return None


# ============================================================
# TEST VOICE REPLY
# ============================================================

test_voice_file = generate_voice_reply(
    "Your appointment has been cancelled successfully."
)

print("\n✅ TTS test completed.")


# ============================================================
# ORIGINAL NOTEBOOK CODE CELL 33
# ============================================================

# ============================================================
# IMPROVE VOICE REPLY DATE AND TIME PRONUNCIATION
# ============================================================

import re
from datetime import datetime


def prepare_text_for_speech(text):

    if not text:
        return ""

    speech_text = text

    # --------------------------------------------------------
    # CONVERT DD-MM-YYYY TO NATURAL SPOKEN DATE
    # Example:
    # 05-09-2026 → 5 September 2026
    # --------------------------------------------------------

    date_pattern = r"\b(\d{2})-(\d{2})-(\d{4})\b"

    def replace_date(match):

        day = int(match.group(1))
        month = int(match.group(2))
        year = int(match.group(3))

        try:
            date_object = datetime(
                year,
                month,
                day
            )

            return date_object.strftime("%-d %B %Y")

        except ValueError:
            return match.group(0)

    speech_text = re.sub(
        date_pattern,
        replace_date,
        speech_text
    )

    # --------------------------------------------------------
    # CONVERT HH:MM TO NATURAL SPOKEN TIME
    # Example:
    # 14:30 → 2:30 PM
    # 11:00 → 11:00 AM
    # --------------------------------------------------------

    time_pattern = r"\b([01]\d|2[0-3]):([0-5]\d)\b"

    def replace_time(match):

        hour = int(match.group(1))
        minute = int(match.group(2))

        try:
            time_object = datetime.strptime(
                f"{hour:02d}:{minute:02d}",
                "%H:%M"
            )

            return time_object.strftime("%-I:%M %p")

        except ValueError:
            return match.group(0)

    speech_text = re.sub(
        time_pattern,
        replace_time,
        speech_text
    )

    return speech_text


# ============================================================
# IMPROVED VOICE REPLY
# ============================================================

import re
from datetime import datetime

TTS_MODEL = "canopylabs/orpheus-v1-english"
TTS_VOICE = "hannah"
TTS_SPEED = 0.85


def prepare_text_for_speech(text):
    if not text:
        return ""

    speech_text = text.strip()

    # --------------------------------------------------------
    # Convert DD-MM-YYYY → natural spoken date
    # Example: 05-09-2026 → 5 September 2026
    # --------------------------------------------------------

    date_pattern = r"\b(\d{2})-(\d{2})-(\d{4})\b"

    def replace_date(match):
        day = int(match.group(1))
        month = int(match.group(2))
        year = int(match.group(3))

        try:
            date_object = datetime(year, month, day)
            return date_object.strftime("%-d %B %Y")
        except ValueError:
            return match.group(0)

    speech_text = re.sub(
        date_pattern,
        replace_date,
        speech_text
    )

    # --------------------------------------------------------
    # Convert HH:MM → natural spoken time
    # Example: 14:30 → 2:30 PM
    # --------------------------------------------------------

    time_pattern = r"\b([01]\d|2[0-3]):([0-5]\d)\b"

    def replace_time(match):
        hour = int(match.group(1))
        minute = int(match.group(2))

        try:
            time_object = datetime.strptime(
                f"{hour:02d}:{minute:02d}",
                "%H:%M"
            )

            return time_object.strftime("%-I:%M %p")

        except ValueError:
            return match.group(0)

    speech_text = re.sub(
        time_pattern,
        replace_time,
        speech_text
    )

    # --------------------------------------------------------
    # Add natural pauses
    # --------------------------------------------------------

    speech_text = speech_text.replace(
        " is confirmed for ",
        " is confirmed. Your appointment is on "
    )

    speech_text = speech_text.replace(
        " at ",
        " at "
    )

    return speech_text


def generate_voice_reply(text):

    if not text or not text.strip():
        return None

    try:

        # Prepare natural speech text
        speech_text = prepare_text_for_speech(text)

        print("📝 Original response:")
        print(text)

        print("\n🔊 Text sent to TTS:")
        print(speech_text)

        # Groq Orpheus limit = 200 characters
        if len(speech_text) > 200:
            speech_text = speech_text[:197] + "..."

        speech_file = "voice_reply.wav"

        # Generate speech
        response = groq_client.audio.speech.create(
            model=TTS_MODEL,
            voice=TTS_VOICE,
            input=speech_text,
            response_format="wav",
            speed=TTS_SPEED
        )

        response.write_to_file(speech_file)

        print("\n🔊 Improved voice generated successfully.")
        print(f"🎙️ Voice: {TTS_VOICE}")
        print(f"🐢 Speed: {TTS_SPEED}")
        print(f"📁 Audio file: {speech_file}")

        return speech_file

    except Exception as e:

        print("\n❌ Voice reply error:")
        print(type(e).__name__)
        print(str(e))

        return None


# ============================================================
# ORIGINAL NOTEBOOK CODE CELL 34
# ============================================================

# ============================================================
# CLEAR AI VOICE REPLY
# ============================================================

TTS_MODEL = "canopylabs/orpheus-v1-english"

# Try Hannah for a clearer assistant voice
TTS_VOICE = "hannah"


def generate_voice_reply(text):

    if not text or not text.strip():
        return None

    try:

        # ----------------------------------------------------
        # CONVERT DATE AND TIME FOR NATURAL SPEECH
        # ----------------------------------------------------

        speech_text = prepare_text_for_speech(text)

        print("📝 Original response:")
        print(text)

        print("\n🔊 Text sent to TTS:")
        print(speech_text)

        # ----------------------------------------------------
        # LIMIT INPUT
        # ----------------------------------------------------

        if len(speech_text) > 200:
            speech_text = speech_text[:197] + "..."

        speech_file = "voice_reply.wav"

        # ----------------------------------------------------
        # GENERATE CLEARER VOICE
        # ----------------------------------------------------

        response = groq_client.audio.speech.create(
            model=TTS_MODEL,
            voice=TTS_VOICE,
            input=speech_text,
            response_format="wav",
            speed=0.90
        )

        response.write_to_file(speech_file)

        print("\n🔊 Voice reply generated successfully.")
        print(f"🎙️ Voice: {TTS_VOICE}")
        print("🐢 Speed: 0.90")
        print(f"📁 Audio file: {speech_file}")

        return speech_file

    except Exception as e:

        print("\n❌ Voice reply error:")
        print(type(e).__name__)
        print(str(e))

        return None


# ============================================================
# ORIGINAL NOTEBOOK CODE CELL 35
# ============================================================

# ============================================================
# TEST IMPROVED VOICE
# ============================================================

test_voice_file = generate_voice_reply(
    "Your appointment is confirmed for 05-09-2026 at 14:30."
)

print("\n✅ Improved voice test completed.")


# ============================================================
# ORIGINAL NOTEBOOK CODE CELL 36
# ============================================================

# ============================================================
# VOICE-FRIENDLY TTS RESPONSE
# ============================================================

import re
from datetime import datetime

TTS_MODEL = "canopylabs/orpheus-v1-english"
TTS_VOICE = "hannah"
TTS_SPEED = 0.85


def prepare_text_for_speech(text):
    """
    Convert database-style date/time into natural spoken English.
    """

    if not text:
        return ""

    speech_text = text.strip()

    # --------------------------------------------------------
    # Convert DD-MM-YYYY → natural spoken date
    # Example: 03-09-2026 → 3 September 2026
    # --------------------------------------------------------

    date_pattern = r"\b(\d{2})-(\d{2})-(\d{4})\b"

    def replace_date(match):
        day = int(match.group(1))
        month = int(match.group(2))
        year = int(match.group(3))

        try:
            date_object = datetime(year, month, day)
            return date_object.strftime("%-d %B %Y")
        except ValueError:
            return match.group(0)

    speech_text = re.sub(
        date_pattern,
        replace_date,
        speech_text
    )

    # --------------------------------------------------------
    # Convert HH:MM → natural spoken time
    # Example: 16:00 → 4 PM
    # Example: 14:30 → 2:30 PM
    # --------------------------------------------------------

    time_pattern = r"\b([01]\d|2[0-3]):([0-5]\d)\b"

    def replace_time(match):
        hour = int(match.group(1))
        minute = int(match.group(2))

        try:
            time_object = datetime.strptime(
                f"{hour:02d}:{minute:02d}",
                "%H:%M"
            )

            if minute == 0:
                return time_object.strftime("%-I %p")
            else:
                return time_object.strftime("%-I:%M %p")

        except ValueError:
            return match.group(0)

    speech_text = re.sub(
        time_pattern,
        replace_time,
        speech_text
    )

    return speech_text


def create_voice_friendly_message(text):
    """
    Convert long system/database responses into
    short, natural chatbot speech.
    """

    if not text:
        return ""

    # --------------------------------------------------------
    # Appointment confirmation
    # --------------------------------------------------------

    appointment_pattern = re.search(
        r"Appointment ID:\s*(\d+).*?"
        r"Name:\s*(.+?)\n.*?"
        r"Date:\s*(\d{2}-\d{2}-\d{4}).*?"
        r"Time:\s*(\d{2}:\d{2})",
        text,
        re.IGNORECASE | re.DOTALL
    )

    if appointment_pattern:

        appointment_id = appointment_pattern.group(1)
        name = appointment_pattern.group(2).strip()
        appointment_date = appointment_pattern.group(3)
        appointment_time = appointment_pattern.group(4)

        spoken_date = prepare_text_for_speech(
            appointment_date
        )

        spoken_time = prepare_text_for_speech(
            appointment_time
        )

        return (
            f"Appointment confirmed. "
            f"{name}, your appointment is on "
            f"{spoken_date} at {spoken_time}."
        )

    # --------------------------------------------------------
    # Simple success messages
    # --------------------------------------------------------

    if "cancelled successfully" in text.lower():

        return "Your appointment has been cancelled successfully."

    if "rescheduled successfully" in text.lower():

        return "Your appointment has been rescheduled successfully."

    # --------------------------------------------------------
    # Missing information
    # --------------------------------------------------------

    if "missing information" in text.lower():

        return text.replace("⚠️", "").strip()

    # --------------------------------------------------------
    # General response
    # --------------------------------------------------------

    return prepare_text_for_speech(text)


def generate_voice_reply(text):

    if not text or not text.strip():
        return None

    try:

        # ----------------------------------------------------
        # Create short voice-friendly message
        # ----------------------------------------------------

        speech_text = create_voice_friendly_message(text)

        print("📝 Original response:")
        print(text)

        print("\n🔊 Voice-friendly response:")
        print(speech_text)

        # ----------------------------------------------------
        # Safety check for Groq TTS 200-character limit
        # ----------------------------------------------------

        if len(speech_text) > 200:
            print(
                "\n⚠️ Voice response is longer than 200 characters."
            )

            speech_text = speech_text[:200].rsplit(" ", 1)[0] + "."

        # ----------------------------------------------------
        # Generate WAV audio
        # ----------------------------------------------------

        speech_file = "voice_reply.wav"

        response = groq_client.audio.speech.create(
            model=TTS_MODEL,
            voice=TTS_VOICE,
            input=speech_text,
            response_format="wav",
            speed=TTS_SPEED
        )

        response.write_to_file(speech_file)

        print("\n🔊 Voice generated successfully.")
        print(f"🎙️ Voice : {TTS_VOICE}")
        print(f"🐢 Speed : {TTS_SPEED}")
        print(f"📁 File  : {speech_file}")

        return speech_file

    except Exception as e:

        print("\n❌ Voice reply error:")
        print(type(e).__name__)
        print(str(e))

        return None


# ============================================================
# ORIGINAL NOTEBOOK CODE CELL 37
# ============================================================

# ============================================================
# CREATE CORRECT VOICE MESSAGE FOR EACH ACTION
# ============================================================

def create_voice_friendly_message(text):

    if not text:
        return ""

    clean_text = text.strip()

    # --------------------------------------------------------
    # CANCEL APPOINTMENT
    # --------------------------------------------------------

    if "appointment cancelled successfully" in clean_text.lower():

        appointment_match = re.search(
            r"Appointment ID:\s*(\d+)",
            clean_text,
            re.IGNORECASE
        )

        if appointment_match:
            appointment_id = appointment_match.group(1)

            return (
                f"Appointment {appointment_id} "
                f"has been cancelled successfully."
            )

        return "Your appointment has been cancelled successfully."

    # --------------------------------------------------------
    # RESCHEDULE APPOINTMENT
    # --------------------------------------------------------

    if "appointment rescheduled successfully" in clean_text.lower():

        appointment_match = re.search(
            r"Appointment ID:\s*(\d+)",
            clean_text,
            re.IGNORECASE
        )

        if appointment_match:
            appointment_id = appointment_match.group(1)

            return (
                f"Appointment {appointment_id} "
                f"has been rescheduled successfully."
            )

        return "Your appointment has been rescheduled successfully."

    # --------------------------------------------------------
    # BOOK APPOINTMENT
    # --------------------------------------------------------

    appointment_pattern = re.search(
        r"Appointment ID:\s*(\d+).*?"
        r"Name:\s*(.+?)\n.*?"
        r"Date:\s*(\d{2}-\d{2}-\d{4}).*?"
        r"Time:\s*(\d{2}:\d{2})",
        clean_text,
        re.IGNORECASE | re.DOTALL
    )

    if appointment_pattern:

        appointment_id = appointment_pattern.group(1)
        name = appointment_pattern.group(2).strip()
        appointment_date = appointment_pattern.group(3)
        appointment_time = appointment_pattern.group(4)

        spoken_date = prepare_text_for_speech(
            appointment_date
        )

        spoken_time = prepare_text_for_speech(
            appointment_time
        )

        return (
            f"Appointment confirmed. "
            f"{name}, your appointment is on "
            f"{spoken_date} at {spoken_time}."
        )

    # --------------------------------------------------------
    # MISSING INFORMATION
    # --------------------------------------------------------

    if "missing information" in clean_text.lower():

        return clean_text.replace("⚠️", "").strip()

    # --------------------------------------------------------
    # GENERAL RESPONSE
    # --------------------------------------------------------

    return prepare_text_for_speech(clean_text)


# ============================================================
# ORIGINAL NOTEBOOK CODE CELL 38
# ============================================================

# ============================================================
# TEST CANCELLATION VOICE
# ============================================================

test_cancel_message = """
Appointment cancelled successfully!
Appointment ID: 4
Name: Kalimathie
Date: 03-09-2026
Time: 11:30
"""

test_cancel_voice = generate_voice_reply(
    test_cancel_message
)

print("\n✅ Cancellation voice test completed.")


# ============================================================
# ORIGINAL NOTEBOOK CODE CELL 39
# ============================================================

# ============================================================
# VALIDATE APPOINTMENT DATA + EMAIL
# ============================================================

import re


def is_valid_email(email):
    """
    Validate email address format.
    """

    if not email:
        return False

    email = email.strip()

    # Basic but reliable email format validation
    pattern = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"

    return bool(re.match(pattern, email))


def validate_appointment_data(data):

    if not data:
        return {
            "valid": False,
            "missing": [],
            "message": "❌ No appointment information found."
        }

    required_fields = {
        "name": "Name",
        "appointment_date": "Appointment date",
        "appointment_time": "Appointment time",
        "email": "Email address"
    }

    missing = []

    # --------------------------------------------------------
    # Check required fields
    # --------------------------------------------------------

    for field, display_name in required_fields.items():

        value = data.get(field, "")

        if not value or not str(value).strip():
            missing.append(display_name)

    if missing:

        return {
            "valid": False,
            "missing": missing,
            "message": (
                "⚠️ Missing information: "
                + ", ".join(missing)
            )
        }

    # --------------------------------------------------------
    # Validate email format
    # --------------------------------------------------------

    email = str(data.get("email", "")).strip()

    if not is_valid_email(email):

        return {
            "valid": False,
            "missing": [],
            "message": (
                "❌ Invalid email address. "
                "Please enter a valid email address."
            )
        }

    # --------------------------------------------------------
    # All validation passed
    # --------------------------------------------------------

    return {
        "valid": True,
        "missing": [],
        "message": "✅ All required appointment information is valid."
    }


# ============================================================
# ORIGINAL NOTEBOOK CODE CELL 40
# ============================================================

# ============================================================
# OPTIMIZED VOICE-FRIENDLY RESPONSES
# ============================================================

def create_voice_friendly_message(text):

    if not text:
        return ""

    clean_text = text.strip()
    lower_text = clean_text.lower()

    # --------------------------------------------------------
    # CANCEL
    # --------------------------------------------------------

    if "appointment cancelled successfully" in lower_text:

        appointment_match = re.search(
            r"Appointment ID:\s*(\d+)",
            clean_text,
            re.IGNORECASE
        )

        if appointment_match:

            appointment_id = appointment_match.group(1)

            return (
                f"Appointment {appointment_id} "
                f"has been cancelled successfully."
            )

        return "Your appointment has been cancelled successfully."

    # --------------------------------------------------------
    # RESCHEDULE
    # --------------------------------------------------------

    if "appointment rescheduled successfully" in lower_text:

        appointment_match = re.search(
            r"Appointment ID:\s*(\d+)",
            clean_text,
            re.IGNORECASE
        )

        if appointment_match:

            appointment_id = appointment_match.group(1)

            return (
                f"Appointment {appointment_id} "
                f"has been rescheduled successfully."
            )

        return "Your appointment has been rescheduled successfully."

    # --------------------------------------------------------
    # BOOKING
    # --------------------------------------------------------

    if "appointment booked successfully" in lower_text:

        appointment_pattern = re.search(
            r"Appointment ID:\s*(\d+).*?"
            r"Name:\s*(.+?)\n.*?"
            r"Date:\s*(\d{2}-\d{2}-\d{4}).*?"
            r"Time:\s*(\d{2}:\d{2})",
            clean_text,
            re.IGNORECASE | re.DOTALL
        )

        if appointment_pattern:

            name = appointment_pattern.group(2).strip()
            appointment_date = appointment_pattern.group(3)
            appointment_time = appointment_pattern.group(4)

            spoken_date = prepare_text_for_speech(
                appointment_date
            )

            spoken_time = prepare_text_for_speech(
                appointment_time
            )

            return (
                f"Appointment confirmed. "
                f"{name}, your appointment is on "
                f"{spoken_date} at {spoken_time}."
            )

        return "Your appointment has been booked successfully."

    # --------------------------------------------------------
    # MISSING INFORMATION
    # --------------------------------------------------------

    if "missing information" in lower_text:

        if "email address" in lower_text and "appointment date" not in lower_text:

            return "Please provide your email address."

        if "appointment date" in lower_text and "email address" in lower_text:

            return "Please provide the appointment date and your email address."

        return "Please provide the missing appointment information."

    # --------------------------------------------------------
    # LIST APPOINTMENTS
    # --------------------------------------------------------

    if "booked appointments" in lower_text:

        appointment_ids = re.findall(
            r"Appointment ID\s*:\s*(\d+)",
            clean_text,
            re.IGNORECASE
        )

        if appointment_ids:

            count = len(appointment_ids)

            if count == 1:
                return (
                    f"You have one booked appointment. "
                    f"The appointment ID is {appointment_ids[0]}."
                )

            ids_text = ", ".join(appointment_ids[:-1])

            if len(appointment_ids) > 1:
                ids_text += f", and {appointment_ids[-1]}"

            return (
                f"You have {count} booked appointments. "
                f"The appointment IDs are {ids_text}."
            )

        return "You currently have no booked appointments."

    # --------------------------------------------------------
    # PLEASE RECORD
    # --------------------------------------------------------

    if "please record your request" in lower_text:

        return "Please record your appointment request."

    # --------------------------------------------------------
    # GENERAL RESPONSE
    # --------------------------------------------------------

    return prepare_text_for_speech(clean_text)


# ============================================================
# ORIGINAL NOTEBOOK CODE CELL 41
# ============================================================

# ============================================================
# FINAL GRADIO UI - VOICE APPOINTMENT CHATBOT
# ============================================================

import gradio as gr
import json


# ============================================================
# PROCESS VOICE REQUEST FOR GRADIO
# ============================================================

def process_voice_for_ui(audio_file):

    # --------------------------------------------------------
    # No audio
    # --------------------------------------------------------

    if not audio_file:

        message = "🎤 Please record your appointment request."

        # Do not waste TTS quota when there is no audio
        return (
            "",
            "",
            message,
            None,
            "",
            display_appointments(),
            None
        )

    # --------------------------------------------------------
    # Process voice
    # --------------------------------------------------------

    result = process_voice_action(audio_file)

    transcription = result.get("transcription", "")
    ai_data = result.get("ai_data")

    # --------------------------------------------------------
    # AI could not understand request
    # --------------------------------------------------------

    if not ai_data:

        message = result.get(
            "message",
            "Sorry, I could not understand your request."
        )

        voice_reply = generate_voice_reply(message)

        return (
            transcription,
            "",
            message,
            voice_reply,
            "",
            display_appointments(),
            None
        )

    # --------------------------------------------------------
    # BOOK APPOINTMENT
    # --------------------------------------------------------

    if ai_data.get("intent") == "book":

        validation = validate_appointment_data(ai_data)

        # ----------------------------------------------------
        # Missing information
        # ----------------------------------------------------

        if not validation["valid"]:

            missing = validation["missing"]

            message = (
                "Missing information: "
                + ", ".join(missing)
                + ". Please enter the missing information below."
            )

            voice_reply = generate_voice_reply(message)

            # Keep pending appointment information
            return (
                transcription,
                json.dumps(ai_data, indent=2),
                f"⚠️ {message}",
                voice_reply,
                "",
                display_appointments(),
                ai_data
            )

        # ----------------------------------------------------
        # Complete booking
        # ----------------------------------------------------

        booking_result = process_booking(ai_data)

        message = booking_result["message"]

        voice_reply = generate_voice_reply(message)

        return (
            transcription,
            json.dumps(ai_data, indent=2),
            message,
            voice_reply,
            "",
            display_appointments(),
            None
        )

    # --------------------------------------------------------
    # CANCEL / RESCHEDULE / LIST
    # --------------------------------------------------------

    message = result.get(
        "message",
        "Request processed."
    )

    voice_reply = generate_voice_reply(message)

    return (
        transcription,
        json.dumps(ai_data, indent=2),
        message,
        voice_reply,
        "",
        display_appointments(),
        None
    )


# ============================================================
# COMPLETE BOOKING WITH EMAIL
# ============================================================

def complete_booking_with_email(email, pending_data):

    # --------------------------------------------------------
    # No pending appointment
    # --------------------------------------------------------

    if not pending_data:

        message = (
            "No pending appointment found. "
            "Please process the voice request again."
        )

        voice_reply = generate_voice_reply(message)

        return (
            f"❌ {message}",
            voice_reply,
            display_appointments(),
            None
        )

    # --------------------------------------------------------
    # Copy pending data
    # --------------------------------------------------------

    pending_data = pending_data.copy()

    pending_data["email"] = (
        email.strip()
        if email
        else ""
    )

    # --------------------------------------------------------
    # Validate
    # --------------------------------------------------------

    validation = validate_appointment_data(
        pending_data
    )

    if not validation["valid"]:

        message = (
            "Missing information: "
            + ", ".join(validation["missing"])
        )

        voice_reply = generate_voice_reply(message)

        return (
            f"⚠️ {message}",
            voice_reply,
            display_appointments(),
            pending_data
        )

    # --------------------------------------------------------
    # Book appointment
    # --------------------------------------------------------

    result = process_booking(
        pending_data
    )

    message = result["message"]

    voice_reply = generate_voice_reply(
        message
    )

    # --------------------------------------------------------
    # Clear pending data after successful booking
    # --------------------------------------------------------

    if result["success"]:

        return (
            message,
            voice_reply,
            display_appointments(),
            None
        )

    # --------------------------------------------------------
    # Keep pending data if booking failed
    # --------------------------------------------------------

    return (
        message,
        voice_reply,
        display_appointments(),
        pending_data
    )


# ============================================================
# CLEAR INTERFACE
# ============================================================

def clear_interface():

    return (
        None,                    # Audio
        "",                      # Transcription
        "",                      # AI Understanding
        "",                      # Status
        None,                    # Voice Reply
        "",                      # Email
        display_appointments(),  # Appointments
        None                     # Pending Data
    )


# ============================================================
# GRADIO APPLICATION
# ============================================================

with gr.Blocks(
    title="Voice Appointment Chatbot"
) as app:

    # --------------------------------------------------------
    # TITLE
    # --------------------------------------------------------

    gr.Markdown(
        """
# 🎤 Voice Appointment Chatbot

### AI-Powered Appointment Scheduling System

**Book • Cancel • Reschedule • List • Email Confirmation • Voice Reply • Automatic Reminders**
"""
    )

    # --------------------------------------------------------
    # VOICE INPUT
    # --------------------------------------------------------

    gr.Markdown(
        """
## 🎤 Voice Appointment
Record your appointment request using your microphone.
"""
    )

    audio_input = gr.Audio(
        sources=["microphone"],
        type="filepath",
        label="🎤 Record your appointment request"
    )

    # --------------------------------------------------------
    # BUTTONS
    # --------------------------------------------------------

    with gr.Row():

        process_button = gr.Button(
            "🎤 Process Voice",
            variant="primary"
        )

        clear_button = gr.Button(
            "🗑️ Clear"
        )

    # --------------------------------------------------------
    # TRANSCRIPTION
    # --------------------------------------------------------

    transcription_output = gr.Textbox(
        label="📝 Transcription",
        lines=3,
        interactive=False
    )

    # --------------------------------------------------------
    # AI UNDERSTANDING
    # --------------------------------------------------------

    ai_output = gr.Textbox(
        label="🤖 AI Understanding",
        lines=10,
        interactive=False
    )

    # --------------------------------------------------------
    # STATUS
    # --------------------------------------------------------

    status_output = gr.Textbox(
        label="📢 Status",
        lines=10,
        interactive=False
    )

    # --------------------------------------------------------
    # VOICE REPLY
    # --------------------------------------------------------

    gr.Markdown(
        """
## 🔊 AI Voice Reply
"""
    )

    voice_reply_output = gr.Audio(
        label="🔊 Chatbot Response",
        type="filepath",
        autoplay=True
    )

    # --------------------------------------------------------
    # COMPLETE BOOKING
    # --------------------------------------------------------

    gr.Markdown(
        """
## 📧 Complete Appointment Details

If the email address was not provided in the voice request,
enter it below to complete the booking.
"""
    )

    email_input = gr.Textbox(
        label="Email Address",
        placeholder="Enter email address for confirmation",
        type="email"
    )

    complete_booking_button = gr.Button(
        "✅ Complete Booking",
        variant="primary"
    )

    # --------------------------------------------------------
    # APPOINTMENTS
    # --------------------------------------------------------

    gr.Markdown(
        """
## 📋 Appointments
"""
    )

    appointments_output = gr.Textbox(
        value=display_appointments(),
        label="Booked Appointments",
        lines=20,
        interactive=False
    )

    # --------------------------------------------------------
    # HIDDEN PENDING DATA
    # --------------------------------------------------------

    pending_data = gr.State(None)

    # ========================================================
    # EVENT: PROCESS VOICE
    # ========================================================

    process_button.click(
        fn=process_voice_for_ui,
        inputs=[
            audio_input
        ],
        outputs=[
            transcription_output,
            ai_output,
            status_output,
            voice_reply_output,
            email_input,
            appointments_output,
            pending_data
        ]
    )

    # ========================================================
    # EVENT: COMPLETE BOOKING
    # ========================================================

    complete_booking_button.click(
        fn=complete_booking_with_email,
        inputs=[
            email_input,
            pending_data
        ],
        outputs=[
            status_output,
            voice_reply_output,
            appointments_output,
            pending_data
        ]
    )

    # ========================================================
    # EVENT: CLEAR
    # ========================================================

    clear_button.click(
        fn=clear_interface,
        inputs=[],
        outputs=[
            audio_input,
            transcription_output,
            ai_output,
            status_output,
            voice_reply_output,
            email_input,
            appointments_output,
            pending_data
        ]
    )


# ============================================================
# START AUTOMATIC REMINDER LOOP
# ============================================================

start_reminder_loop()


# ============================================================
# LAUNCH GRADIO
# ============================================================

app.launch(
    share=True,
    debug=True
)

