# Astra

## Services

- Open WebUI (port 3000 -> 8080)
- Piper TTS (port 5500)
- Sentiment Analyzer API (port 5501)
- Email Scheduler API (port 5502)

## Sentiment Analyzer API

This microservice wraps the `asset-sentiment-analyzer` Python package and exposes simple REST endpoints you can call from Open WebUI or any client.

**What it does:**
- 🔍 **Searches Google News** for recent articles about your asset
- 📰 **Fetches and reads actual article content** from news websites
- 🤖 **Uses GPT to analyze** the real news content (not speculation)
- 📊 **Generates sentiment verdicts** (bullish/bearish/neutral) based on analysis
- 📈 **Creates trend charts** showing sentiment over time

Base URL: `http://localhost:5501`

Endpoints:

- `GET /health` → `{ "ok": true }`

- `POST /v1/sentiment` → Returns sentiment label, news links, and article previews
  - Body:
    ```json
    { "asset": "Crude Oil", "date": "06-02-2024", "nlinks": 4 }
    ```
  - Response:
    ```json
    {
      "asset": "Crude Oil",
      "date": "06-02-2024",
      "sentiment": "bullish",
      "analysis_source": "Analyzed from Google News search results and article content",
      "links": ["https://..."],
      "news_previews": [
        {
          "url": "https://...",
          "preview": "Article excerpt..."
        }
      ],
      "links_analyzed": 4
    }
    ```

- `POST /v1/report` → Generates a GPT-powered daily report
  - Body:
    ```json
    { "asset": "AAPL", "date": "11-05-2025", "max_words": 200 }
    ```
  - Response:
    ```json
    {
      "asset": "AAPL",
      "date": "11-05-2025",
      "sentiment": "bullish",
      "report": "Detailed GPT analysis...",
      "analysis_source": "GPT analysis of Google News articles",
      "news_sources": ["https://..."],
      "sources_analyzed": 4
    }
    ```

- `POST /v1/trend-chart` → Generates a sentiment trend chart (PNG as base64)
  - Body:
    ```json
    { "asset": "Gold", "days": 7, "end_date": "11-05-2025" }
    ```
  - Response:
    ```json
    {
      "asset": "Gold",
      "days": 7,
      "date_range": {"start": "10-29-2025", "end": "11-05-2025"},
      "sentiments": [{"date": "...", "sentiment": "bullish"}],
      "chart": "data:image/png;base64,..."
    }
    ```### Environment

The service uses OpenAI-compatible providers. By default `docker-compose.yaml` wires it to DeepSeek:

- `OPENAI_API_KEY` → `${DEEPSEEK_API_KEY}`
- `OPENAI_API_BASE_URL` → `https://api.deepseek.com/v1`
- `OPENAI_MODEL` → optional override via `.env`

If you prefer OpenAI, set `OPENAI_API_KEY` and remove/override `OPENAI_API_BASE_URL`.

## Email Scheduler API

This microservice provides agentic email capabilities - send emails immediately or schedule them (one-time or recurring).

**What it does:**
- 📧 **Send emails immediately** via Gmail API
- 📊 **Send sentiment analysis emails** - fetches sentiment and emails in one call
- ⏰ **Schedule one-time emails** for a specific date/time
- 🔁 **Schedule recurring emails** (hourly, daily, weekly)
- 📋 **List scheduled jobs** to see what's queued
- ❌ **Cancel scheduled jobs** when needed

Base URL: `http://localhost:5502`

Endpoints:

- `GET /health` → `{ "ok": true, "scheduler_running": true }`

- `POST /v1/send` → Send an email immediately
  - Body:
    ```json
    {
      "to": "recipient@example.com",
      "subject": "Hello from Astra",
      "body": "This is a plain text email",
      "html": "<h1>Optional HTML version</h1>"
    }
    ```
  - Response:
    ```json
    {
      "status": "sent",
      "to": "recipient@example.com",
      "subject": "Hello from Astra",
      "timestamp": "2025-11-20T12:34:56.789"
    }
    ```

- `POST /v1/send-sentiment` → Fetch sentiment analysis and send via email (combined operation)
  - Body:
    ```json
    {
      "asset": "Cloudflare",
      "to": "user@example.com",
      "start_date": "2025-11-19",
      "end_date": "2025-11-20"
    }
    ```
    - `start_date` and `end_date` are optional (defaults to last 7 days)
  - Response:
    ```json
    {
      "status": "sent",
      "to": "user@example.com",
      "asset": "Cloudflare",
      "date_range": {"start": "2025-11-19", "end": "2025-11-20"},
      "articles_analyzed": 100,
      "message_id": "19aa0c03b064f6dd",
      "timestamp": "2025-11-20T10:12:26.254271",
      "preview": "Sentiment analysis preview..."
    }
    ```

- `POST /v1/schedule` → Schedule an email (one-time or recurring)
  - Body:
    ```json
    {
      "to": "recipient@example.com",
      "subject": "Scheduled Report",
      "body": "Your hourly update",
      "schedule_type": "hourly",
      "start_time": "2025-11-20T14:00:00"
    }
    ```
    - `schedule_type`: "once", "hourly", "daily", "weekly"
    - `start_time`: ISO format (optional, defaults to now)
  - Response:
    ```json
    {
      "id": "email_hourly_1700488800.123",
      "next_run_time": "2025-11-20T14:00:00",
      "trigger": "hourly"
    }
    ```

- `GET /v1/jobs` → List all scheduled email jobs
  - Response:
    ```json
    [
      {
        "id": "email_hourly_1700488800.123",
        "next_run_time": "2025-11-20T14:00:00",
        "trigger": "interval[1:00:00]"
      }
    ]
    ```

- `DELETE /v1/jobs/{job_id}` → Cancel a scheduled job
  - Response:
    ```json
    {
      "status": "cancelled",
      "job_id": "email_hourly_1700488800.123"
    }
    ```

### Gmail API Setup

The email service uses the **Gmail API** for reliable, OAuth2-authenticated email sending.

**One-time setup:**

1. **Create Google Cloud Project & Enable Gmail API:**
   - Go to https://console.cloud.google.com/
   - Create a new project
   - Navigate to "APIs & Services" > "Library"
   - Search for "Gmail API" and enable it

2. **Configure OAuth Consent Screen:**
   - Go to "APIs & Services" > "OAuth consent screen"
   - Select **"External"** user type
   - Fill in app name and contact emails
   - On **"Test users"** page, click **"+ ADD USERS"**
   - Add your Gmail address that will send emails
   - Click "Save and Continue"

3. **Create OAuth2 Credentials:**
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - Choose "Desktop app"
   - Download the JSON file

4. **Generate Access Token:**
   - Install: `pip install google-auth-oauthlib google-api-python-client`
   - Run OAuth flow with your downloaded credentials
   - You'll see "Google hasn't verified this app" - Click "Advanced" → "Go to [App] (unsafe)"
   - Grant permissions
   - Save the resulting credentials JSON

5. **Add to `.env`:**
   ```env
   GMAIL_CREDENTIALS='{"token":"...","refresh_token":"...","token_uri":"...","client_id":"...","client_secret":"...","scopes":["..."]}'
   ```

### Using with Open WebUI

**Setup:**

1. **Configure Gmail credentials** (see above)

2. **Rebuild and start:**
   ```powershell
   docker compose up -d --build
   ```

3. **Open Open WebUI** at http://localhost:3000

4. **Go to Workspace → Tools → Connections**

5. **Click "+ Add Connection"**

6. **Fill in the form:**
   - **Type:** OpenAPI
   - **API Base URL:** `http://email-scheduler:5502` (toggle ON)
   - **OpenAPI Spec URL:** `http://email-scheduler:5502/openapi.json`
   - **Auth:** None
   - **Name:** Email Scheduler

7. **Save and Enable**

**Usage examples:**
```
Send an email to john@example.com with subject "Meeting" and say "The meeting is at 3pm"

Send me a sentiment analysis email for Cloudflare from yesterday

Schedule a daily email to team@company.com about server status
```

The AI automatically uses the appropriate endpoint based on your request!

### Environment

## Using with Open WebUI (Sentiment Analyzer)

### ✅ OpenAPI Connection (Recommended)

The easiest way to integrate is using Open WebUI's OpenAPI Connection feature.

**Setup Steps:**

1. **Start your stack:**
   ```powershell
   docker compose up -d --build
   ```

2. **Open Open WebUI** at http://localhost:3000

3. **Go to Workspace → Tools → Connections**

4. **Click "+ Add Connection"**

5. **Fill in the form:**
   - **Type:** OpenAPI
   - **API Base URL:** `http://sentiment-analyzer:5501` (toggle ON)
   - **OpenAPI Spec URL:** `http://sentiment-analyzer:5501/openapi.json`
   - **Auth:** Bearer (leave ID field empty)
   - **Name:** Sentiment Analyzer
   - **Description:** Analyzes financial asset sentiment from real Google News

6. **Click Save** and make sure it's **enabled**

**That's it!** The LLM will automatically detect when to use sentiment analysis.

**Try in chat:**
```
What's the sentiment for Tesla stock today?
Give me a report on Crude Oil sentiment
Show me Bitcoin sentiment trend for last 7 days
```

### Method 2: HTTP Tool (Manual API Calls)

- In Open WebUI, go to Settings → Tools and add a tool that POSTs to `http://sentiment-analyzer:5501/v1/sentiment` with a JSON schema:
		 ```json
		 {
			 "name": "get_asset_sentiment",
			 "description": "Get daily news sentiment for an asset.",
			 "parameters": {
				 "type": "object",
				 "properties": {
					 "asset": {"type": "string"},
					 "date": {"type": "string", "description": "MM-dd-YYYY", "nullable": true},
					 "nlinks": {"type": "integer", "default": 4}
				 },
				 "required": ["asset"]
			 }
		 }
		 ```
	      }
     ```
   - The tool's HTTP request body should be the parameters as JSON; display the service response back in chat.

### Method 3: Direct API Calls (Advanced)

2) Use it manually from the chat by copying a curl snippet:
	 ```bash
	 curl -s http://localhost:5501/v1/sentiment \
		 -H "Content-Type: application/json" \
		 -d '{"asset":"Crude Oil","date":"06-02-2024"}'
	 ```

## Run

Place your API keys in a `.env` file next to `docker-compose.yaml`:

```
DEEPSEEK_API_KEY=sk-...
# optionally for model override:
# OPENAI_MODEL=deepseek-chat
```

Start the stack:

```powershell
docker compose up -d --build
```

Open WebUI: http://localhost:3000

Health check:

```powershell
curl http://localhost:5501/health
```