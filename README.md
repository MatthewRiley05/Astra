# Astra - AI-Powered Financial Analysis Chatbot

## Group Members

|Student ID |          Name          |
|-----------|------------------------|
| 23102891D | Matthew Riley Raymundo |
| 22096687D | Jonah Chua             |
| 22096321D | Dominique Pesengco     |

---

## Project Overview

Astra is an AI-powered financial analysis chatbot built using Open WebUI with a microservices architecture. The system provides comprehensive financial market analysis, sentiment tracking, portfolio optimization, and automated reporting capabilities through an intelligent conversational interface.

### AI Personality & Capabilities

ASTRA (AI Stock Trading & Research Assistant) is specifically designed as a finance-focused AI assistant with the following characteristics:

- **Finance-Only Scope**: Only answers questions about finance, economics, markets, and portfolio analysis
- **U.S. Stock Market Focus**: Individual stock data and portfolio optimization limited to U.S.-listed equities (NYSE, NASDAQ, AMEX)
- **Global Market Commentary**: Can discuss macro topics for any country, including global markets, FX, crypto, commodities, and indices
- **Tool-First Approach**: Prioritizes internal tools and APIs over web search and code interpretation
- **Data Validation**: Cross-references multiple sources and explicitly notes data limitations
- **Educational Focus**: Provides general educational information, not personalized financial advice

---

## Additional Features Implemented

Beyond the basic chatbot functionality, we have implemented the following advanced features:

### 1. **Market Data & Portfolio Optimization Service** (Port 5003)
- **Stock Screening**: Predefined screening strategies for aggressive growth, dividend stocks, small caps, etc.
- **Portfolio Optimization**: Modern Portfolio Theory (MPT) implementation with multiple optimization methods:
  - Maximum Sharpe Ratio
  - Minimum Volatility
  - Maximum Quadratic Utility
  - Efficient Risk/Return optimization
- **Performance Analytics**: 
  - Portfolio vs S&P 500 benchmark comparison
  - Efficient frontier visualization
  - Risk metrics (volatility, drawdown, Sharpe ratio)
- **Industry Filtering**: Filter stocks by SIC (Standard Industrial Classification) codes
- **Real-time Market Data**: Historical price data, OHLCV data, company fundamentals

### 2. **Sentiment Analysis Service** (Port 5501)
- **Real-time News Analysis**: Fetches and analyzes actual news articles from Google News
- **GPT-Powered Sentiment**: Uses AI to determine bullish/bearish/neutral sentiment
- **Trend Visualization**: Generates sentiment trend charts over customizable time periods
- **Comprehensive Reports**: AI-generated daily sentiment reports with source citations
- **Multi-asset Support**: Analyze stocks, commodities, cryptocurrencies, and more

### 3. **Email Automation & Scheduling** (Port 5502)
- **Immediate Email Sending**: Gmail API integration for reliable email delivery
- **Scheduled Emails**: Support for one-time and recurring email schedules (hourly, daily, weekly)
- **Sentiment Email Integration**: Combined sentiment analysis + email delivery in one operation
- **Job Management**: List, schedule, and cancel email jobs through the API
- **OAuth2 Authentication**: Secure Gmail API access using OAuth2 credentials

### 4. **Financial Data Service** (Port 5503)
- **SEC Edgar Integration**: Retrieves official company filings from SEC database
- **Financial Statements**: Access to company financial data, ratios, and metrics
- **Historical Financial Analysis**: Multi-period company performance tracking
- **Chart Generation**: Visual representations of financial trends

### 5. **Text-to-Speech Service** (Port 5500)
- **Piper TTS Integration**: High-quality neural text-to-speech
- **Multi-voice Support**: Multiple voice options for different use cases
- **Real-time Synthesis**: On-demand audio generation for chatbot responses

---

## System Architecture

Astra consists of six microservices orchestrated through Docker Compose:

| Service | Port | Description |
|---------|------|-------------|
| **Open WebUI** | 3000 | Main chatbot interface powered by DeepSeek LLM |
| **Piper TTS** | 5500 | Text-to-speech service for voice responses |
| **Sentiment Analyzer** | 5501 | News sentiment analysis using Google News + GPT |
| **Email Scheduler** | 5502 | Automated email sending and scheduling |
| **Financial Data** | 5503 | SEC Edgar financial data retrieval |
| **Market Data** | 5003 | Stock screening and portfolio optimization |

---

## How to Run the Source Code

### Prerequisites

1. **Docker Desktop** - Download and install from [https://www.docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop)
2. **API Keys**:
   - DeepSeek API key (for LLM): Get from [https://platform.deepseek.com/](https://platform.deepseek.com/)
   - Gmail API credentials (for email service): See Gmail API Setup section below
3. **PowerShell** or **Command Prompt** (Windows) / **Terminal** (macOS/Linux)

### Installation & Setup

#### Step 1: Clone/Extract the Project

```powershell
# If cloning from repository
git clone <repository-url>
cd Astra

# If extracting from zip file
# Extract the zip file and navigate to the Astra directory
cd path/to/Astra
```

#### Step 2: Configure Environment Variables

Create a `.env` file in the project root directory with the following content:

```env
# Required: DeepSeek API Key
DEEPSEEK_API_KEY=sk-your-deepseek-api-key-here

# Required for Email Service: Gmail API Credentials (see Gmail Setup section)
GMAIL_CREDENTIALS='{"token":"...","refresh_token":"...","token_uri":"...","client_id":"...","client_secret":"...","scopes":["..."]}'

# Optional: Model override
# OPENAI_MODEL=deepseek-chat
```

#### Step 3: Start All Services

```powershell
# Build and start all services in detached mode
docker compose up -d --build
```

This command will:
- Build Docker images for all services
- Download required dependencies
- Start all containers in the background
- Set up networking between services

#### Step 4: Verify Services are Running

```powershell
# Check container status
docker compose ps

# Check individual service health
curl http://localhost:3000/health   # Open WebUI
curl http://localhost:5500/health   # TTS Service
curl http://localhost:5501/health   # Sentiment Analyzer
curl http://localhost:5502/health   # Email Scheduler
curl http://localhost:5503/health   # Financial Data
curl http://localhost:5003/health   # Market Data
```

#### Step 5: Access the Chatbot

1. Open your web browser
2. Navigate to: **http://localhost:3000**
3. Create an account or sign in
4. Start chatting with Astra!

### Connecting Services to Open WebUI

After starting the services, you need to connect them to Open WebUI so the chatbot can use them:

#### Configure Market Data Connection

1. In Open WebUI, go to **Workspace → Tools → Connections**
2. Click **"+ Add Connection"**
3. Fill in:
   - **Type**: OpenAPI
   - **API Base URL**: `http://market-data:5003` (toggle ON)
   - **OpenAPI Spec URL**: `http://market-data:5003/openapi.json`
   - **Auth**: None
   - **Name**: Market Data & Portfolio API
4. **Save and Enable**

#### Configure Sentiment Analyzer Connection

1. Click **"+ Add Connection"** again
2. Fill in:
   - **Type**: OpenAPI
   - **API Base URL**: `http://sentiment-analyzer:5501` (toggle ON)
   - **OpenAPI Spec URL**: `http://sentiment-analyzer:5501/openapi.json`
   - **Auth**: Bearer (leave ID field empty)
   - **Name**: Sentiment Analyzer
3. **Save and Enable**

#### Configure Email Scheduler Connection

1. Click **"+ Add Connection"** again
2. Fill in:
   - **Type**: OpenAPI
   - **API Base URL**: `http://email-scheduler:5502` (toggle ON)
   - **OpenAPI Spec URL**: `http://email-scheduler:5502/openapi.json`
   - **Auth**: None
   - **Name**: Email Scheduler
4. **Save and Enable**

#### Configure Financial Data Connection

1. Click **"+ Add Connection"** again
2. Fill in:
   - **Type**: OpenAPI
   - **API Base URL**: `http://financial-data:5503` (toggle ON)
   - **OpenAPI Spec URL**: `http://financial-data:5503/openapi.json`
   - **Auth**: None
   - **Name**: Financial Data API
3. **Save and Enable**

### Stopping the Services

```powershell
# Stop all services
docker compose down

# Stop and remove all data volumes (WARNING: This deletes all data)
docker compose down -v
```

---

## Gmail API Setup (Required for Email Service)

The email service uses the Gmail API for reliable, OAuth2-authenticated email sending.

### One-Time Setup

#### 1. Create Google Cloud Project & Enable Gmail API

1. Go to [https://console.cloud.google.com/](https://console.cloud.google.com/)
2. Create a new project
3. Navigate to "APIs & Services" > "Library"
4. Search for "Gmail API" and enable it

#### 2. Configure OAuth Consent Screen

1. Go to "APIs & Services" > "OAuth consent screen"
2. Select **"External"** user type
3. Fill in app name and contact emails
4. On **"Test users"** page, click **"+ ADD USERS"**
5. Add your Gmail address that will send emails
6. Click "Save and Continue"

#### 3. Create OAuth2 Credentials

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth client ID"
3. Choose "Desktop app"
4. Download the JSON file

#### 4. Generate Access Token

1. Install required packages:
   ```powershell
   pip install google-auth-oauthlib google-api-python-client
   ```

2. Run OAuth flow with your downloaded credentials
3. You'll see "Google hasn't verified this app" - Click "Advanced" → "Go to [App] (unsafe)"
4. Grant permissions
5. Save the resulting credentials JSON

#### 5. Add to `.env`

Copy the generated credentials JSON and add it to your `.env` file:

```env
GMAIL_CREDENTIALS='{"token":"...","refresh_token":"...","token_uri":"...","client_id":"...","client_secret":"...","scopes":["..."]}'
```

---

## Usage Examples

### Portfolio Optimization

```
Create an optimized portfolio from aggressive small cap stocks with $10,000 investment over 1 year time horizon
```

### Sentiment Analysis

```
What's the sentiment for Tesla stock today?
Give me a 7-day sentiment trend for Bitcoin
```

### Email Automation

```
Send me a sentiment analysis email for Apple stock from last week
Schedule a daily email to john@example.com with portfolio updates
```

### Financial Data

```
Get the latest financial statements for Microsoft
Show me Apple's revenue trends over the past 5 years
```

---

## Services

---

## Detailed API Documentation

### Market Data & Portfolio Optimization API (Port 5003)

**Base URL:** `http://localhost:5003`

#### Available Endpoints

- **GET** `/health` - Health check
- **GET** `/openapi.json` - OpenAPI specification
- **POST** `/api/screen/predefined` - Screen stocks by predefined criteria
- **GET** `/api/screen/available` - List available screening queries
- **POST** `/api/market/closing-prices` - Get historical closing prices
- **POST** `/api/market/ticker-info` - Get detailed stock information
- **POST** `/api/stocks/by-sic` - Filter stocks by industry (SIC codes)
- **GET** `/api/stocks/sic-list` - Get all available SIC codes
- **POST** `/api/portfolio/optimize` - Optimize portfolio allocation
- **POST** `/api/portfolio/plot-returns` - Generate portfolio performance chart
- **POST** `/api/portfolio/efficient-frontier` - Generate efficient frontier data

#### Key Features

- Modern Portfolio Theory (MPT) optimization
- Multiple optimization methods (max Sharpe, min volatility, etc.)
- Real-time market data from Yahoo Finance
- Portfolio performance visualization
- Industry-based stock filtering
- Risk-return analysis

---

### Sentiment Analyzer API (Port 5501)

**Base URL:** `http://localhost:5501`

This microservice wraps the `asset-sentiment-analyzer` Python package and exposes REST endpoints for real-time sentiment analysis.

**What it does:**
- 🔍 **Searches Google News** for recent articles about your asset
- 📰 **Fetches and reads actual article content** from news websites
- 🤖 **Uses GPT to analyze** the real news content (not speculation)
- 📊 **Generates sentiment verdicts** (bullish/bearish/neutral) based on analysis
- 📈 **Creates trend charts** showing sentiment over time

#### Endpoints

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
    ```

#### Environment Configuration

The service uses OpenAI-compatible providers. By default `docker-compose.yaml` wires it to DeepSeek:

- `OPENAI_API_KEY` → `${DEEPSEEK_API_KEY}`
- `OPENAI_API_BASE_URL` → `https://api.deepseek.com/v1`
- `OPENAI_MODEL` → optional override via `.env`

If you prefer OpenAI, set `OPENAI_API_KEY` and remove/override `OPENAI_API_BASE_URL`.

---

### Email Scheduler API (Port 5502)

**Base URL:** `http://localhost:5502`

This microservice provides agentic email capabilities - send emails immediately or schedule them (one-time or recurring).

**What it does:**
- 📧 **Send emails immediately** via Gmail API
- 📊 **Send sentiment analysis emails** - fetches sentiment and emails in one call
- ⏰ **Schedule one-time emails** for a specific date/time
- 🔁 **Schedule recurring emails** (hourly, daily, weekly)
- 📋 **List scheduled jobs** to see what's queued
- ❌ **Cancel scheduled jobs** when needed

#### Endpoints

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

    }
    ```

---

## Troubleshooting

### Common Issues

#### Services won't start
```powershell
# Check Docker Desktop is running
# Restart Docker Desktop
# Rebuild containers
docker compose down
docker compose up -d --build
```

#### Can't access Open WebUI (Port 3000)
```powershell
# Check if port 3000 is already in use
# On Windows:
netstat -ano | findstr :3000

# On Mac/Linux:
lsof -i :3000

# Kill the process or change the port in docker-compose.yaml
```

#### Email service not working
- Verify Gmail credentials are correctly set in `.env`
- Check that you've added your email as a test user in Google Cloud Console
- Ensure the OAuth token hasn't expired (regenerate if needed)

#### Sentiment analysis returns errors
- Verify DeepSeek API key is valid in `.env`
- Check internet connectivity for Google News access
- Verify the service is running: `curl http://localhost:5501/health`

#### Portfolio optimization fails
- Ensure stock tickers are valid and not delisted
- Check that period and holding_period parameters are in correct format
- Verify at least 2 stocks are provided for optimization

### Viewing Logs

```powershell
# View logs for all services
docker compose logs

# View logs for specific service
docker compose logs open-webui
docker compose logs sentiment-analyzer
docker compose logs email-scheduler
docker compose logs market-data
docker compose logs financial-data

# Follow logs in real-time
docker compose logs -f
```

### Restarting Individual Services

```powershell
# Restart a specific service
docker compose restart open-webui
docker compose restart sentiment-analyzer
docker compose restart email-scheduler
```

---

## Technology Stack

- **Frontend/UI**: Open WebUI (Web-based chat interface)
- **LLM**: DeepSeek AI (via OpenAI-compatible API)
- **Backend Services**: 
  - Flask (Market Data, Sentiment Analyzer)
  - FastAPI (Financial Data, Email Scheduler)
  - Python 3.11+
- **Container Orchestration**: Docker Compose
- **Data Sources**:
  - Yahoo Finance (Market data)
  - Google News (Sentiment analysis)
  - SEC Edgar (Financial statements)
  - US Treasury (Risk-free rates)
- **Email**: Gmail API with OAuth2
- **TTS**: Piper neural text-to-speech

---

## Project Structure

```
Astra/
├── docker-compose.yaml          # Service orchestration
├── .env                          # Environment variables (API keys)
├── README.md                     # This file
├── LICENSE                       # Project license
│
├── email/                        # Email Scheduler Service
│   ├── app.py                    # Flask application
│   ├── dockerfile                # Container definition
│   └── requirements.txt          # Python dependencies
│
├── finance/                      # Financial Data Service
│   ├── app.py                    # FastAPI application
│   ├── EdgarRetriever.py         # SEC Edgar data retrieval
│   ├── possible_tags.txt         # Available financial tags
│   ├── dockerfile                # Container definition
│   └── requirements.txt          # Python dependencies
│
├── market_data/                  # Market Data & Portfolio Service
│   ├── app.py                    # Flask application
│   ├── PortfolioBuilder.py       # Portfolio construction utilities
│   ├── pyportfolio.py            # Portfolio optimization engine
│   ├── company_tickers_with_sic.json  # Stock ticker database
│   ├── dockerfile                # Container definition
│   └── requirements.txt          # Python dependencies
│
├── sentiment/                    # Sentiment Analyzer Service
│   ├── app.py                    # Flask application
│   ├── dockerfile                # Container definition
│   └── requirements.txt          # Python dependencies
│
└── tts/                          # Text-to-Speech Service
    ├── app.py                    # Flask application
    ├── dockerfile                # Container definition
    └── requirements.txt          # Python dependencies
```

---

## ASTRA System Prompt

Below is the complete system prompt that defines ASTRA's behavior and capabilities. This prompt is configured in Open WebUI to guide the AI's responses.

### Identity & Scope

```
You are ASTRA, an AI finance assistant running inside OpenWebUI.

CORE IDENTITY & SCOPE
- You ONLY answer questions about finance, economics, markets, or portfolio analysis.
- You may answer macro questions about any country, and general questions about global markets, 
  FX, crypto, commodities, and indices.
- For INDIVIDUAL STOCKS and equity screening/optimization, you can ONLY retrieve and work with 
  U.S.-listed stocks (e.g., NYSE, NASDAQ, AMEX). You do NOT have coverage of non-U.S.-listed equities.
- If a question is not clearly finance-related, politely refuse and ask the user to rephrase 
  in a finance context.
- You may answer finance-related programming/data questions (e.g., computing Sharpe ratio in Python).

NON-US STOCK LIMITATION
- If the user asks for data, screening, or portfolio optimization involving a non-U.S.-listed stock:
  - Clearly say that your stock universe is limited to U.S.-listed equities.
  - Do NOT fabricate prices, tickers, or fundamentals for non-U.S. stocks.
  - You may still give high-level, conceptual commentary (e.g., about the company's business 
    model or industry) if you can, but explicitly note that you do not have live or historical 
    market data for that listing.

DATA & TOOL PRIORITY (VERY IMPORTANT)
When answering finance questions, you MUST prioritize data and tools in this order:
1) Local / internal tools and data:
   - Market Data & Portfolio API (port 5003)
   - Finance Data (call on EDGAR functions to get financial statements such as balance 
     sheet/income statement/cashflow)
   - RAG / vector database (internal docs, saved research)
   - Sentiment analysis docker
   - Any internal email or scheduling tools
2) Web search:
   - Only when local tools and RAG do not provide the required information or context.
3) Local code interpreter / Python:
   - ONLY for calculations, transformations, or plotting on data you already have.
   - NEVER use the code interpreter to fetch prices, fundamentals, or live market data that 
     should come from the Market Data & Portfolio API or other local tools.
   - NEVER use it as a substitute for the provided finance tools if those tools can handle 
     the task.

If both a local tool and web search can answer a question, you MUST prefer the local tool, 
and then optionally cross-check with web search if needed.

TRUTHFULNESS & CHECKING
- For anything involving real-world data (prices, company-specific info, news, macro data):
  - FIRST use the Market Data & Portfolio API and other local tools that apply.
  - Use RAG for internal reports, notes, and saved documents.
  - Use web search only when local tools and RAG are insufficient for context (e.g., latest 
    news, macro events, filings).
  - If sources disagree or data is limited, say so explicitly. Do NOT invent numbers.
- For conceptual questions, you may use your own knowledge, but still use RAG/web if recency 
  or policy changes matter.
- Always mention the data period and source (API vs web vs RAG) for time-sensitive info.

MARKET DATA & PORTFOLIO API (PORT 5003) – HIGH-LEVEL BEHAVIOR
You have an internal API which works on a universe of U.S.-listed stocks. It can:
- Screen U.S.-listed stocks with predefined screeners and list available screener names.
- Get historical closing prices and ticker info (OHLCV, metadata, key stats) for U.S.-listed stocks.
- Filter U.S.-listed stocks by SIC codes and list available SIC codes/descriptions.
- Optimize portfolios of U.S.-listed stocks (Modern Portfolio Theory) with methods like max_sharpe, 
  min_volatility, etc., returning:
  - Expected return, volatility, Sharpe ratio, optimal weights, risk-free rate, and (optionally) 
    dollar allocations.
- Generate efficient frontier simulations and identify an optimal portfolio on the frontier.
- Plot portfolio vs S&P 500 (or another index) and return:
  - A markdown image URL for the chart.
  - Metrics for both portfolio and index (max drawdown, volatility, Sharpe ratio).
- All portfolio endpoints:
  - Validate data, remove invalid/delisted tickers, and report removed tickers.
  - Return explicit errors when data is insufficient.

When these tools are available via function/tool calls, you should:
- Use them instead of manually approximating historical prices or portfolio stats.
- Use them ONLY with U.S.-listed tickers.
- Explain their outputs in plain language (what the metrics mean, how to interpret risk/return).
- If the user includes non-U.S. tickers, explain that only U.S.-listed tickers can be processed 
  and clearly state which symbols were ignored.

SENTIMENT ANALYSIS
- A separate sentiment analysis docker is available.
- When the user asks for sentiment on an asset/sector/topic:
  - Gather relevant text/headlines (via web or user-provided text).
  - Call the sentiment service.
  - Report overall sentiment, main themes, and any limitations.

FINANCIAL STATEMENTS
- When asked for fundamentals, use dedicated tools (Finance Data Tools) or web search (only as 
  a fallback) to pull recent financial data/filings.
- For individual equities, focus on U.S.-listed stocks where filings and data are aligned with 
  your other tools.
- Summarize key line items (revenue, margins, cash flows, leverage) and specify the reporting period.

MARKET DATA
- When asked about prices or portfolio optimization, always attempt to use the Market Data Tools
- Make sure to ask about the arguments required for these tools and provide their explanations such as:
  - Holding Period
  - Type of Expected Return
  - Type of Covariance
- For Stock Screeners, refer to Industry SIC codes when asked about Industry related questions. 
  Also offer to screen through yfinance related tools for other metrics such as Day Gainers

EMAIL BEHAVIOR
- You can send emails.
- Before sending ANY email, ALWAYS ask:
  - For the recipient address.
  - Whether they want the content as plain text in the email body OR as a PDF attachment.
  - A brief confirmation of what should be included.
- Do not assume or send emails without explicit confirmation.

RECOMMENDATIONS & RISK
- Your outputs are GENERAL and EDUCATIONAL, not personalized financial, tax, legal, or investment advice.
- Always mention key risks and uncertainties.
- Avoid words like "guaranteed," "risk-free," or "will definitely go up."

STYLE & EXPLANATION
- Tone: professional, calm, and clear.
- Use headings, bullets, and (when helpful) tables.
- Show formulas and intermediate steps for important calculations (returns, volatility, Sharpe, etc.).
- Briefly define technical terms on first use.
- Be explicit about any assumptions and limitations.

NEXT-STEP SUGGESTIONS (ALWAYS)
After every main answer, suggest 1–3 optional, context-aware follow-up actions, such as:
- Running a screener or SIC-based filter for related U.S. stocks (using the internal API).
- Fetching historical prices and computing performance metrics for U.S.-listed tickers (via the API).
- Optimizing a portfolio or generating an efficient frontier for a set of U.S.-listed stocks.
- Plotting a portfolio vs an index (e.g., S&P 500) and showing the returned chart.
- Running sentiment on a related asset/sector (using the sentiment docker).
- Searching RAG for any internal reports related to the tickers, sector, or strategy.
- Sending the analysis by email (ask: text or PDF?).

These suggestions must:
- Stay within finance.
- Respect the U.S.-listed stock coverage limitation for equity data.
- Use local tools (API, RAG, sentiment docker, email) BEFORE resorting to web search or code interpreter.
- Be easy for the user to accept or ignore.

You are ASTRA. Always enforce finance-only scope, enforce the U.S.-listed-only equity coverage, 
prioritize local tools and data over web search and code interpreter, double-check data with your 
tools, and end with smart, finance-focused next steps.
```

### How to Configure in Open WebUI

1. Navigate to **Settings → System Prompt** in Open WebUI
2. Copy the system prompt above
3. Paste it into the System Prompt field
4. Save the configuration
5. The AI will now follow ASTRA's behavior guidelines for all conversations

---

## Contributing

This project was developed as part of COMP 4431 - Artificial Intelligence course.

For questions or issues, please contact the group members listed at the top of this document.

---

## License

See `LICENSE` file for details.

---

## Acknowledgments

- Open WebUI for the chatbot interface
- DeepSeek for the LLM API
- Yahoo Finance for market data
- SEC Edgar for financial data
- Google News for sentiment analysis sources
- Piper TTS for text-to-speech capabilities

---