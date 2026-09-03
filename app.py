import os
import re
import json
import sqlite3
import smtplib
import threading
import time
from datetime import datetime, date, timedelta
from email.message import EmailMessage

import gradio as gr
from groq import Groq


# ============================================================
# CONFIGURATION
# ============================================================

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")

GMAIL_ADDRESS = "dailyscheduletest@gmail.com"

AI_MODEL = "openai/gpt-oss-20b"
STT_MODEL = "whisper-large-v3-turbo"
TTS_MODEL = "canopylabs/orpheus-v1-english"
TTS_VOICE = "hannah"
TTS_SPEED = 0.85

DB_NAME = "appointments.db"
REMINDER_MINUTES = 15


if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY environment variable is not set.")

if not GMAIL_APP_PASSWORD:
    raise ValueError("GMAIL_APP_PASSWORD environment variable is not set.")


groq_client = Groq(api_key=GROQ_API_KEY)


# ============================================================
# DATABASE
# ============================================================

def get_db_connection():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_database():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS appointments (
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


initialize_database()


# ============================================================
# DATE AND TIME
# ============================================================

def validate_date(date_text):
    if not date_text:
        return False

    try:
        appointment_date = datetime.strptime(
            date_text.strip(),
            "%d-%m-%Y"
        ).date()

        return appointment_date >= date.today()

    except (ValueError, TypeError):
        return False


def validate_time(time_text):
    if not time_text:
        return False

    try:
        datetime.strptime(time_text.strip(), "%H:%M")
        return True

    except (ValueError, TypeError):
        return False


def format_time(time_text):
    if not time_text:
        return ""

    formats = [
        "%H:%M",
        "%I:%M %p",
        "%I %p",
        "%I:%M%p",
        "%I%p",
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


# ============================================================
# EMAIL VALIDATION
# ============================================================

def is_valid_email(email):
    if not email:
        return False

    pattern = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
    return bool(re.match(pattern, email.strip()))


# ============================================================
# SPEECH TO TEXT
# ============================================================

def transcribe_audio(audio_file):
    if not audio_file:
        return ""

    try:
        with open(audio_file, "rb") as file:
            transcription = groq_client.audio.transcriptions.create(
                file=file,
                model=STT_MODEL,
                response_format="json",
                language="en",
                temperature=0.0,
            )

        text = transcription.text.strip()

        print("🎤 Transcription:")
        print(text)

        return text

    except Exception as e:
        print(f"❌ Transcription error: {e}")
        return ""


# ============================================================
# AI APPOINTMENT UNDERSTANDING
# ============================================================

def understand_appointment(user_text):
    if not user_text or not user_text.strip():
        return None

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
   Extract the appointment ID when the user provides one.
   Example: "cancel appointment 5" -> "5"
   If not provided, use "".

3. appointment_date must use DD-MM-YYYY.

4. appointment_time must use HH:MM in 24-hour format.

5. If the user says "today", use today's date.

6. If the user says "tomorrow", calculate tomorrow's date
   based on today's date ({today_date}).

7. If information is missing, keep that field as "".

8. Do not invent missing information.

9. Extract the person's name carefully.

10. Extract the email address if provided.

11. Extract the purpose if provided.

12. For cancellation, extract appointment_id.
    Do not invent an appointment ID.

13. For rescheduling, extract:
    appointment_id, new appointment_date and new appointment_time.

14. For listing appointments, intent must be "list".

15. Return ONLY valid JSON.
"""

    try:
        response = groq_client.chat.completions.create(
            model=AI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_text,
                },
            ],
            temperature=0,
            response_format={"type": "json_object"},
        )

        raw_response = response.choices[0].message.content
        result = json.loads(raw_response)

        print("🤖 AI Understanding:")
        print(json.dumps(result, indent=2))

        return result

    except Exception as e:
        print(f"❌ AI Understanding Error: {e}")
        return None


# ============================================================
# BOOK APPOINTMENT
# ============================================================

def book_appointment(
    name,
    appointment_date,
    appointment_time,
    purpose,
    email,
):
    if not name or not name.strip():
        return {
            "success": False,
            "message": "❌ Name is required.",
        }

    if not appointment_date:
        return {
            "success": False,
            "message": "❌ Appointment date is required.",
        }

    if not validate_date(appointment_date):
        return {
            "success": False,
            "message": "❌ Invalid date. Please use DD-MM-YYYY format.",
        }

    if not appointment_time:
        return {
            "success": False,
            "message": "❌ Appointment time is required.",
        }

    appointment_time = format_time(appointment_time)

    if not appointment_time:
        return {
            "success": False,
            "message": "❌ Invalid time. Example: 10:30 AM",
        }

    if not is_valid_email(email):
        return {
            "success": False,
            "message": "❌ Please provide a valid email address.",
        }

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id
        FROM appointments
        WHERE appointment_date = ?
        AND appointment_time = ?
    """, (
        appointment_date.strip(),
        appointment_time,
    ))

    existing = cursor.fetchone()

    if existing:
        conn.close()

        return {
            "success": False,
            "message": (
                "❌ This time slot is already booked.\n\n"
                f"📅 {appointment_date}\n"
                f"⏰ {appointment_time}"
            ),
        }

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
        REMINDER_MINUTES,
        0,
        None,
    ))

    appointment_id = cursor.lastrowid

    conn.commit()
    conn.close()

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
            f"🔔 Reminder: {REMINDER_MINUTES} minutes before"
        ),
    }


# ============================================================
# CANCEL APPOINTMENT
# ============================================================

def cancel_appointment(appointment_id):
    if not appointment_id:
        return {
            "success": False,
            "message": "❌ Appointment ID is required.",
        }

    try:
        appointment_id = int(appointment_id)
    except (ValueError, TypeError):
        return {
            "success": False,
            "message": "❌ Invalid Appointment ID.",
        }

    conn = get_db_connection()
    cursor = conn.cursor()

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
                f"❌ Appointment ID {appointment_id} was not found."
            ),
        }

    cursor.execute("""
        DELETE FROM appointments
        WHERE id = ?
    """, (appointment_id,))

    conn.commit()
    conn.close()

    return {
        "success": True,
        "message": (
            "✅ Appointment cancelled successfully!\n\n"
            f"🆔 Appointment ID: {appointment_id}\n"
            f"👤 Name: {appointment['name']}\n"
            f"📅 Date: {appointment['appointment_date']}\n"
            f"⏰ Time: {appointment['appointment_time']}"
        ),
    }


# ============================================================
# RESCHEDULE APPOINTMENT
# ============================================================

def reschedule_appointment(
    appointment_id,
    new_date,
    new_time,
):
    if not appointment_id:
        return {
            "success": False,
            "message": "❌ Appointment ID is required.",
        }

    try:
        appointment_id = int(appointment_id)
    except (ValueError, TypeError):
        return {
            "success": False,
            "message": "❌ Invalid Appointment ID.",
        }

    if not new_date:
        return {
            "success": False,
            "message": "❌ New appointment date is required.",
        }

    if not validate_date(new_date):
        return {
            "success": False,
            "message": (
                "❌ Invalid date. "
                "Please use DD-MM-YYYY format."
            ),
        }

    if not new_time:
        return {
            "success": False,
            "message": "❌ New appointment time is required.",
        }

    new_time = format_time(new_time)

    if not new_time:
        return {
            "success": False,
            "message": "❌ Invalid time.",
        }

    conn = get_db_connection()
    cursor = conn.cursor()

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
            ),
        }

    cursor.execute("""
        SELECT id
        FROM appointments
        WHERE appointment_date = ?
        AND appointment_time = ?
        AND id != ?
    """, (
        new_date.strip(),
        new_time,
        appointment_id,
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
            ),
        }

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
        appointment_id,
    ))

    conn.commit()
    conn.close()

    return {
        "success": True,
        "message": (
            "✅ Appointment rescheduled successfully!\n\n"
            f"🆔 Appointment ID: {appointment_id}\n"
            f"👤 Name: {appointment['name']}\n"
            f"📅 New Date: {new_date.strip()}\n"
            f"⏰ New Time: {new_time}\n"
            f"📧 Email: {appointment['email']}"
        ),
    }


# ============================================================
# LIST APPOINTMENTS
# ============================================================

def get_appointments():
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


# ============================================================
# EMAIL
# ============================================================

def send_email(subject, name, appointment_date, appointment_time,
               purpose, customer_email, appointment_id, reminder=False):
    try:
        message = EmailMessage()

        message["From"] = GMAIL_ADDRESS
        message["To"] = customer_email
        message["Subject"] = subject

        if reminder:
            intro = "This is a reminder about your upcoming appointment."
            ending = "Please make sure you are available at the scheduled time."
        else:
            intro = "Your appointment has been successfully booked."
            ending = "You will receive a reminder 15 minutes before your appointment."

        email_body = f"""
Hello {name},

{intro}

Appointment Details
-------------------
Appointment ID : {appointment_id}
Name           : {name}
Date           : {appointment_date}
Time           : {appointment_time}
Purpose        : {purpose if purpose else "Not specified"}

{ending}

Thank you.

Best regards,
Appointment Scheduling Assistant
"""

        message.set_content(email_body)

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            smtp.send_message(message)

        return True

    except Exception as e:
        print(f"❌ Email error: {e}")
        return False


def send_confirmation_email(
    name,
    appointment_date,
    appointment_time,
    purpose,
    customer_email,
    appointment_id,
):
    return send_email(
        "Appointment Confirmation",
        name,
        appointment_date,
        appointment_time,
        purpose,
        customer_email,
        appointment_id,
        reminder=False,
    )


def send_reminder_email(
    name,
    appointment_date,
    appointment_time,
    purpose,
    customer_email,
    appointment_id,
):
    return send_email(
        "Appointment Reminder",
        name,
        appointment_date,
        appointment_time,
        purpose,
        customer_email,
        appointment_id,
        reminder=True,
    )


# ============================================================
# REMINDER CHECKER
# ============================================================

def check_and_send_reminders():
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
            appointment_datetime = datetime.strptime(
                f"{appointment['appointment_date']} "
                f"{appointment['appointment_time']}",
                "%d-%m-%Y %H:%M",
            )

            reminder_datetime = (
                appointment_datetime
                - timedelta(minutes=appointment["reminder_minutes"])
            )

            current_datetime = datetime.now()

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
                    appointment_id=appointment["id"],
                )

                if success:
                    cursor.execute("""
                        UPDATE appointments
                        SET reminder_sent = 1,
                            reminder_sent_at = ?
                        WHERE id = ?
                    """, (
                        datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
                        appointment["id"],
                    ))

                    conn.commit()
                    reminders_sent += 1

        except Exception as e:
            print(
                f"❌ Error processing Appointment "
                f"ID {appointment['id']}: {e}"
            )

    conn.close()

    return reminders_sent


reminder_loop_running = False


def reminder_loop():
    global reminder_loop_running

    while reminder_loop_running:
        try:
            check_and_send_reminders()
        except Exception as e:
            print(f"❌ Reminder loop error: {e}")

        time.sleep(60)


def start_reminder_loop():
    global reminder_loop_running

    if reminder_loop_running:
        return

    reminder_loop_running = True

    reminder_thread = threading.Thread(
        target=reminder_loop,
        daemon=True,
    )

    reminder_thread.start()

    print("🔔 Automatic reminder loop started.")


# ============================================================
# VALIDATION
# ============================================================

def validate_appointment_data(data):
    if not data:
        return {
            "valid": False,
            "missing": [],
            "message": "❌ No appointment information found.",
        }

    required_fields = {
        "name": "Name",
        "appointment_date": "Appointment date",
        "appointment_time": "Appointment time",
        "email": "Email address",
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
            ),
        }

    if not is_valid_email(data["email"]):
        return {
            "valid": False,
            "missing": [],
            "message": (
                "❌ Invalid email address. "
                "Please enter a valid email address."
            ),
        }

    return {
        "valid": True,
        "missing": [],
        "message": "✅ All required appointment information is valid.",
    }


# ============================================================
# BOOKING WORKFLOW
# ============================================================

def process_booking(data):
    validation = validate_appointment_data(data)

    if not validation["valid"]:
        return {
            "success": False,
            "message": validation["message"],
            "appointment_id": None,
        }

    booking_result = book_appointment(
        name=data["name"],
        appointment_date=data["appointment_date"],
        appointment_time=data["appointment_time"],
        purpose=data.get("purpose", ""),
        email=data["email"],
    )

    if not booking_result["success"]:
        return {
            "success": False,
            "message": booking_result["message"],
            "appointment_id": None,
        }

    appointment_id = booking_result["appointment_id"]

    email_sent = send_confirmation_email(
        name=data["name"],
        appointment_date=data["appointment_date"],
        appointment_time=data["appointment_time"],
        purpose=data.get("purpose", ""),
        customer_email=data["email"],
        appointment_id=appointment_id,
    )

    if email_sent:
        message = (
            booking_result["message"]
            + "\n\n📧 Confirmation email sent successfully."
        )
    else:
        message = (
            booking_result["message"]
            + "\n\n⚠️ Appointment was booked, "
              "but confirmation email could not be sent."
        )

    return {
        "success": True,
        "appointment_id": appointment_id,
        "message": message,
    }


# ============================================================
# APPOINTMENT ACTION HANDLER
# ============================================================

def handle_appointment_action(data):
    if not data:
        return {
            "success": False,
            "message": "❌ No appointment information available.",
        }

    intent = data.get("intent", "").lower().strip()

    if intent == "book":
        return process_booking(data)

    if intent == "list":
        return {
            "success": True,
            "message": display_appointments(),
        }

    if intent == "cancel":
        appointment_id = data.get("appointment_id")

        if not appointment_id:
            return {
                "success": False,
                "message": (
                    "⚠️ Please provide the Appointment ID "
                    "you want to cancel."
                ),
            }

        return cancel_appointment(appointment_id)

    if intent == "reschedule":
        appointment_id = data.get("appointment_id")
        new_date = data.get("appointment_date")
        new_time = data.get("appointment_time")

        if not appointment_id:
            return {
                "success": False,
                "message": (
                    "⚠️ Please provide the Appointment ID "
                    "you want to reschedule."
                ),
            }

        if not new_date or not new_time:
            return {
                "success": False,
                "message": (
                    "⚠️ Please provide the new "
                    "appointment date and time."
                ),
            }

        return reschedule_appointment(
            appointment_id,
            new_date,
            new_time,
        )

    return {
        "success": False,
        "message": f"❌ Unsupported appointment action: {intent}",
    }


# ============================================================
# VOICE WORKFLOW
# ============================================================

def process_voice_action(audio_file):
    if not audio_file:
        return {
            "success": False,
            "transcription": "",
            "ai_data": None,
            "message": "🎤 Please record your request.",
        }

    transcription = transcribe_audio(audio_file)

    if not transcription:
        return {
            "success": False,
            "transcription": "",
            "ai_data": None,
            "message": "❌ Could not understand the audio.",
        }

    ai_data = understand_appointment(transcription)

    if not ai_data:
        return {
            "success": False,
            "transcription": transcription,
            "ai_data": None,
            "message": (
                "❌ Could not understand "
                "the appointment request."
            ),
        }

    action_result = handle_appointment_action(ai_data)

    return {
        "success": action_result["success"],
        "transcription": transcription,
        "ai_data": ai_data,
        "message": action_result["message"],
    }


# ============================================================
# VOICE-FRIENDLY RESPONSE
# ============================================================

def prepare_text_for_speech(text):
    if not text:
        return ""

    speech_text = text.strip()

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
        speech_text,
    )

    time_pattern = r"\b([01]\d|2[0-3]):([0-5]\d)\b"

    def replace_time(match):
        hour = int(match.group(1))
        minute = int(match.group(2))

        try:
            time_object = datetime.strptime(
                f"{hour:02d}:{minute:02d}",
                "%H:%M",
            )

            if minute == 0:
                return time_object.strftime("%-I %p")

            return time_object.strftime("%-I:%M %p")

        except ValueError:
            return match.group(0)

    speech_text = re.sub(
        time_pattern,
        replace_time,
        speech_text,
    )

    return speech_text


def create_voice_friendly_message(text):
    if not text:
        return ""

    clean_text = text.strip()
    lower_text = clean_text.lower()

    if "appointment cancelled successfully" in lower_text:
        match = re.search(
            r"Appointment ID:\s*(\d+)",
            clean_text,
            re.IGNORECASE,
        )

        if match:
            return (
                f"Appointment {match.group(1)} "
                "has been cancelled successfully."
            )

        return "Your appointment has been cancelled successfully."

    if "appointment rescheduled successfully" in lower_text:
        match = re.search(
            r"Appointment ID:\s*(\d+)",
            clean_text,
            re.IGNORECASE,
        )

        if match:
            return (
                f"Appointment {match.group(1)} "
                "has been rescheduled successfully."
            )

        return "Your appointment has been rescheduled successfully."

    if "appointment booked successfully" in lower_text:
        match = re.search(
            r"Appointment ID:\s*(\d+).*?"
            r"Name:\s*(.+?)\n.*?"
            r"Date:\s*(\d{2}-\d{2}-\d{4}).*?"
            r"Time:\s*(\d{2}:\d{2})",
            clean_text,
            re.IGNORECASE | re.DOTALL,
        )

        if match:
            name = match.group(2).strip()
            appointment_date = prepare_text_for_speech(match.group(3))
            appointment_time = prepare_text_for_speech(match.group(4))

            return (
                f"Appointment confirmed. {name}, "
                f"your appointment is on "
                f"{appointment_date} at {appointment_time}."
            )

        return "Your appointment has been booked successfully."

    if "missing information" in lower_text:
        if (
            "email address" in lower_text
            and "appointment date" not in lower_text
        ):
            return "Please provide your email address."

        if (
            "appointment date" in lower_text
            and "email address" in lower_text
        ):
            return (
                "Please provide the appointment date "
                "and your email address."
            )

        return "Please provide the missing appointment information."

    if "booked appointments" in lower_text:
        appointment_ids = re.findall(
            r"Appointment ID\s*:\s*(\d+)",
            clean_text,
            re.IGNORECASE,
        )

        if appointment_ids:
            count = len(appointment_ids)

            if count == 1:
                return (
                    "You have one booked appointment. "
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

    if "please record your request" in lower_text:
        return "Please record your appointment request."

    return prepare_text_for_speech(clean_text)


def generate_voice_reply(text):
    if not text or not text.strip():
        return None

    try:
        speech_text = create_voice_friendly_message(text)

        if len(speech_text) > 200:
            speech_text = speech_text[:200].rsplit(" ", 1)[0] + "."

        speech_file = "voice_reply.wav"

        response = groq_client.audio.speech.create(
            model=TTS_MODEL,
            voice=TTS_VOICE,
            input=speech_text,
            response_format="wav",
            speed=TTS_SPEED,
        )

        response.write_to_file(speech_file)

        return speech_file

    except Exception as e:
        print(f"❌ Voice reply error: {e}")
        return None


# ============================================================
# GRADIO CALLBACKS
# ============================================================

def process_voice_for_ui(audio_file):
    if not audio_file:
        message = "🎤 Please record your appointment request."

        return (
            "",
            "",
            message,
            None,
            "",
            display_appointments(),
            None,
        )

    result = process_voice_action(audio_file)

    transcription = result.get("transcription", "")
    ai_data = result.get("ai_data")

    if not ai_data:
        message = result.get(
            "message",
            "Sorry, I could not understand your request.",
        )

        voice_reply = generate_voice_reply(message)

        return (
            transcription,
            "",
            message,
            voice_reply,
            "",
            display_appointments(),
            None,
        )

    if ai_data.get("intent") == "book":
        validation = validate_appointment_data(ai_data)

        if not validation["valid"]:
            message = (
                "Missing information: "
                + ", ".join(validation["missing"])
                + ". Please enter the missing information below."
            )

            voice_reply = generate_voice_reply(message)

            return (
                transcription,
                json.dumps(ai_data, indent=2),
                f"⚠️ {message}",
                voice_reply,
                "",
                display_appointments(),
                ai_data,
            )

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
            None,
        )

    message = result.get(
        "message",
        "Request processed.",
    )

    voice_reply = generate_voice_reply(message)

    return (
        transcription,
        json.dumps(ai_data, indent=2),
        message,
        voice_reply,
        "",
        display_appointments(),
        None,
    )


def complete_booking_with_email(email, pending_data):
    if not pending_data:
        message = (
            "No pending appointment found. "
            "Please process the voice request again."
        )

        return (
            f"❌ {message}",
            generate_voice_reply(message),
            display_appointments(),
            None,
        )

    pending_data = pending_data.copy()
    pending_data["email"] = email.strip() if email else ""

    validation = validate_appointment_data(pending_data)

    if not validation["valid"]:
        message = (
            "Missing information: "
            + ", ".join(validation["missing"])
        )

        return (
            f"⚠️ {message}",
            generate_voice_reply(message),
            display_appointments(),
            pending_data,
        )

    result = process_booking(pending_data)
    message = result["message"]
    voice_reply = generate_voice_reply(message)

    if result["success"]:
        return (
            message,
            voice_reply,
            display_appointments(),
            None,
        )

    return (
        message,
        voice_reply,
        display_appointments(),
        pending_data,
    )


def clear_interface():
    return (
        None,
        "",
        "",
        "",
        None,
        "",
        display_appointments(),
        None,
    )


# ============================================================
# GRADIO APPLICATION
# ============================================================

with gr.Blocks(title="Voice Appointment Chatbot") as app:

    gr.Markdown("""
# 🎤 Voice Appointment Chatbot

### AI-Powered Appointment Scheduling System

**Book • Cancel • Reschedule • List • Email Confirmation • Voice Reply • Automatic Reminders**
""")

    gr.Markdown("""
## 🎤 Voice Appointment

Record your appointment request using your microphone.
""")

    audio_input = gr.Audio(
        sources=["microphone"],
        type="filepath",
        label="🎤 Record your appointment request",
    )

    with gr.Row():
        process_button = gr.Button(
            "🎤 Process Voice",
            variant="primary",
        )

        clear_button = gr.Button("🗑️ Clear")

    transcription_output = gr.Textbox(
        label="📝 Transcription",
        lines=3,
        interactive=False,
    )

    ai_output = gr.Textbox(
        label="🤖 AI Understanding",
        lines=10,
        interactive=False,
    )

    status_output = gr.Textbox(
        label="📢 Status",
        lines=10,
        interactive=False,
    )

    gr.Markdown("## 🔊 AI Voice Reply")

    voice_reply_output = gr.Audio(
        label="🔊 Chatbot Response",
        type="filepath",
        autoplay=True,
    )

    gr.Markdown("""
## 📧 Complete Appointment Details

If the email address was not provided in the voice request,
enter it below to complete the booking.
""")

    email_input = gr.Textbox(
        label="Email Address",
        placeholder="Enter email address for confirmation",
        type="email",
    )

    complete_booking_button = gr.Button(
        "✅ Complete Booking",
        variant="primary",
    )

    gr.Markdown("## 📋 Appointments")

    appointments_output = gr.Textbox(
        value=display_appointments(),
        label="Booked Appointments",
        lines=20,
        interactive=False,
    )

    pending_data = gr.State(None)

    process_button.click(
        fn=process_voice_for_ui,
        inputs=[audio_input],
        outputs=[
            transcription_output,
            ai_output,
            status_output,
            voice_reply_output,
            email_input,
            appointments_output,
            pending_data,
        ],
    )

    complete_booking_button.click(
        fn=complete_booking_with_email,
        inputs=[
            email_input,
            pending_data,
        ],
        outputs=[
            status_output,
            voice_reply_output,
            appointments_output,
            pending_data,
        ],
    )

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
            pending_data,
        ],
    )


# ============================================================
# START REMINDER LOOP
# ============================================================

start_reminder_loop()


# ============================================================
# GOOGLE CLOUD RUN
# ============================================================

PORT = int(os.environ.get("PORT", "7860"))

app.launch(
    server_name="0.0.0.0",
    server_port=PORT,
    share=False,
    debug=False,
)
