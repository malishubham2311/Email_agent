# my_agent/agent.py

from google.adk.agents import Agent


def get_current_time(city: str) -> dict:
    import datetime
    return {
        "city": city,
        "time": datetime.datetime.now().isoformat(),
    }


time_agent = Agent(
    model="gemini-2.5-flash",
    name="time_agent",
    description="Tells the current time.",
    instruction=(
        "You are a helpful assistant that tells users the current time. "
        "Use the get_current_time tool whenever a user asks for the time "
        "in a city, then reply in natural language."
    ),
    tools=[get_current_time],
)

email_triage_agent = Agent(
    model="gemini-2.5-flash",
    name="email_triage_agent",
    description="Classifies emails and drafts replies.",
    instruction=(
        "You triage emails for a busy professional.\n"
        "The user will paste the full email text (From, To, Subject, Body).\n"
        "You MUST respond with ONLY a JSON object, no extra text, with keys:\n"
        "  - category: one of ['respond_now','respond_later','forward','archive','spam']\n"
        "  - priority: one of ['high','medium','low']\n"
        "  - labels: list of strings like ['WORK','NEWSLETTER','URGENT','SPAM']\n"
        "  - summary: brief summary of the email in <= 2 sentences\n"
        "  - reply_draft: a short polite reply, or empty string.\n"
        "  - confidence: a float between 0 and 1 (e.g., 0.93) representing how confident you are in the category.\n"
        "  - suggested_action: one of ['label_only','needs_reply','needs_forward','ignore'].\n"
        "\n"
        "Rules:\n"
        "  - If the email is a marketing campaign, promotion, sales offer, or newsletter, "
        "set category='archive', priority='low', labels must include 'NEWSLETTER', "
        "suggested_action='label_only', and confidence should usually be >= 0.8.\n"
        "  - If the email is clear spam or scam (suspicious links, unrealistic offers), "
        "set category='spam', labels should include 'SPAM', suggested_action='ignore', "
        "and confidence should usually be >= 0.8.\n"
        "  - If the sender domain matches the user's company domain (e.g., '@company.com'), "
        "labels should include 'WORK'. These are more important by default.\n"
        "  - If the email clearly requires you to answer a question or confirm something, "
        "use category='respond_now' or 'respond_later' and suggested_action='needs_reply'.\n"
        "  - If the email is mainly for another person or team to act on, "
        "use category='forward' and suggested_action='needs_forward'.\n"
        "\n"
        "Do not explain your reasoning, only output JSON."
    ),
)



# ADK looks for this name:
root_agent = email_triage_agent
