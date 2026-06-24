# AI Placement Agent using Zapier + Gemini

A web-based placement recommendation system that automates career guidance for students using **Google Forms → Google Sheets → Zapier → Gemini AI → Gmail**.

---

## 🚀 Quick Start

### 1. Clone / unzip the project

```bash
unzip placement-agent.zip
cd placement-agent
```

### 2. Create a virtual environment & install dependencies

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and fill in your real values:

| Variable | Where to get it |
|---|---|
| `GEMINI_API_KEY` | [Google AI Studio](https://aistudio.google.com/app/apikey) |
| `GMAIL_SENDER` | Your Gmail address |
| `GMAIL_APP_PASSWORD` | [Generate a Gmail App Password](https://support.google.com/accounts/answer/185833) — do NOT use your real password |
| `FLASK_SECRET_KEY` | Any long random string |

### 4. Run locally

```bash
python app.py
```

Open [http://localhost:5000](http://localhost:5000) in your browser.

---

## 🏗️ Project Structure

```
placement-agent/
├── app.py              ← Flask application (routes, Gemini, email)
├── requirements.txt    ← Python dependencies
├── .env.example        ← Environment variable template
├── templates/
│   └── index.html      ← Dashboard HTML (Jinja2 template)
├── static/
│   ├── style.css       ← Responsive stylesheet
│   └── script.js       ← Frontend JavaScript
└── README.md           ← This file
```

---

## ⚡ Zapier Integration

### Full workflow

```
Google Form → Google Sheets → Zapier → Flask webhook → Gemini AI → Gmail → Student
```

### Step-by-step

1. **Create a Google Form** with fields:
   - Full Name
   - Email Address
   - Skills (paragraph)
   - Preferred Domain (multiple choice)
   - Graduation Year

2. **Link to Google Sheets**: Form → Responses → click the green Sheets icon.

3. **Zapier → New Zap**
   - **Trigger**: Google Sheets → *New Spreadsheet Row*
   - **Action**: Webhooks by Zapier → *POST*
     - URL: `https://your-app.replit.app/api/zapier-webhook`
     - Payload type: `json`
     - Data mapping:
       ```
       name            → (column) Full Name
       email           → (column) Email Address
       skills          → (column) Skills
       domain          → (column) Preferred Domain
       graduation_year → (column) Graduation Year
       ```

4. **Test** with a real form submission, then **turn the Zap ON**.

---

## 🔗 API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/submit` | Submit student data, get recommendations |
| `GET` | `/api/submissions` | List all submissions |
| `POST` | `/api/zapier-webhook` | Zapier webhook (same body as `/submit`) |
| `GET` | `/api/health` | Health check |

### Example — manual submission

```bash
curl -X POST http://localhost:5000/api/submit \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Priya Sharma",
    "email": "priya@example.com",
    "skills": "Python, Machine Learning, SQL",
    "domain": "Data Science & Analytics",
    "graduation_year": "2025"
  }'
```

---

## 🤖 Gemini Prompt Template

The prompt sent to Gemini:

```
Analyze the following student profile:

Name: {name}
Skills: {skills}
Domain: {domain}
Graduation Year: {graduation_year}

Provide:
1. Top 3 suitable job roles
2. Career recommendation
3. Skills to improve
4. Learning roadmap
5. Placement readiness score out of 100
```

---

## ☁️ Deployment on Replit

1. Create a new **Python** Repl and upload the project files.
2. In **Secrets** (the lock icon), add `GEMINI_API_KEY`, `GMAIL_SENDER`, `GMAIL_APP_PASSWORD`, `FLASK_SECRET_KEY`.
3. In `pyproject.toml` or the Replit run command, set:
   ```
   python app.py
   ```
4. Your app will be live at `https://<your-repl>.replit.app`.
5. Use that URL in the Zapier webhook action.

---

## 📋 Requirements

```
flask==3.1.0
python-dotenv==1.0.1
requests==2.32.3
gunicorn==22.0.0
```

---

## 🔒 Security Notes

- Never commit `.env` to version control — it is already in `.gitignore`.
- Use a **Gmail App Password**, not your real Gmail password.
- Rotate `FLASK_SECRET_KEY` before deploying to production.
- For production, add rate limiting and input sanitisation.

---

## 📄 License

MIT — free to use, modify, and distribute.
