# Astra

## Services

- Open WebUI (port 3000 -> 8080)
- Piper TTS (port 5500)
- Sentiment Analyzer API (port 5501)

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

## Using with Open WebUI

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