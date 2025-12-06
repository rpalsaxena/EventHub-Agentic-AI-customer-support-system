"""
EventHub Workflow Nodes

Node functions for the LangGraph workflow.
Each node processes the state and returns updated state.
"""

from typing import Dict, Any
from .state import TicketState

# Import agents
from agentic.agents.classifier import TicketClassifier
from agentic.agents.resolver import TicketResolver
from agentic.agents.escalation import EscalationAgent

# Import tools
from agentic.tools.rag_tools import search_knowledge_base
from agentic.tools.db_tools import get_user_info, get_reservation_info, get_user_reservations, get_user_tickets


# ============================================================================
# INITIALIZE AGENTS (cached)
# ============================================================================

_classifier = None
_resolver = None
_escalation_agent = None


def get_classifier() -> TicketClassifier:
    """Get or create classifier agent (singleton)."""
    global _classifier
    if _classifier is None:
        _classifier = TicketClassifier()
    return _classifier


def get_resolver() -> TicketResolver:
    """Get or create resolver agent (singleton)."""
    global _resolver
    if _resolver is None:
        _resolver = TicketResolver()
    return _resolver


def get_escalation_agent() -> EscalationAgent:
    """Get or create escalation agent (singleton)."""
    global _escalation_agent
    if _escalation_agent is None:
        _escalation_agent = EscalationAgent()
    return _escalation_agent


# ============================================================================
# NODE FUNCTIONS
# ============================================================================

def classifier_node(state: TicketState) -> Dict[str, Any]:
    """
    Node 1: Classify the incoming ticket.
    
    Determines:
    - Category (refund, cancellation, complaint, general, technical)
    - Urgency (low, medium, high, critical)
    - Sentiment (positive, neutral, negative)
    - Summary (brief description)
    
    Args:
        state: Current workflow state with ticket info
    
    Returns:
        Updated state fields for classification
    """
    classifier = get_classifier()
    
    # Classify the ticket
    classification = classifier.classify(
        subject=state["subject"],
        description=state["description"],
        ticket_id=state.get("ticket_id")
    )
    
    return {
        "category": classification.get("category", "general"),
        "urgency": classification.get("urgency", "medium"),
        "sentiment": classification.get("sentiment", "neutral"),
        "summary": classification.get("summary", ""),
    }


def tool_calling_node(state: TicketState) -> Dict[str, Any]:
    """
    Node 2: Fetch tool results based on category (CultPass pattern).
    
    Deterministic tool selection:
    - off_topic: Return polite rejection, skip all tool calls
    - Always: Search knowledge base
    - If user_email exists: Fetch user_info, user_reservations, user_tickets
    - refund/cancellation/complaint: + specific reservation_info if ID provided
    
    Args:
        state: Current workflow state with classification
    
    Returns:
        Updated state with tool_results and rag_confidence
    """
    tool_results = {}
    category = state.get("category", "general")
    
    # ========== GUARDRAIL: Handle off-topic queries ==========
    if category == "off_topic":
        # Return early with polite rejection - no expensive tool calls
        return {
            "tool_results": {"off_topic": True},
            "rag_confidence": 0.0,
            "status": "resolved",
            "response": (
                "I'm EventHub's customer support assistant, and I specialize in helping with "
                "event bookings, tickets, reservations, refunds, and account-related questions. "
                "Unfortunately, I'm not able to help with questions outside of these topics. "
                "Is there anything related to your EventHub experience I can assist you with?"
            ),
        }
    
    # Build query from ticket
    query = f"{state['subject']} {state['description']}"
    
    # ========== ALWAYS: Search Knowledge Base ==========
    try:
        kb_results = search_knowledge_base.invoke({"query": query, "top_k": 3})
        tool_results["kb_results"] = kb_results
    except Exception as e:
        tool_results["kb_results"] = [{"error": str(e)}]
    
    # Calculate RAG confidence from top result
    rag_confidence = 0.0
    if tool_results.get("kb_results") and isinstance(tool_results["kb_results"], list):
        if len(tool_results["kb_results"]) > 0:
            first_result = tool_results["kb_results"][0]
            if isinstance(first_result, dict) and "relevance" in first_result:
                rag_confidence = first_result.get("relevance", 0.0)
    
    category = state.get("category", "general")
    user_email = state.get("user_email")
    
    # ========== If user email provided: Fetch ALL user context ==========
    if user_email:
        # Get user info
        try:
            user_info = get_user_info.invoke({"email": user_email})
            tool_results["user_info"] = user_info
        except Exception as e:
            tool_results["user_info"] = {"error": str(e)}
        
        # Get user's reservations (ALWAYS - so we can answer "what did I book?")
        try:
            user_reservations = get_user_reservations.invoke({"email": user_email, "limit": 10})
            tool_results["user_reservations"] = user_reservations
        except Exception as e:
            tool_results["user_reservations"] = [{"error": str(e)}]
        
        # Get user's support tickets (for context on previous issues)
        try:
            user_tickets = get_user_tickets.invoke({"email": user_email, "limit": 5})
            tool_results["user_support_tickets"] = user_tickets
        except Exception as e:
            tool_results["user_support_tickets"] = [{"error": str(e)}]
    
    # ========== Category-specific: Specific reservation lookup ==========
    if category in ["refund", "cancellation", "complaint"]:
        # If specific reservation ID provided, get detailed info
        if state.get("reservation_id"):
            try:
                reservation_info = get_reservation_info.invoke({"reservation_id": state["reservation_id"]})
                tool_results["reservation_info"] = reservation_info
            except Exception as e:
                tool_results["reservation_info"] = {"error": str(e)}
    
    return {
        "tool_results": tool_results,
        "rag_confidence": rag_confidence,
    }


def resolver_node(state: TicketState) -> Dict[str, Any]:
    """
    Node 3: Generate resolution response using pre-fetched tool results.
    
    Uses the CultPass pattern:
    - Receives tool_results from previous node
    - Single LLM call for response generation
    - Code-based escalation decision
    
    Args:
        state: Current workflow state with tool_results
    
    Returns:
        Updated state with response, status, escalation_reason
    """
    # If off_topic was handled in tool_calling_node, response is already set
    if state.get("tool_results", {}).get("off_topic"):
        return {
            "response": state.get("response", "I can only help with EventHub-related questions."),
            "status": "resolved",
            "escalation_reason": "",
            "rag_confidence": 0.0,
        }
    
    resolver = get_resolver()
    
    # Build ticket_data from state
    ticket_data = {
        "ticket_id": state.get("ticket_id"),
        "subject": state.get("subject"),
        "description": state.get("description"),
        "user_email": state.get("user_email"),
        "reservation_id": state.get("reservation_id"),
    }
    
    # Build classification from state
    classification = {
        "category": state.get("category"),
        "urgency": state.get("urgency"),
        "sentiment": state.get("sentiment"),
        "summary": state.get("summary"),
    }
    
    # Resolve using pre-fetched tool results
    resolution = resolver.resolve(
        ticket_data=ticket_data,
        classification=classification,
        tool_results=state.get("tool_results", {})
    )
    
    return {
        "response": resolution.get("response", ""),
        "status": resolution.get("status", "resolved"),
        "escalation_reason": resolution.get("escalation_reason", ""),
        "rag_confidence": resolution.get("rag_confidence", state.get("rag_confidence", 0.0)),
    }


def escalation_node(state: TicketState) -> Dict[str, Any]:
    """
    Node 4a: Handle escalated tickets.
    
    Prepares escalation package for human agents:
    - Generates empathetic customer message
    - Formats all context for human review
    - Calculates priority
    
    Args:
        state: Current workflow state with escalation_reason
    
    Returns:
        Updated state with escalation details
    """
    escalation_agent = get_escalation_agent()
    
    # Build ticket_data from state
    ticket_data = {
        "ticket_id": state.get("ticket_id"),
        "subject": state.get("subject"),
        "description": state.get("description"),
        "user_email": state.get("user_email"),
        "reservation_id": state.get("reservation_id"),
    }
    
    # Build classification from state
    classification = {
        "category": state.get("category"),
        "urgency": state.get("urgency"),
        "sentiment": state.get("sentiment"),
        "summary": state.get("summary"),
    }
    
    # Process escalation
    escalation_result = escalation_agent.escalate(
        ticket_data=ticket_data,
        classification=classification,
        tool_results=state.get("tool_results", {}),
        escalation_reason=state.get("escalation_reason", "Unknown"),
        resolver_response=state.get("response")
    )
    
    return {
        "escalation_priority": escalation_result.get("priority", 3),
        "customer_message": escalation_result.get("customer_message", ""),
        "escalation_package": escalation_result.get("escalation_package", {}),
        "final_response": escalation_result.get("customer_message", ""),
        "final_status": "escalated",
    }


def response_node(state: TicketState) -> Dict[str, Any]:
    """
    Node 4b: Finalize resolved tickets.
    
    Sets final response for resolved tickets.
    
    Args:
        state: Current workflow state with response
    
    Returns:
        Updated state with final_response and final_status
    """
    return {
        "final_response": state.get("response", ""),
        "final_status": "resolved",
    }


# ============================================================================
# ROUTING FUNCTION
# ============================================================================

def route_from_resolver(state: TicketState) -> str:
    """
    Router: Decide between response_node and escalation_node.
    
    Args:
        state: Current workflow state with status
    
    Returns:
        "escalate" or "respond" based on status
    """
    status = state.get("status", "resolved")
    
    if status == "escalated":
        return "escalate"
    return "respond"
