# Astra

## Services

- Open WebUI (port 3000 -> 8080)
- Piper TTS (port 5500)
- Sentiment Analyzer API (port 5501)

## Sentiment Analyzer API

This microservice wraps the `asset-sentiment-analyzer` Python package and exposes simple REST endpoints you can call from Open WebUI or any client.

Base URL: `http://localhost:5501`

Endpoints:

- `GET /health` → `{ "ok": true }`
- `POST /v1/sentiment` → Returns sentiment label and news links
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
			"links": ["https://..."]
		}
		```
- `POST /v1/report` → Generates a GPT-powered daily report (and sentiment)
	- Body:
		```json
		{ "asset": "AAPL", "date": "11-05-2025", "max_words": 200 }
		```

### Environment

The service uses OpenAI-compatible providers. By default `docker-compose.yaml` wires it to DeepSeek:

- `OPENAI_API_KEY` → `${DEEPSEEK_API_KEY}`
- `OPENAI_API_BASE_URL` → `https://api.deepseek.com/v1`
- `OPENAI_MODEL` → optional override via `.env`

If you prefer OpenAI, set `OPENAI_API_KEY` and remove/override `OPENAI_API_BASE_URL`.

## Using with Open WebUI

### Method 1: Install as a Function (Recommended - Slash Commands!)

Open WebUI supports custom **Functions** that can be triggered via slash commands (e.g., `/sentiment`) or automatically by the LLM when relevant.

**Installation Steps:**

1. **Start your stack:**
   ```powershell
   docker compose up -d --build
   ```

2. **Open Open WebUI** at http://localhost:3000

3. **Go to Workspace → Functions** (or Admin Panel → Functions)

4. **Click "+ Add Function"** or "Import Function"

5. **Upload the function file:**
   - Navigate to `open-webui-functions/sentiment_analyzer.py` in your project
   - Copy the entire contents and paste into the function editor
   - Or drag-and-drop the file

6. **Enable the function** for your workspace/users

**Usage in Chat:**

Once installed, users can:

- **Slash command (manual):**
  ```
  /sentiment asset="Crude Oil" date="11-05-2025"
  /sentiment asset="AAPL"
  ```

- **Or just ask naturally:**
  ```
  What's the sentiment for Crude Oil today?
  Generate a report for Apple stock on November 5th
  ```
  The LLM will automatically call `get_asset_sentiment()` or `generate_sentiment_report()` based on context!

**Available Functions:**
- `get_asset_sentiment(asset, date?, nlinks?)` - Quick sentiment verdict + news links
- `generate_sentiment_report(asset, date?, max_words?)` - Detailed GPT report

### Method 2: HTTP Tool (Manual API Calls)

If you prefer to configure an HTTP tool webhook:

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