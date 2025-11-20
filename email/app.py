import os
import base64
import json
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr, Field
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

app = FastAPI(title="Email Scheduler API")

# Config
SENTIMENT_API_URL = os.getenv("SENTIMENT_API_URL", "http://sentiment-analyzer:5501")
scheduler = BackgroundScheduler(jobstores={"default": MemoryJobStore()}, timezone="UTC")
scheduler.start()


# Models
class EmailRequest(BaseModel):
    to: EmailStr
    subject: str
    body: str
    html: Optional[str] = None


class ScheduleEmailRequest(EmailRequest):
    schedule_type: str = Field(
        ..., description="'once', 'hourly', 'daily', or 'weekly'"
    )
    start_time: Optional[str] = None


class SentimentEmailRequest(BaseModel):
    asset: str
    to: EmailStr
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class JobResponse(BaseModel):
    id: str
    next_run_time: Optional[str]
    trigger: str


# Gmail API
def get_gmail_service():
    creds_json = os.getenv("GMAIL_CREDENTIALS")
    if not creds_json:
        raise ValueError("GMAIL_CREDENTIALS not set")

    creds = Credentials.from_authorized_user_info(json.loads(creds_json))
    return build("gmail", "v1", credentials=creds)


def send_email(to: str, subject: str, body: str, html: Optional[str] = None) -> str:
    service = get_gmail_service()

    msg = MIMEMultipart("alternative") if html else MIMEText(body)
    if html:
        msg.attach(MIMEText(body, "plain"))
        msg.attach(MIMEText(html, "html"))

    msg["To"] = to
    msg["Subject"] = subject

    encoded = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    result = (
        service.users().messages().send(userId="me", body={"raw": encoded}).execute()
    )
    return result["id"]


# Endpoints
@app.get("/health")
def health():
    return {"ok": True, "scheduler_running": scheduler.running}


@app.post("/v1/send")
def send_now(req: EmailRequest):
    return {
        "status": "sent",
        "to": req.to,
        "subject": req.subject,
        "message_id": send_email(req.to, req.subject, req.body, req.html),
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.post("/v1/schedule", response_model=JobResponse)
def schedule(req: ScheduleEmailRequest):
    start_dt = (
        datetime.fromisoformat(req.start_time) if req.start_time else datetime.utcnow()
    )

    triggers = {
        "once": DateTrigger(run_date=start_dt),
        "hourly": IntervalTrigger(hours=1, start_date=start_dt),
        "daily": IntervalTrigger(days=1, start_date=start_dt),
        "weekly": IntervalTrigger(weeks=1, start_date=start_dt),
    }

    trigger = triggers.get(req.schedule_type)
    if not trigger:
        raise HTTPException(400, "Invalid schedule_type")

    job_id = f"email_{req.schedule_type}_{datetime.utcnow().timestamp()}"
    job = scheduler.add_job(
        send_email,
        trigger=trigger,
        args=[req.to, req.subject, req.body, req.html],
        id=job_id,
        replace_existing=True,
    )

    return JobResponse(
        id=job.id,
        next_run_time=job.next_run_time.isoformat() if job.next_run_time else None,
        trigger=req.schedule_type,
    )


@app.get("/v1/jobs")
def list_jobs():
    return [
        JobResponse(
            id=job.id,
            next_run_time=job.next_run_time.isoformat() if job.next_run_time else None,
            trigger=str(job.trigger),
        )
        for job in scheduler.get_jobs()
    ]


@app.delete("/v1/jobs/{job_id}")
def cancel_job(job_id: str):
    try:
        scheduler.remove_job(job_id)
        return {"status": "cancelled", "job_id": job_id}
    except Exception as e:
        raise HTTPException(404, f"Job not found: {str(e)}")


@app.post("/v1/send-sentiment")
def send_sentiment(req: SentimentEmailRequest):
    today = datetime.now().strftime("%Y-%m-%d")
    start = req.start_date or (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    end = req.end_date or today

    # Fetch sentiment
    try:
        resp = requests.post(
            f"{SENTIMENT_API_URL}/v1/sentiment",
            json={"asset": req.asset, "start_date": start, "end_date": end},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        raise HTTPException(500, f"Sentiment fetch failed: {str(e)}")

    analysis = data.get("analysis", "No analysis available")
    articles = data.get("articles", [])

    # Format email
    body = f"""Sentiment Analysis Report

Asset: {req.asset}
Date Range: {start} to {end}

ANALYSIS:
{analysis}

NEWS ARTICLES ({len(articles)} found):
"""
    for i, article in enumerate(articles[:15], 1):
        body += f"\n{i}. {article.get('title', 'No title')}"
        body += f"\n   Link: {article.get('link', 'N/A')}"
        if article.get("published"):
            body += f"\n   Published: {article['published']}"
        body += "\n"

    body += (
        f"\n---\nReport generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}"
    )

    # Send
    msg_id = send_email(
        req.to, f"Sentiment Analysis: {req.asset} ({start} to {end})", body
    )

    return {
        "status": "sent",
        "to": req.to,
        "asset": req.asset,
        "date_range": {"start": start, "end": end},
        "articles_analyzed": len(articles),
        "message_id": msg_id,
        "timestamp": datetime.utcnow().isoformat(),
        "preview": analysis[:200] + "..." if len(analysis) > 200 else analysis,
    }


@app.on_event("shutdown")
def shutdown():
    scheduler.shutdown()
