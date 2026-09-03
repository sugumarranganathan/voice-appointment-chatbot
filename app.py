
import os
import json
import sqlite3
import smtplib
import tempfile
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

APP_TIMEZONE = ZoneInfo("Asia/Kolkata")
from email.message import EmailMessage

import gradio as gr
from groq import Groq
from fastapi import FastAPI, Header, HTTPException
import uvicorn


# ============================================================
# CONFIGURATION
# ============================================================

DB_NAME = os.environ.get(
    "DB_NAME",
    "/content/voice-appointment-chatbot-reminder/appointments.db"
)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")
GMAIL_ADDRESS = os.environ.get(
    "GMAIL_ADDRESS",
    "dailyscheduletest@gmail.com"
)

REMINDER_MINUTES = int(os.environ.get("REMINDER_MINUTES", "15"))
REMINDER_WEBHOOK_SECRET = os.environ.get("REMINDER_WEBHOOK_SECRET")

AI_MODEL = "openai/gpt-oss-20b"
STT_MODEL = "whisper-large-v3-turbo"
TTS_MODEL = "canopylabs/orpheus-v1-english"
TTS_VOICE = "hannah"
TTS_SPEED = 0.85


# ============================================================
# GROQ CLIENT
# ============================================================

client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None


# ============================================================
# DATABASE
# ============================================================

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            appointment_date TEXT NOT NULL,
            appointment_time TEXT NOT NULL,
            purpose TEXT,
            email TEXT,
            reminder_minutes INTEGER DEFAULT 15,
            reminder_sent INTEGER DEFAULT 0,
            reminder_sent_at TEXT
        )
    """)

    conn.commit()
    conn.close()


init_db()


# ============================================================
# EMAIL
# ============================================================

def send_email(to_email, subject, body):
    if not GMAIL_APP_PASSWORD:
        print("GMAIL_APP_PASSWORD is not configured.")
        return False

    try:
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = GMAIL_ADDRESS
        message["To"] = to_email
        message.set_content(body)

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            smtp.send_message(message)

        return True

    except Exception as e:
        print(f"Email error: {e}")
        return False


def send_confirmation_email(appointment):
    subject = "Appointment Confirmation"

    body = f"""
Hello {appointment["name"]},

Your appointment has been successfully booked.

Appointment ID : {appointment["id"]}
Date           : {appointment["appointment_date"]}
Time           : {appointment["appointment_time"]}
Purpose        : {appointment["purpose"] or "Not specified"}

Reminder       : {appointment["reminder_minutes"]} minutes before

Thank you.
Voice Appointment Chatbot
"""

    return send_email(
        appointment["email"],
        subject,
        body
    )


def send_reminder_email(appointment):
    subject = "Appointment Reminder"

    body = f"""
Hello {appointment["name"]},

This is a reminder for your upcoming appointment.

Appointment ID : {appointment["id"]}
Date           : {appointment["appointment_date"]}
Time           : {appointment["appointment_time"]}
Purpose        : {appointment["purpose"] or "Not specified"}

Your appointment is in approximately
{appointment["reminder_minutes"]} minutes.

Thank you.
Voice Appointment Chatbot
"""

    return send_email(
        appointment["email"],
        subject,
        body
    )


# ============================================================
# DATE / TIME VALIDATION
# ============================================================

def valid_date(date_text):
    try:
        return datetime.strptime(date_text, "%d-%m-%Y")
    except ValueError:
        return None


def valid_time(time_text):
    try:
        return datetime.strptime(time_text, "%H:%M")
    except ValueError:
        return None


def normalize_date(date_text):
    value = valid_date(date_text)
    return value.strftime("%d-%m-%Y") if value else None


def normalize_time(time_text):
    value = valid_time(time_text)
    return value.strftime("%H:%M") if value else None


# ============================================================
# APPOINTMENT OPERATIONS
# ============================================================

def book_appointment(
    name,
    appointment_date,
    appointment_time,
    purpose,
    email,
    reminder_minutes=15
):

    appointment_date = normalize_date(appointment_date)
    appointment_time = normalize_time(appointment_time)

    if not name:
        return False, "Name is required."

    if not appointment_date:
        return False, "Date must be in DD-MM-YYYY format."

    if not appointment_time:
        return False, "Time must be in HH:MM 24-hour format."

    if not email:
        return False, "Email is required."

    appointment_datetime = datetime.strptime(
        f"{appointment_date} {appointment_time}",
        "%d-%m-%Y %H:%M"
    )

    if appointment_datetime <= datetime.now():
        return False, "The appointment date and time must be in the future."

    conn = get_db()

    existing = conn.execute("""
        SELECT id
        FROM appointments
        WHERE appointment_date = ?
        AND appointment_time = ?
    """, (
        appointment_date,
        appointment_time
    )).fetchone()

    if existing:
        conn.close()
        return False, "That appointment time is already booked."

    cursor = conn.execute("""
        INSERT INTO appointments
        (
            name,
            appointment_date,
            appointment_time,
            purpose,
            email,
            reminder_minutes,
            reminder_sent
        )
        VALUES (?, ?, ?, ?, ?, ?, 0)
    """, (
        name,
        appointment_date,
        appointment_time,
        purpose,
        email,
        reminder_minutes
    ))

    appointment_id = cursor.lastrowid

    conn.commit()

    appointment = conn.execute("""
        SELECT *
        FROM appointments
        WHERE id = ?
    """, (appointment_id,)).fetchone()

    conn.close()

    email_sent = send_confirmation_email(appointment)

    if email_sent:
        return True, (
            f"Appointment booked successfully. "
            f"Appointment ID: {appointment_id}. "
            f"Confirmation email sent to {email}."
        )

    return True, (
        f"Appointment booked successfully. "
        f"Appointment ID: {appointment_id}. "
        f"However, the confirmation email could not be sent."
    )


def list_appointments():
    conn = get_db()

    rows = conn.execute("""
        SELECT *
        FROM appointments
        ORDER BY appointment_date, appointment_time
    """).fetchall()

    conn.close()

    if not rows:
        return "📋 BOOKED APPOINTMENTS\n" + "=" * 60 + "\n\nNo appointments found."

    output = [
        "📋 BOOKED APPOINTMENTS",
        "=" * 60,
        ""
    ]

    for row in rows:
        reminder_minutes = row["reminder_minutes"] or 15

        reminder_sent = (
            "Yes"
            if row["reminder_sent"]
            else "No"
        )

        output.append(
            f"🆔 Appointment ID : {row['id']}\n"
            f"👤 Name           : {row['name']}\n"
            f"📅 Date           : {row['appointment_date']}\n"
            f"⏰ Time           : {row['appointment_time']}\n"
            f"📝 Purpose        : {row['purpose'] or 'N/A'}\n"
            f"📧 Email          : {row['email'] or 'N/A'}\n"
            f"🔔 Reminder       : {reminder_minutes} minutes before\n"
            f"📨 Reminder Sent  : {reminder_sent}\n"
            f"\n{'-' * 60}\n"
        )

    return "\n".join(output)

def cancel_appointment(appointment_id):
    conn = get_db()

    row = conn.execute("""
        SELECT *
        FROM appointments
        WHERE id = ?
    """, (appointment_id,)).fetchone()

    if not row:
        conn.close()
        return False, "Appointment not found."

    conn.execute("""
        DELETE FROM appointments
        WHERE id = ?
    """, (appointment_id,))

    conn.commit()
    conn.close()

    return True, f"Appointment {appointment_id} cancelled successfully."


def reschedule_appointment(
    appointment_id,
    new_date,
    new_time
):

    new_date = normalize_date(new_date)
    new_time = normalize_time(new_time)

    if not new_date:
        return False, "New date must be in DD-MM-YYYY format."

    if not new_time:
        return False, "New time must be in HH:MM format."

    new_datetime = datetime.strptime(
        f"{new_date} {new_time}",
        "%d-%m-%Y %H:%M"
    )

    if new_datetime <= datetime.now():
        return False, "The new appointment time must be in the future."

    conn = get_db()

    row = conn.execute("""
        SELECT *
        FROM appointments
        WHERE id = ?
    """, (appointment_id,)).fetchone()

    if not row:
        conn.close()
        return False, "Appointment not found."

    conflict = conn.execute("""
        SELECT id
        FROM appointments
        WHERE appointment_date = ?
        AND appointment_time = ?
        AND id != ?
    """, (
        new_date,
        new_time,
        appointment_id
    )).fetchone()

    if conflict:
        conn.close()
        return False, "The new appointment time is already booked."

    conn.execute("""
        UPDATE appointments
        SET appointment_date = ?,
            appointment_time = ?,
            reminder_sent = 0,
            reminder_sent_at = NULL
        WHERE id = ?
    """, (
        new_date,
        new_time,
        appointment_id
    ))

    conn.commit()
    conn.close()

    return True, (
        f"Appointment {appointment_id} rescheduled to "
        f"{new_date} at {new_time}."
    )


# ============================================================
# REMINDER ENGINE
# ============================================================

def check_and_send_reminders():
    conn = get_db()

    rows = conn.execute("""
        SELECT *
        FROM appointments
        WHERE reminder_sent = 0
        AND email IS NOT NULL
        AND email != ''
    """).fetchall()

    # Appointments are stored as India local time.
    # Cloud Run uses UTC by default, so explicitly use Asia/Kolkata.
    now = datetime.now(APP_TIMEZONE).replace(tzinfo=None)
    sent_count = 0

    for appointment in rows:

        try:
            appointment_datetime = datetime.strptime(
                f"{appointment['appointment_date']} "
                f"{appointment['appointment_time']}",
                "%d-%m-%Y %H:%M"
            )

            reminder_datetime = (
                appointment_datetime
                - timedelta(minutes=appointment["reminder_minutes"])
            )

            if (
                now >= reminder_datetime
                and now < appointment_datetime
            ):

                success = send_reminder_email(appointment)

                if success:
                    conn.execute("""
                        UPDATE appointments
                        SET reminder_sent = 1,
                            reminder_sent_at = ?
                        WHERE id = ?
                    """, (
                        now.isoformat(),
                        appointment["id"]
                    ))

                    sent_count += 1

        except Exception as e:
            print(
                f"Reminder processing error "
                f"for appointment {appointment['id']}: {e}"
            )

    conn.commit()
    conn.close()

    return sent_count


# ============================================================
# AI UNDERSTANDING
# ============================================================

def understand_request(text):

    if not client:
        raise RuntimeError("GROQ_API_KEY is not configured.")

    today = datetime.now(APP_TIMEZONE).strftime("%d-%m-%Y")

    system_prompt = f"""
You are an appointment scheduling assistant.

Today's date is {today}.

Understand the user's request and return ONLY valid JSON.

The intent must be exactly one of:
book
cancel
reschedule
list

Date format:
DD-MM-YYYY

Time format:
HH:MM in 24-hour format.

Rules:
- "today" means today's date.
- "tomorrow" means tomorrow's date.
- Convert natural-language dates into DD-MM-YYYY.
- Convert natural-language times into HH:MM.
- Do not invent missing information.
- If the user wants to cancel or reschedule and gives an appointment ID,
  use that ID.
- For reschedule, put the new date and time in new_appointment_date
  and new_appointment_time.

Return these fields:

intent
appointment_id
name
appointment_date
appointment_time
purpose
email
reminder_minutes
new_appointment_date
new_appointment_time
response_text

Nullable fields must use null.

Current date:
{today}
"""

    schema = {
        "type": "object",
        "properties": {
            "intent": {
                "type": "string",
                "enum": [
                    "book",
                    "cancel",
                    "reschedule",
                    "list"
                ]
            },
            "appointment_id": {
                "type": ["integer", "null"]
            },
            "name": {
                "type": ["string", "null"]
            },
            "appointment_date": {
                "type": ["string", "null"]
            },
            "appointment_time": {
                "type": ["string", "null"]
            },
            "purpose": {
                "type": ["string", "null"]
            },
            "email": {
                "type": ["string", "null"]
            },
            "reminder_minutes": {
                "type": ["integer", "null"]
            },
            "new_appointment_date": {
                "type": ["string", "null"]
            },
            "new_appointment_time": {
                "type": ["string", "null"]
            },
            "response_text": {
                "type": "string"
            }
        },
        "required": [
            "intent",
            "appointment_id",
            "name",
            "appointment_date",
            "appointment_time",
            "purpose",
            "email",
            "reminder_minutes",
            "new_appointment_date",
            "new_appointment_time",
            "response_text"
        ],
        "additionalProperties": False
    }

    response = client.chat.completions.create(
        model=AI_MODEL,
        messages=[
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": text
            }
        ],
        temperature=0,
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "appointment_request",
                "schema": schema,
                "strict": True
            }
        }
    )

    return json.loads(
        response.choices[0].message.content
    )


# ============================================================
# SPEECH TO TEXT
# ============================================================

def transcribe_audio(audio_path):

    if not audio_path:
        return ""

    if not client:
        raise RuntimeError("GROQ_API_KEY is not configured.")

    with open(audio_path, "rb") as audio_file:

        result = client.audio.transcriptions.create(
            file=audio_file,
            model=STT_MODEL,
            response_format="verbose_json",
            language="en",
            temperature=0.0
        )

    return result.text


# ============================================================
# TEXT TO SPEECH
# ============================================================


# ============================================================
# VOICE RESPONSE HELPERS
# ============================================================

ORDINALS = {
    1: "first",
    2: "second",
    3: "third",
    4: "fourth",
    5: "fifth",
    6: "sixth",
    7: "seventh",
    8: "eighth",
    9: "ninth",
    10: "tenth",
    11: "eleventh",
    12: "twelfth",
    13: "thirteenth",
    14: "fourteenth",
    15: "fifteenth",
    16: "sixteenth",
    17: "seventeenth",
    18: "eighteenth",
    19: "nineteenth",
    20: "twentieth",
    21: "twenty-first",
    22: "twenty-second",
    23: "twenty-third",
    24: "twenty-fourth",
    25: "twenty-fifth",
    26: "twenty-sixth",
    27: "twenty-seventh",
    28: "twenty-eighth",
    29: "twenty-ninth",
    30: "thirtieth",
    31: "thirty-first"
}


def format_date_for_speech(date_str):
    """
    Convert DD-MM-YYYY into natural English speech.

    Example:
    03-09-2026 -> September third, 2026
    21-09-2026 -> September twenty-first, 2026
    """
    try:
        dt = datetime.strptime(date_str, "%d-%m-%Y")
        return f"{dt.strftime('%B')} {ORDINALS[dt.day]}, {dt.year}"
    except Exception:
        return date_str


def format_time_for_speech(time_str):
    """
    Convert 24-hour HH:MM into natural 12-hour speech.

    Example:
    14:30 -> 2:30 PM
    09:15 -> 9:15 AM
    """
    try:
        dt = datetime.strptime(time_str, "%H:%M")
        hour = dt.hour % 12 or 12
        return f"{hour}:{dt.strftime('%M')} {dt.strftime('%p')}"
    except Exception:
        return time_str


def short_booking_voice(data):
    name = data.get("name") or "you"
    date = format_date_for_speech(data.get("appointment_date", ""))
    time = format_time_for_speech(data.get("appointment_time", ""))

    return (
        f"Appointment booked successfully for {name} "
        f"on {date} at {time}."
    )


def short_reschedule_voice(data):
    date = format_date_for_speech(
        data.get("new_appointment_date", "")
    )
    time = format_time_for_speech(
        data.get("new_appointment_time", "")
    )

    appointment_id = data.get("appointment_id")

    return (
        f"Appointment {appointment_id} has been rescheduled "
        f"to {date} at {time}."
    )


def short_cancel_voice(appointment_id):
    return (
        f"Appointment {appointment_id} has been cancelled successfully."
    )


def short_list_voice():
    conn = get_db()

    row = conn.execute(
        "SELECT COUNT(*) AS count FROM appointments"
    ).fetchone()

    conn.close()

    count = row["count"]

    if count == 0:
        return "There are no booked appointments."

    if count == 1:
        return "You have one booked appointment."

    return f"You have {count} booked appointments."


def generate_voice(text):

    if not client or not text:
        return None

    # Orpheus supports a maximum input length.
    text = text[:200]

    output_file = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".wav"
    )

    output_path = output_file.name
    output_file.close()

    response = client.audio.speech.create(
        model=TTS_MODEL,
        voice=TTS_VOICE,
        input=text,
        response_format="wav"
    )

    response.write_to_file(output_path)

    return output_path


# ============================================================
# PROCESS REQUEST
# ============================================================

def process_request(audio_path, manual_email=""):

    if not audio_path:
        return (
            "",
            "Please record your voice first.",
            None,
            "",
            list_appointments(),
            None
        )

    try:

        transcription = transcribe_audio(audio_path)

        if not transcription:
            return (
                "",
                "I could not understand the audio.",
                None,
                "",
                list_appointments(),
                None
            )

        data = understand_request(transcription)

        intent = data["intent"]

        if data.get("email") is None and manual_email:
            data["email"] = manual_email

        # ----------------------------------------------------
        # BOOK
        # ----------------------------------------------------

        if intent == "book":

            required = [
                data.get("name"),
                data.get("appointment_date"),
                data.get("appointment_time"),
                data.get("purpose"),
                data.get("email")
            ]

            if not all(required):

                missing = []

                if not data.get("name"):
                    missing.append("name")

                if not data.get("appointment_date"):
                    missing.append("date")

                if not data.get("appointment_time"):
                    missing.append("time")

                if not data.get("purpose"):
                    missing.append("purpose")

                if not data.get("email"):
                    missing.append("email")

                message = (
                    "I need the following information: "
                    + ", ".join(missing)
                )

                return (
                    transcription,
                    json.dumps(data, indent=2),
                    generate_voice(message),
                    message,
                    list_appointments(),
                    data
                )

            success, message = book_appointment(
                data["name"],
                data["appointment_date"],
                data["appointment_time"],
                data["purpose"],
                data["email"],
                data.get("reminder_minutes") or REMINDER_MINUTES
            )

            voice_message = short_booking_voice(data)

            return (
                transcription,
                json.dumps(data, indent=2),
                generate_voice(voice_message),
                message,
                list_appointments(),
                None
            )

        # ----------------------------------------------------
        # CANCEL
        # ----------------------------------------------------

        if intent == "cancel":

            appointment_id = data.get("appointment_id")

            if not appointment_id:
                message = "Please provide the appointment ID to cancel it."

                return (
                    transcription,
                    json.dumps(data, indent=2),
                    generate_voice(message),
                    message,
                    list_appointments(),
                    data
                )

            success, message = cancel_appointment(
                appointment_id
            )

            voice_message = short_cancel_voice(appointment_id)

            return (
                transcription,
                json.dumps(data, indent=2),
                generate_voice(voice_message),
                message,
                list_appointments(),
                None
            )

        # ----------------------------------------------------
        # RESCHEDULE
        # ----------------------------------------------------

        if intent == "reschedule":

            appointment_id = data.get("appointment_id")

            new_date = data.get("new_appointment_date")
            new_time = data.get("new_appointment_time")

            if not appointment_id:
                message = "Please provide the appointment ID."

                return (
                    transcription,
                    json.dumps(data, indent=2),
                    generate_voice(message),
                    message,
                    list_appointments(),
                    data
                )

            if not new_date or not new_time:
                message = "Please provide the new date and time."

                return (
                    transcription,
                    json.dumps(data, indent=2),
                    generate_voice(message),
                    message,
                    list_appointments(),
                    data
                )

            success, message = reschedule_appointment(
                appointment_id,
                new_date,
                new_time
            )

            voice_message = short_reschedule_voice(data)

            return (
                transcription,
                json.dumps(data, indent=2),
                generate_voice(voice_message),
                message,
                list_appointments(),
                None
            )

        # ----------------------------------------------------
        # LIST
        # ----------------------------------------------------

        if intent == "list":

            message = list_appointments()
            voice_message = short_list_voice()

            return (
                transcription,
                json.dumps(data, indent=2),
                generate_voice(voice_message),
                voice_message,
                message,
                None
            )

    except Exception as e:

        message = f"Error: {str(e)}"

        return (
            "",
            message,
            generate_voice(message),
            message,
            list_appointments(),
            None
        )


# ============================================================
# COMPLETE BOOKING AFTER EMAIL ENTRY
# ============================================================

def complete_booking_with_email(email, pending_data):

    if not pending_data:
        message = "There is no pending booking."

        return (
            message,
            generate_voice(message),
            list_appointments(),
            None
        )

    if not email:
        message = "Please enter an email address."

        return (
            message,
            generate_voice(message),
            list_appointments(),
            pending_data
        )

    try:
        data = json.loads(pending_data) if isinstance(
            pending_data, str
        ) else pending_data

        success, message = book_appointment(
            data["name"],
            data["appointment_date"],
            data["appointment_time"],
            data["purpose"],
            email,
            data.get("reminder_minutes") or REMINDER_MINUTES
        )

        return (
            message,
            generate_voice(message),
            list_appointments(),
            None if success else pending_data
        )

    except Exception as e:

        message = f"Booking error: {str(e)}"

        return (
            message,
            generate_voice(message),
            list_appointments(),
            pending_data
        )


# ============================================================
# CLEAR UI
# ============================================================

def clear_interface():

    return (
        None,
        "",
        "",
        "",
        None,
        "",
        list_appointments(),
        None
    )


# ============================================================
# GRADIO UI
# ============================================================

def build_ui():

    with gr.Blocks(
        title="Voice Appointment Chatbot"
    ) as demo:

        gr.Markdown("""
        # 🎙️ Voice Appointment Chatbot

        Manage appointments using voice:

        **Book • Cancel • Reschedule • List**

        The system uses Whisper for speech-to-text,
        GPT-OSS-20B for understanding,
        and Orpheus for voice responses.
        """)

        audio_input = gr.Audio(
            sources=["microphone"],
            type="filepath",
            label="🎤 Speak your appointment request"
        )

        process_button = gr.Button(
            "▶️ Process Voice",
            variant="primary"
        )

        clear_button = gr.Button(
            "🧹 Clear"
        )

        transcription_output = gr.Textbox(
            label="📝 Transcription"
        )

        ai_output = gr.Textbox(
            label="🤖 AI Understanding",
            lines=10
        )

        status_output = gr.Textbox(
            label="📌 Status",
            lines=4
        )

        voice_reply_output = gr.Audio(
            label="🔊 AI Voice Reply",
            type="filepath",
            autoplay=True
        )

        email_input = gr.Textbox(
            label="📧 Email Address",
            placeholder="Enter email if it was not spoken"
        )

        complete_booking_button = gr.Button(
            "✅ Complete Booking"
        )

        appointments_output = gr.Textbox(
            label="📅 Appointments",
            lines=10,
            value=list_appointments
        )

        pending_data = gr.State(None)

        process_button.click(
            fn=process_request,
            inputs=[
                audio_input,
                email_input
            ],
            outputs=[
                transcription_output,
                ai_output,
                voice_reply_output,
                status_output,
                appointments_output,
                pending_data
            ]
        )

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

    return demo


# ============================================================
# FASTAPI + CLOUD SCHEDULER
# ============================================================

demo = build_ui()

api_app = FastAPI(
    title="Voice Appointment Chatbot API"
)


@api_app.get("/health")
def health():
    return {
        "status": "healthy"
    }


@api_app.post("/reminders")
def reminders(
    x_reminder_key: str | None = Header(default=None)
):

    if REMINDER_WEBHOOK_SECRET:
        if x_reminder_key != REMINDER_WEBHOOK_SECRET:
            raise HTTPException(
                status_code=401,
                detail="Unauthorized"
            )

    sent = check_and_send_reminders()

    return {
        "status": "success",
        "reminders_sent": sent
    }


app = gr.mount_gradio_app(
    api_app,
    demo,
    path="/"
)


# ============================================================
# CLOUD RUN START
# ============================================================

if __name__ == "__main__":

    port = int(
        os.environ.get("PORT", "8080")
    )

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port
    )
