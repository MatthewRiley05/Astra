# Open WebUI Functions

This directory contains custom functions for Open WebUI that enable slash command interactions.

## Available Functions

### `sentiment_analyzer.py`

Provides two main functions for financial asset sentiment analysis:

1. **`get_asset_sentiment(asset, date?, nlinks?)`**
   - Quick sentiment verdict (bullish/bearish/neutral)
   - Returns news links
   - Example: `/sentiment asset="Crude Oil" date="11-05-2025"`

2. **`generate_sentiment_report(asset, date?, max_words?)`**
   - Detailed GPT-powered report
   - Comprehensive analysis with context
   - Example: `/report asset="AAPL" max_words=300`

## Installation

### Option A: Via Open WebUI UI

1. Start your Docker stack:
   ```powershell
   docker compose up -d --build
   ```

2. Open http://localhost:3000

3. Navigate to **Workspace → Functions** (or **Admin Panel → Functions**)

4. Click **"+ Add Function"** or **"Import Function"**

5. Copy the contents of `sentiment_analyzer.py` and paste into the editor

6. Click **Save** and **Enable** the function

7. The function is now available! Try:
   ```
   /sentiment asset="Gold"
   ```

### Option B: Via Volume Mount (Auto-load)

You can mount the functions directory directly into the Open WebUI container:

```yaml
# Add to open-webui service in docker-compose.yaml
volumes:
  - open-webui-data:/app/backend/data
  - ./open-webui-functions:/app/backend/data/functions:ro
```

Then restart:
```powershell
docker compose restart open-webui
```

## Usage Examples

### In Chat (Natural Language)

The LLM will automatically call these functions when relevant:

```
User: What's the current sentiment for Tesla stock?
→ Calls get_asset_sentiment(asset="TSLA")

User: Give me a detailed analysis of Crude Oil market today
→ Calls generate_sentiment_report(asset="Crude Oil")
```

### Slash Commands (Manual)

Explicitly invoke functions:

```
/sentiment asset="Bitcoin" nlinks=8
/sentiment asset="AAPL" date="11-05-2025"
/report asset="Gold" max_words=400
```

## Configuration

The function connects to your sentiment-analyzer microservice. Default configuration:

- **Service URL:** `http://sentiment-analyzer:5501`
- **Timeout:** 60s for sentiment, 120s for reports

To change the service URL, edit the `Valves` class in the function:

```python
class Valves(BaseModel):
    SENTIMENT_API_BASE_URL: str = Field(
        default="http://sentiment-analyzer:5501",  # Change this
        description="Base URL for sentiment service"
    )
```

## Requirements

- Open WebUI running in Docker
- `sentiment-analyzer` service running (port 5501)
- Valid `OPENAI_API_KEY` or `DEEPSEEK_API_KEY` set in environment

## Troubleshooting

**"Error calling sentiment API"**
- Check that `sentiment-analyzer` service is running: `docker ps`
- Verify connectivity: `docker exec -it open-webui curl http://sentiment-analyzer:5501/health`

**Function not appearing**
- Refresh the page
- Check that the function is **enabled** in settings
- Verify no syntax errors in the function code

**Timeout errors**
- Reports can take 30-60s to generate (GPT inference + web scraping)
- Increase timeout in the function if needed
- Check API rate limits on your OpenAI/DeepSeek account
