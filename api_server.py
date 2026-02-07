# api_server.py

import json
import os

from fastapi import FastAPI
from pydantic import BaseModel
from google import genai
from google.genai import types

from my_agent.agent import root_agent  # email_triage_agent set as root_agent


# ---------- CONFIG ----------

API_KEY = "AIzaSyAdlkVRjc0-QJT0kdXNBNC5rO-5WPQORU0"  # put your Gemini API key here
client = genai.Client(api_key=API_KEY)

app = FastAPI(title="Email Triage API")


# ---------- MODELS ----------

class Email(BaseModel):
    sender: str
    recipient: str
    subject: str
    body: str


# ---------- ROUTES ----------

@app.post("/triage-email")
async def triage(email: Email):
    """
    Triage a single email and return JSON with:
    category, priority, labels, summary, reply_draft.
    """
    prompt = (
        "Here is an email:\n"
        f"From: {email.sender}\n"
        f"To: {email.recipient}\n"
        f"Subject: {email.subject}\n"
        f"Body:\n{email.body}\n"
    )

    system_instruction = root_agent.instruction
    model = root_agent.model

    resp = client.models.generate_content(
        model=model,
        contents=[prompt],
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.2,
        ),
    )

    text = resp.text.strip()

    # Try to parse JSON directly
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Fallback: extract JSON between first { and last }
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        json_str = text[start : end + 1]
        return json.loads(json_str)

    # Last resort: return raw text so you can inspect problems
    return {"raw_output": text}
