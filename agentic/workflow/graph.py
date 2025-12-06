"""
EventHub LangGraph Workflow

Main workflow graph definition using LangGraph.
Orchestrates ticket processing through classification, tool calling,
resolution, and escalation.
"""

from typing import Literal
from langgraph.graph import StateGraph, END

from .state import TicketState, create_initial_state
from .nodes import (
    classifier_node,
    tool_calling_node,
    resolver_node,
    escalation_node,
    response_node,
    route_from_resolver,
)

# Import ticket creation function
from agentic.tools.db_tools import create_support_ticket


# ============================================================================
# WORKFLOW GRAPH
# ============================================================================

def create_workflow() -> StateGraph:
    """
    Create the EventHub support workflow graph.
    
    Flow:
    ```
    START
      │
      ▼
    ┌─────────────┐
    │  CLASSIFIER │  → Classify ticket (category, urgency, sentiment)
    └──────┬──────┘
           │
           ▼
    ┌─────────────┐
    │ TOOL_CALLER │  → Fetch KB articles + user/reservation info
    └──────┬──────┘
           │
           ▼
    ┌─────────────┐
    │  RESOLVER   │  → Generate response + decide escalation
    └──────┬──────┘
           │
           ▼
    ┌─────────────┐
    │   ROUTER    │  → Route based on status
    └──────┬──────┘
           │
     ┌─────┴─────┐
     │           │
     ▼           ▼
    ┌───────┐  ┌──────────┐
    │RESPOND│  │ ESCALATE │
    └───┬───┘  └────┬─────┘
        │           │
        └─────┬─────┘
              │
              ▼
            END
    ```
    
    Returns:
        Compiled LangGraph workflow
    """
    # Create the state graph
    workflow = StateGraph(TicketState)
    
    # ========== ADD NODES ==========
    workflow.add_node("classifier", classifier_node)
    workflow.add_node("tool_caller", tool_calling_node)
    workflow.add_node("resolver", resolver_node)
    workflow.add_node("escalate", escalation_node)
    workflow.add_node("respond", response_node)
    
    # ========== SET ENTRY POINT ==========
    workflow.set_entry_point("classifier")
    
    # ========== ADD EDGES ==========
    # Linear flow: classifier → tool_caller → resolver
    workflow.add_edge("classifier", "tool_caller")
    workflow.add_edge("tool_caller", "resolver")
    
    # Conditional routing from resolver
    workflow.add_conditional_edges(
        "resolver",
        route_from_resolver,
        {
            "escalate": "escalate",
            "respond": "respond",
        }
    )
    
    # Both paths end the workflow
    workflow.add_edge("escalate", END)
    workflow.add_edge("respond", END)
    
    # ========== COMPILE ==========
    app = workflow.compile()
    
    return app


# Create default orchestrator instance
orchestrator = create_workflow()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def run_ticket(
    ticket_id: str,
    subject: str,
    description: str,
    user_email: str = None,
    reservation_id: str = None,
) -> dict:
    """
    Process a support ticket through the complete workflow.
    
    Args:
        ticket_id: Unique ticket identifier
        subject: Ticket subject line
        description: Detailed ticket description
        user_email: Optional customer email
        reservation_id: Optional reservation ID
    
    Returns:
        Dictionary with workflow results:
        {
            "ticket_id": str,
            "final_response": str,
            "final_status": "resolved" | "escalated",
            "classification": {category, urgency, sentiment, summary},
            "tool_results": {...},
            "rag_confidence": float,
            "escalation_details": {...} (if escalated)
        }
    """
    # Create initial state
    initial_state = create_initial_state(
        ticket_id=ticket_id,
        subject=subject,
        description=description,
        user_email=user_email,
        reservation_id=reservation_id,
    )
    
    # Run the workflow
    result = orchestrator.invoke(initial_state)
    
    # Format output
    output = {
        "ticket_id": result.get("ticket_id"),
        "final_response": result.get("final_response", ""),
        "final_status": result.get("final_status", "resolved"),
        "classification": {
            "category": result.get("category"),
            "urgency": result.get("urgency"),
            "sentiment": result.get("sentiment"),
            "summary": result.get("summary"),
        },
        "tool_results": result.get("tool_results", {}),
        "rag_confidence": result.get("rag_confidence", 0.0),
    }
    
    # Add escalation details if escalated
    if result.get("final_status") == "escalated":
        output["escalation_details"] = {
            "priority": result.get("escalation_priority"),
            "customer_message": result.get("customer_message"),
            "escalation_reason": result.get("escalation_reason"),
            "escalation_package": result.get("escalation_package"),
        }
    
    # ========== SAVE TICKET TO DATABASE ==========
    # Map urgency to priority for database
    urgency_to_priority = {
        "low": "low",
        "medium": "medium", 
        "high": "high",
        "critical": "critical"
    }
    priority = urgency_to_priority.get(result.get("urgency", "medium"), "medium")
    
    # Map final_status to ticket status
    status = "resolved" if result.get("final_status") == "resolved" else "escalated"
    
    # Create agent notes with summary
    agent_notes = f"AI Classification: {result.get('category')} | {result.get('urgency')} | {result.get('sentiment')}\n"
    agent_notes += f"Summary: {result.get('summary', '')}\n"
    agent_notes += f"RAG Confidence: {result.get('rag_confidence', 0.0):.1%}"
    
    # Save to database
    try:
        save_result = create_support_ticket(
            ticket_id=ticket_id,
            subject=subject,
            description=description,
            category=result.get("category", "general"),
            priority=priority,
            status=status,
            user_email=user_email,
            reservation_id=reservation_id,
            agent_notes=agent_notes,
        )
        output["ticket_saved"] = save_result.get("success", False)
    except Exception as e:
        output["ticket_saved"] = False
        output["ticket_save_error"] = str(e)
    
    return output


def process_ticket_dict(ticket_data: dict) -> dict:
    """
    Process a ticket from a dictionary (convenience wrapper).
    
    Args:
        ticket_data: Dictionary with ticket fields:
            - ticket_id (required)
            - subject (required)
            - description (required)
            - user_email (optional)
            - reservation_id (optional)
    
    Returns:
        Workflow result dictionary
    """
    return run_ticket(
        ticket_id=ticket_data.get("ticket_id", "UNKNOWN"),
        subject=ticket_data.get("subject", ""),
        description=ticket_data.get("description", ""),
        user_email=ticket_data.get("user_email"),
        reservation_id=ticket_data.get("reservation_id"),
    )
