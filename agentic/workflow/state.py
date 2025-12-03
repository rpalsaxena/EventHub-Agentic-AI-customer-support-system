"""
EventHub Workflow State Definition

TypedDict defining the shared state across all nodes in the workflow.
"""

from typing import TypedDict, Optional, List, Dict, Any


class TicketState(TypedDict):
    """
    State shared across all nodes in the EventHub workflow.
    
    Flow:
    1. START → classifier_node (classification)
    2. classifier_node → tool_calling_node (fetch tools based on category)
    3. tool_calling_node → resolver_node (generate response)
    4. resolver_node → router (decide: resolved or escalated)
    5. router → response_node OR escalation_node
    6. END
    """
    
    # ========== INPUT ==========
    # Ticket data (provided at start)
    ticket_id: str
    subject: str
    description: str
    user_email: Optional[str]
    reservation_id: Optional[str]
    
    # ========== CLASSIFICATION ==========
    # Results from classifier_node
    category: str           # refund, cancellation, complaint, general, technical
    urgency: str            # low, medium, high, critical
    sentiment: str          # positive, neutral, negative
    summary: str            # Brief summary of the issue
    
    # ========== TOOL RESULTS ==========
    # Results from tool_calling_node (CultPass pattern)
    tool_results: Dict[str, Any]  # {kb_results, user_info, reservation_info, ...}
    rag_confidence: float         # Confidence score from KB search (0-1)
    
    # ========== RESOLUTION ==========
    # Results from resolver_node
    response: str                 # Response to customer
    escalation_reason: str        # Why escalated (if applicable)
    
    # ========== ROUTING ==========
    # Routing decision
    status: str                   # "resolved" or "escalated"
    
    # ========== ESCALATION ==========
    # Results from escalation_node (if escalated)
    escalation_priority: int      # 1-4 (1=highest)
    customer_message: str         # Message sent to customer during escalation
    escalation_package: Dict[str, Any]  # Full context for human agent
    
    # ========== OUTPUT ==========
    # Final output
    final_response: str           # Final response to return
    final_status: str             # "resolved" or "escalated"


def create_initial_state(
    ticket_id: str,
    subject: str,
    description: str,
    user_email: Optional[str] = None,
    reservation_id: Optional[str] = None,
) -> TicketState:
    """
    Create initial state for a new ticket.
    
    Args:
        ticket_id: Unique ticket identifier
        subject: Ticket subject line
        description: Detailed ticket description
        user_email: Optional customer email
        reservation_id: Optional reservation ID
    
    Returns:
        Initial TicketState with empty processing fields
    """
    return TicketState(
        # Input
        ticket_id=ticket_id,
        subject=subject,
        description=description,
        user_email=user_email,
        reservation_id=reservation_id,
        
        # Classification (to be filled)
        category="",
        urgency="",
        sentiment="",
        summary="",
        
        # Tool results (to be filled)
        tool_results={},
        rag_confidence=0.0,
        
        # Resolution (to be filled)
        response="",
        escalation_reason="",
        
        # Routing (to be filled)
        status="",
        
        # Escalation (to be filled)
        escalation_priority=4,
        customer_message="",
        escalation_package={},
        
        # Output (to be filled)
        final_response="",
        final_status="",
    )
