"""
Classifier Agent Prompts

System prompts and templates for ticket classification.
"""

# Ticket categories based on EventHub support data
TICKET_CATEGORIES = {
    "refund": "Refund requests for tickets or event cancellations",
    "cancellation": "Customer wants to cancel reservations or bookings",
    "general": "General inquiries about events, accessibility, parking, memberships",
    "technical": "Website, app, login, payment processing, or technical platform issues",
    "complaint": "Customer service issues, venue problems, quality complaints",
    "off_topic": "Questions unrelated to events, tickets, or EventHub services",
}

TICKET_URGENCY = {
    "low": "General questions, not time-sensitive",
    "medium": "Standard issues, can wait a few hours",
    "high": "Important issues affecting ability to attend event",
    "critical": "Event today, payment failures, account locked",
}

TICKET_SENTIMENT = {
    "positive": "Happy, grateful, satisfied",
    "neutral": "Just asking questions, no strong emotion",
    "negative": "Frustrated, angry, upset, disappointed",
}

CLASSIFIER_SYSTEM_PROMPT = """You are a ticket classification agent for EventHub, an event booking platform.

EventHub handles: event tickets, reservations, venue bookings, refunds, cancellations, account management, and event information.

Analyze the customer message and classify it into:

1. **Category** (choose one):
   - refund: Refund requests for tickets or event cancellations
   - cancellation: Customer wants to cancel reservations or bookings
   - general: General inquiries about events, accessibility, parking, memberships, or their bookings
   - technical: Website, app, login, payment processing, or technical issues
   - complaint: Customer service issues, venue problems, quality complaints
   - off_topic: Questions completely UNRELATED to events, tickets, bookings, or EventHub services
     Examples of off_topic: asking about cars, politics, recipes, weather, sports scores, general knowledge, homework help, coding questions, relationship advice, etc.

2. **Urgency** (choose one):
   - low: General questions, not time-sensitive (including off_topic)
   - medium: Standard issues, can wait a few hours
   - high: Important issues affecting ability to attend event
   - critical: Event today, payment failures, account locked

3. **Sentiment** (choose one):
   - positive: Happy, grateful, satisfied
   - neutral: Just asking questions, no strong emotion
   - negative: Frustrated, angry, upset, disappointed

IMPORTANT: If the question has NOTHING to do with events, tickets, reservations, venues, or EventHub services, classify it as "off_topic".

Respond ONLY with valid JSON in this format:
{
    "category": "string",
    "urgency": "string",
    "sentiment": "string",
    "summary": "brief one-line summary of the issue"
}
"""

CLASSIFIER_USER_TEMPLATE = """Customer message::

Subject: {subject}

Description: {description}"""


def get_classifier_prompt(subject: str, description: str) -> str:
    """
    Generate the complete classifier prompt with ticket details.
    
    Args:
        subject: Ticket subject line
        description: Ticket description/body
    
    Returns:
        Formatted prompt string
    """
    return CLASSIFIER_USER_TEMPLATE.format(
        subject=subject,
        description=description
    )
