"""
AI Placement Agent - Flask Application
Integrates Google Forms, Sheets, Zapier, Gemini AI, and Gmail
to deliver personalized career recommendations to students.
"""

import os
import json
import smtplib
import logging
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import requests
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "change-me-in-production")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# In-memory store (replace with a database for production)
submissions = []

# ---------------------------------------------------------------------------
# Gemini helpers
# ---------------------------------------------------------------------------

GEMINI_API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-1.5-flash:generateContent"
)

GEMINI_PROMPT_TEMPLATE = """
Analyze the following student profile and provide detailed career guidance:

Name: {name}
Skills: {skills}
Preferred Domain: {domain}
Graduation Year: {graduation_year}

Please provide a structured response with the following sections:

1. TOP 3 SUITABLE JOB ROLES
   - List three specific job titles that match the student's profile
   - Include a brief reason for each

2. CAREER RECOMMENDATION
   - A personalized career path recommendation (2-3 sentences)

3. SKILLS TO IMPROVE
   - List 5 specific technical or soft skills the student should develop

4. LEARNING ROADMAP
   - A step-by-step 6-month learning plan with clear milestones

5. PLACEMENT READINESS SCORE
   - Score: X/100
   - Brief justification for the score

Format the response in a clear, professional, and encouraging manner suitable
for a student email.
"""


def call_gemini(name: str, skills: str, domain: str, graduation_year: str) -> str:
    """
    Send student data to Gemini AI and return the generated recommendations.
    Raises RuntimeError if the API call fails or the key is missing.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Add it to your .env file."
        )

    prompt = GEMINI_PROMPT_TEMPLATE.format(
        name=name,
        skills=skills,
        domain=domain,
        graduation_year=graduation_year,
    )

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 1500,
        },
    }

    response = requests.post(
        f"{GEMINI_API_URL}?key={api_key}",
        json=payload,
        timeout=30,
    )
    response.raise_for_status()

    data = response.json()
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError) as exc:
        logger.error("Unexpected Gemini response structure: %s", data)
        raise RuntimeError("Could not parse Gemini response.") from exc


# ---------------------------------------------------------------------------
# Email helpers
# ---------------------------------------------------------------------------

EMAIL_TEMPLATE = """\
Dear {name},

Thank you for registering with the AI Placement Agent. Based on your profile,
here are your personalized career recommendations:

---

{recommendations}

---

We wish you the very best in your career journey!

Warm regards,
AI Placement Agent Team

---
This email was generated automatically. Please do not reply directly.
"""


def send_email(recipient: str, name: str, recommendations: str) -> bool:
    """
    Send the career recommendations email via Gmail SMTP.
    Returns True on success, False on failure.
    """
    sender = os.getenv("GMAIL_SENDER")
    password = os.getenv("GMAIL_APP_PASSWORD")

    if not sender or not password:
        logger.warning(
            "Gmail credentials not configured — email will not be sent."
        )
        return False

    body = EMAIL_TEMPLATE.format(name=name, recommendations=recommendations)

    message = MIMEMultipart("alternative")
    message["Subject"] = f"Your AI Career Recommendations — {name}"
    message["From"] = sender
    message["To"] = recipient
    message.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender, password)
            server.sendmail(sender, recipient, message.as_string())
        logger.info("Email sent to %s", recipient)
        return True
    except smtplib.SMTPException as exc:
        logger.error("Failed to send email: %s", exc)
        return False


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    """Render the main dashboard."""
    return render_template("index.html")


@app.route("/api/submit", methods=["POST"])
def submit():
    """
    Accept a student form submission, call Gemini, optionally send an email,
    and return the recommendations as JSON.

    Expected JSON body:
        name, email, skills, domain, graduation_year
    """
    data = request.get_json(force=True)

    # Validate required fields
    required = ["name", "email", "skills", "domain", "graduation_year"]
    missing = [field for field in required if not data.get(field, "").strip()]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

    name = data["name"].strip()
    email = data["email"].strip()
    skills = data["skills"].strip()
    domain = data["domain"].strip()
    graduation_year = data["graduation_year"].strip()

    # --- Gemini AI call ---
    try:
        recommendations = call_gemini(name, skills, domain, graduation_year)
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 500
    except requests.RequestException as exc:
        logger.error("Gemini API request failed: %s", exc)
        return jsonify({"error": "Gemini API call failed. Check your API key and network."}), 502

    # --- Email ---
    email_sent = send_email(email, name, recommendations)

    # --- Persist in memory ---
    record = {
        "id": len(submissions) + 1,
        "name": name,
        "email": email,
        "skills": skills,
        "domain": domain,
        "graduation_year": graduation_year,
        "recommendations": recommendations,
        "email_sent": email_sent,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    submissions.append(record)

    return jsonify({
        "success": True,
        "message": "Analysis complete!",
        "recommendations": recommendations,
        "email_sent": email_sent,
        "record_id": record["id"],
    })


@app.route("/api/submissions", methods=["GET"])
def get_submissions():
    """Return all stored submissions (most recent first)."""
    return jsonify(list(reversed(submissions)))


@app.route("/api/zapier-webhook", methods=["POST"])
def zapier_webhook():
    """
    Zapier webhook endpoint.

    Zapier sends a POST request here when a new row is added to Google Sheets.
    Expected JSON body:
        name, email, skills, domain, graduation_year
    """
    data = request.get_json(force=True)
    logger.info("Zapier webhook received: %s", json.dumps(data, indent=2))

    # Reuse the same submit logic
    name = data.get("name", "").strip()
    email = data.get("email", "").strip()
    skills = data.get("skills", "").strip()
    domain = data.get("domain", "").strip()
    graduation_year = data.get("graduation_year", "").strip()

    if not all([name, email, skills, domain, graduation_year]):
        return jsonify({"error": "Incomplete data from Zapier."}), 400

    try:
        recommendations = call_gemini(name, skills, domain, graduation_year)
    except (RuntimeError, requests.RequestException) as exc:
        logger.error("Gemini call failed in webhook: %s", exc)
        return jsonify({"error": str(exc)}), 500

    email_sent = send_email(email, name, recommendations)

    record = {
        "id": len(submissions) + 1,
        "name": name,
        "email": email,
        "skills": skills,
        "domain": domain,
        "graduation_year": graduation_year,
        "recommendations": recommendations,
        "email_sent": email_sent,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "source": "zapier",
    }
    submissions.append(record)

    return jsonify({
        "success": True,
        "message": f"Processed and emailed {name}.",
        "email_sent": email_sent,
    })


@app.route("/api/health", methods=["GET"])
def health():
    """Simple health-check endpoint."""
    return jsonify({"status": "ok", "submissions": len(submissions)})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_ENV", "production") == "development"
    app.run(host="0.0.0.0", port=port, debug=debug)
