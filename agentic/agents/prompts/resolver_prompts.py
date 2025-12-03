"""
Resolver Agent Prompts - CultPass Pattern

System prompts for ticket resolution using pre-fetched tool results.
"""

# Note: The main resolver prompt is now defined in resolver.py
# This file is kept for backward compatibility and future prompt variations

RESOLVER_TONE_GUIDANCE = {
    "negative": "Be empathetic, apologetic, and understanding. Acknowledge their frustration.",
    "neutral": "Be professional, helpful, and clear. Focus on solving the problem.",
    "positive": "Be friendly, enthusiastic, and appreciative. Match their positive energy."
}

RESOLVER_LENGTH_GUIDANCE = {
    "critical": "2-3 sentences maximum. Be concise and action-focused.",
    "high": "2-3 sentences. Get straight to the solution.",
    "medium": "4-5 sentences. Provide balanced explanation.",
    "low": "5-7 sentences. Give detailed, educational response."
}
