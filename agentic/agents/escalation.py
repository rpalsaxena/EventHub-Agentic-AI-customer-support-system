"""Escalation Agent for EventHub Support System.

This agent handles cases that need human intervention:
- Complaints (always escalated)
- Low RAG confidence responses
- Critical + negative sentiment issues
- Tool errors in critical categories

The agent formats all context for human agents and generates
an empathetic escalation message for the customer.
"""

from langchain_aws import ChatBedrock
from langchain_core.messages import SystemMessage, HumanMessage
from typing import Optional


ESCALATION_PROMPT = """You are a customer support escalation agent for EventHub.

The customer's issue needs to be escalated to a human agent. Your job is to:
1. Acknowledge the customer's concern empathetically
2. Explain that you're connecting them with a specialist
3. Summarize what you understand about their issue
4. Assure them someone will help shortly

Customer's issue summary: {summary}
Category: {category}
Urgency: {urgency}
Sentiment: {sentiment}
Escalation Reason: {escalation_reason}

Write a brief, empathetic escalation message (2-3 sentences):"""


class EscalationAgent:
    """
    Handles escalated tickets by preparing context for human agents
    and generating empathetic customer messages.
    
    Following CultPass pattern:
    - Receives all context from resolver (no additional tool calls)
    - Single LLM call for customer message
    - Formats tool results for human agent display
    """
    
    def __init__(self, model_id: str = "us.meta.llama3-3-70b-instruct-v1:0"):
        """Initialize the escalation agent."""
        self.model_id = model_id
        self.llm = ChatBedrock(
            model_id=model_id,
            model_kwargs={
                "temperature": 0.3,
                "max_tokens": 300,
            },
            region_name="us-east-1"
        )
    
    def escalate(
        self,
        ticket_data: dict,
        classification: dict,
        tool_results: dict,
        escalation_reason: str,
        resolver_response: Optional[str] = None
    ) -> dict:
        """
        Process an escalated ticket and prepare for human handoff.
        
        Args:
            ticket_data: Original ticket information
            classification: Category, urgency, sentiment from classifier
            tool_results: Pre-fetched tool results from resolver
            escalation_reason: Why this ticket was escalated
            resolver_response: Optional response that resolver attempted
        
        Returns:
            Dictionary with customer message and escalation package
        """
        # Generate customer-facing escalation message
        customer_message = self._generate_customer_message(
            ticket_data, classification, escalation_reason
        )
        
        # Determine priority for human queue
        priority = self._calculate_priority(classification, escalation_reason)
        
        # Format escalation package for human agent
        escalation_package = self._format_escalation_package(
            ticket_data=ticket_data,
            classification=classification,
            tool_results=tool_results,
            escalation_reason=escalation_reason,
            resolver_response=resolver_response,
            priority=priority
        )
        
        return {
            "status": "escalated",
            "customer_message": customer_message,
            "escalation_package": escalation_package,
            "priority": priority
        }
    
    def _generate_customer_message(
        self,
        ticket_data: dict,
        classification: dict,
        escalation_reason: str
    ) -> str:
        """Generate empathetic message for customer about escalation."""
        prompt = ESCALATION_PROMPT.format(
            summary=classification.get("summary", ticket_data.get("subject", "Your issue")),
            category=classification.get("category", "general"),
            urgency=classification.get("urgency", "medium"),
            sentiment=classification.get("sentiment", "neutral"),
            escalation_reason=escalation_reason
        )
        
        messages = [SystemMessage(content=prompt)]
        response = self.llm.invoke(messages)
        
        return response.content.strip()
    
    def _calculate_priority(self, classification: dict, escalation_reason: str) -> int:
        """
        Calculate priority level for human queue (1=highest, 4=lowest).
        
        Priority Rules:
        - P1: Critical urgency OR complaints
        - P2: High urgency + negative sentiment
        - P3: Medium urgency OR low confidence
        - P4: Everything else
        """
        urgency = classification.get("urgency", "medium")
        sentiment = classification.get("sentiment", "neutral")
        category = classification.get("category", "general")
        
        # P1: Critical or complaints
        if urgency == "critical" or category == "complaint":
            return 1
        
        # P2: High urgency with negative sentiment
        if urgency == "high" and sentiment == "negative":
            return 2
        
        # P3: Medium urgency or confidence issues
        if urgency in ["medium", "high"] or "confidence" in escalation_reason.lower():
            return 3
        
        # P4: Low urgency
        return 4
    
    def _format_escalation_package(
        self,
        ticket_data: dict,
        classification: dict,
        tool_results: dict,
        escalation_reason: str,
        resolver_response: Optional[str],
        priority: int
    ) -> dict:
        """Format all context for human agent review."""
        return {
            "ticket_info": {
                "ticket_id": ticket_data.get("ticket_id"),
                "subject": ticket_data.get("subject"),
                "description": ticket_data.get("description"),
                "user_email": ticket_data.get("user_email"),
                "reservation_id": ticket_data.get("reservation_id"),
            },
            "classification": {
                "category": classification.get("category"),
                "urgency": classification.get("urgency"),
                "sentiment": classification.get("sentiment"),
                "summary": classification.get("summary"),
            },
            "escalation_info": {
                "reason": escalation_reason,
                "priority": priority,
                "priority_label": self._get_priority_label(priority),
                "resolver_attempted": resolver_response is not None,
            },
            "tool_results": tool_results,
        }
    
    def _get_priority_label(self, priority: int) -> str:
        """Convert priority number to label."""
        labels = {
            1: "🔴 CRITICAL",
            2: "🟠 HIGH",
            3: "🟡 MEDIUM",
            4: "🟢 LOW"
        }
        return labels.get(priority, "🟡 MEDIUM")


def print_escalation_for_human(escalation_result: dict) -> None:
    """
    Print formatted escalation details for human agent.
    This displays all the important context passed from the resolver.
    
    Args:
        escalation_result: Result from EscalationAgent.escalate()
    """
    package = escalation_result["escalation_package"]
    
    print("=" * 80)
    print("🚨 ESCALATED TICKET - HUMAN AGENT REQUIRED")
    print("=" * 80)
    
    # Priority Banner
    priority_label = package["escalation_info"]["priority_label"]
    print(f"\n📊 PRIORITY: {priority_label}")
    print(f"   Reason: {package['escalation_info']['reason']}")
    
    # Ticket Information
    print(f"\n{'─' * 40}")
    print("📋 TICKET INFORMATION")
    print(f"{'─' * 40}")
    ticket = package["ticket_info"]
    print(f"  Ticket ID: {ticket.get('ticket_id', 'N/A')}")
    print(f"  Subject: {ticket.get('subject', 'N/A')}")
    print(f"  User Email: {ticket.get('user_email', 'N/A')}")
    if ticket.get("reservation_id"):
        print(f"  Reservation ID: {ticket['reservation_id']}")
    print(f"\n  Description:")
    desc = ticket.get('description', 'N/A')
    print(f"  {desc[:300]}{'...' if len(desc) > 300 else ''}")
    
    # Classification
    print(f"\n{'─' * 40}")
    print("🏷️ CLASSIFICATION")
    print(f"{'─' * 40}")
    classification = package["classification"]
    print(f"  Category: {classification.get('category', 'N/A').upper()}")
    print(f"  Urgency: {classification.get('urgency', 'N/A').upper()}")
    print(f"  Sentiment: {classification.get('sentiment', 'N/A').upper()}")
    print(f"  Summary: {classification.get('summary', 'N/A')}")
    
    # Tool Results (Context gathered)
    print(f"\n{'─' * 40}")
    print("🔧 CONTEXT GATHERED (Tool Results)")
    print(f"{'─' * 40}")
    
    tool_results = package.get("tool_results", {})
    
    # Knowledge Base Results
    if "kb_results" in tool_results:
        print("\n  📚 KNOWLEDGE BASE ARTICLES:")
        kb_results = tool_results["kb_results"]
        if isinstance(kb_results, list) and kb_results:
            for i, article in enumerate(kb_results[:3], 1):
                title = article.get("title", "N/A")
                relevance = article.get("relevance", 0)
                print(f"    {i}. {title} (Relevance: {relevance:.1%})")
        else:
            print(f"    No relevant articles found")
    
    # User Information
    if "user_info" in tool_results:
        print("\n  👤 USER INFORMATION:")
        user_info = tool_results["user_info"]
        if isinstance(user_info, dict):
            print(f"    Name: {user_info.get('full_name', 'N/A')}")
            print(f"    Email: {user_info.get('email', 'N/A')}")
            print(f"    Subscription: {user_info.get('subscription_tier', 'N/A')} ({user_info.get('subscription_status', 'N/A')})")
            print(f"    Member Since: {user_info.get('created_at', 'N/A')}")
        else:
            print(f"    {user_info}")
    
    # Reservation Information
    if "reservation_info" in tool_results:
        print("\n  🎫 RESERVATION INFORMATION:")
        res_info = tool_results["reservation_info"]
        if isinstance(res_info, dict):
            print(f"    Reservation ID: {res_info.get('reservation_id', 'N/A')}")
            print(f"    Event: {res_info.get('event_title', 'N/A')}")
            print(f"    Date: {res_info.get('event_date', 'N/A')}")
            print(f"    Venue: {res_info.get('venue_name', 'N/A')}")
            print(f"    Status: {res_info.get('status', 'N/A')}")
            print(f"    Tickets: {res_info.get('quantity', 'N/A')}")
            print(f"    Total Price: ${res_info.get('total_price', 0):.2f}")
        else:
            print(f"    {res_info}")
    
    # Customer Message
    print(f"\n{'─' * 40}")
    print("💬 MESSAGE SENT TO CUSTOMER")
    print(f"{'─' * 40}")
    print(f"  {escalation_result['customer_message']}")
    
    print(f"\n{'=' * 80}")
    print("⏳ Waiting for human agent to take action...")
    print("=" * 80)
