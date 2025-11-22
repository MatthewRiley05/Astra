import os
import base64
import json
import requests
import io
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from datetime import datetime, timedelta, timezone
from typing import Optional, Literal
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_LEFT, TA_CENTER
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
    format: Literal["text", "pdf"] = Field(
        default="text",
        description="Email format: 'text' for plain text or 'pdf' for PDF attachment",
    )


class ScheduledSentimentEmailRequest(BaseModel):
    asset: str
    to: EmailStr
    interval_minutes: int = Field(
        ...,
        description="Interval in minutes between emails (e.g., 5 for every 5 minutes, 60 for hourly)",
    )
    duration_minutes: int = Field(
        ..., description="Total duration in minutes to send emails"
    )
    start_time: Optional[str] = None
    format: Literal["text", "pdf"] = Field(
        default="text",
        description="Email format: 'text' for plain text or 'pdf' for PDF attachment",
    )


class JobResponse(BaseModel):
    id: str
    next_run_time: Optional[str]
    trigger: str


# Gmail API
def generate_sentiment_pdf(
    asset: str, start: str, end: str, analysis: str, articles: list
) -> bytes:
    """Generate a PDF report for sentiment analysis"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=18,
    )

    story = []
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Heading1"],
        fontSize=24,
        textColor="#1a1a1a",
        spaceAfter=30,
        alignment=TA_CENTER,
    )

    heading_style = ParagraphStyle(
        "CustomHeading",
        parent=styles["Heading2"],
        fontSize=14,
        textColor="#333333",
        spaceAfter=12,
        spaceBefore=12,
    )

    normal_style = ParagraphStyle(
        "CustomNormal",
        parent=styles["Normal"],
        fontSize=10,
        textColor="#444444",
        alignment=TA_LEFT,
    )

    # Title
    story.append(Paragraph(f"Sentiment Analysis Report", title_style))
    story.append(Spacer(1, 0.2 * inch))

    # Metadata
    story.append(Paragraph(f"<b>Asset:</b> {asset}", normal_style))
    story.append(Paragraph(f"<b>Date Range:</b> {start} to {end}", normal_style))
    story.append(
        Paragraph(
            f"<b>Generated:</b> {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
            normal_style,
        )
    )
    story.append(Spacer(1, 0.3 * inch))

    # Analysis section
    story.append(Paragraph("Analysis", heading_style))
    analysis_lines = analysis.split("\n")
    for line in analysis_lines:
        if line.strip():
            story.append(Paragraph(line, normal_style))
            story.append(Spacer(1, 0.1 * inch))

    story.append(Spacer(1, 0.3 * inch))

    # Articles section
    story.append(Paragraph(f"News Articles ({len(articles)} found)", heading_style))
    story.append(Spacer(1, 0.1 * inch))

    for i, article in enumerate(articles[:15], 1):
        title = article.get("title", "No title")
        link = article.get("link", "N/A")
        published = article.get("published", "")

        story.append(Paragraph(f"<b>{i}. {title}</b>", normal_style))
        story.append(
            Paragraph(f"<i>Link:</i> <link href='{link}'>{link}</link>", normal_style)
        )
        if published:
            story.append(Paragraph(f"<i>Published:</i> {published}", normal_style))
        story.append(Spacer(1, 0.15 * inch))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


def send_email_with_attachment(
    to: str, subject: str, body: str, attachment_data: bytes, attachment_name: str
) -> str:
    """Send email with PDF attachment"""
    service = get_gmail_service()

    msg = MIMEMultipart()
    msg["To"] = to
    msg["Subject"] = subject

    # Attach text body
    msg.attach(MIMEText(body, "plain"))

    # Attach PDF
    pdf_part = MIMEApplication(attachment_data, _subtype="pdf")
    pdf_part.add_header("Content-Disposition", "attachment", filename=attachment_name)
    msg.attach(pdf_part)

    encoded = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    result = (
        service.users().messages().send(userId="me", body={"raw": encoded}).execute()
    )
    return result["id"]


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
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/v1/schedule", response_model=JobResponse)
def schedule(req: ScheduleEmailRequest):
    start_dt = (
        datetime.fromisoformat(req.start_time)
        if req.start_time
        else datetime.now(timezone.utc)
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

    job_id = f"email_{req.schedule_type}_{datetime.now(timezone.utc).timestamp()}"
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
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    start = req.start_date or (datetime.now(timezone.utc) - timedelta(days=7)).strftime(
        "%Y-%m-%d"
    )
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

    # Send based on format
    if req.format == "pdf":
        # Generate PDF
        pdf_data = generate_sentiment_pdf(req.asset, start, end, analysis, articles)

        # Simple text body for PDF attachment
        body = f"""Sentiment Analysis Report

Please find the detailed sentiment analysis report for {req.asset} attached as a PDF.

Date Range: {start} to {end}
Articles Analyzed: {len(articles)}

---
Report generated at {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")}"""

        filename = f"sentiment_analysis_{req.asset}_{start}_to_{end}.pdf"
        msg_id = send_email_with_attachment(
            req.to,
            f"Sentiment Analysis: {req.asset} ({start} to {end})",
            body,
            pdf_data,
            filename,
        )
    else:
        # Format text email
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

        body += f"\n---\nReport generated at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}"

        # Send
        msg_id = send_email(
            req.to, f"Sentiment Analysis: {req.asset} ({start} to {end})", body
        )

    return {
        "status": "sent",
        "to": req.to,
        "asset": req.asset,
        "format": req.format,
        "date_range": {"start": start, "end": end},
        "articles_analyzed": len(articles),
        "message_id": msg_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "preview": analysis[:200] + "..." if len(analysis) > 200 else analysis,
    }


def fetch_and_send_sentiment(to: str, asset: str, format: str = "text"):
    """Helper function to fetch sentiment and send email"""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    start = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")
    end = today

    # Fetch sentiment
    try:
        resp = requests.post(
            f"{SENTIMENT_API_URL}/v1/sentiment",
            json={"asset": asset, "start_date": start, "end_date": end},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        print(f"Sentiment fetch failed: {str(e)}")
        return

    analysis = data.get("analysis", "No analysis available")
    articles = data.get("articles", [])

    # Send based on format
    if format == "pdf":
        # Generate PDF
        pdf_data = generate_sentiment_pdf(asset, start, end, analysis, articles)

        # Simple text body for PDF attachment
        body = f"""Hourly Sentiment Analysis Report

Please find the detailed sentiment analysis report for {asset} attached as a PDF.

Date Range: {start} to {end}
Articles Analyzed: {len(articles)}

---
Report generated at {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")}"""

        filename = f"hourly_sentiment_{asset}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.pdf"
        try:
            send_email_with_attachment(
                to, f"Hourly Sentiment Update: {asset}", body, pdf_data, filename
            )
            print(f"Sent hourly sentiment PDF for {asset} to {to}")
        except Exception as e:
            print(f"Failed to send email: {str(e)}")
    else:
        # Format text email
        body = f"""Hourly Sentiment Analysis Report

Asset: {asset}
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

        body += f"\n---\nReport generated at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}"

        # Send
        try:
            send_email(to, f"Hourly Sentiment Update: {asset}", body)
            print(f"Sent hourly sentiment email for {asset} to {to}")
        except Exception as e:
            print(f"Failed to send email: {str(e)}")


@app.post("/v1/schedule-sentiment", response_model=JobResponse)
def schedule_sentiment(req: ScheduledSentimentEmailRequest):
    """
    Schedule sentiment emails at custom intervals for a specified duration.
    Examples:
    - interval_minutes=5, duration_minutes=30: Send every 5 minutes for 30 minutes
    - interval_minutes=60, duration_minutes=120: Send every hour for 2 hours
    - interval_minutes=15, duration_minutes=60: Send every 15 minutes for 1 hour
    All times are in UTC.
    Format can be 'text' (default) or 'pdf' for PDF attachment.
    """
    start_dt = (
        datetime.fromisoformat(req.start_time)
        if req.start_time
        else datetime.now(timezone.utc)
    )

    # Calculate end time
    end_dt = start_dt + timedelta(minutes=req.duration_minutes)

    job_id = f"sentiment_{req.asset}_{datetime.now(timezone.utc).timestamp()}"
    job = scheduler.add_job(
        fetch_and_send_sentiment,
        trigger=IntervalTrigger(
            minutes=req.interval_minutes, start_date=start_dt, end_date=end_dt
        ),
        args=[req.to, req.asset, req.format],
        id=job_id,
        replace_existing=True,
    )

    return JobResponse(
        id=job.id,
        next_run_time=job.next_run_time.isoformat() if job.next_run_time else None,
        trigger=f"every {req.interval_minutes} minutes for {req.duration_minutes} minutes ({req.format} format)",
    )


@app.on_event("shutdown")
def shutdown():
    scheduler.shutdown()
