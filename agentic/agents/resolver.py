"""Resolver Agent - CultPass Pattern

Resolves customer tickets using RAG (knowledge base) and database tools.
Tools are called BEFORE resolver invocation (in workflow node).
Resolver formats the response using pre-fetched tool results.
"""

import os
from typing import Dict, Any, Tuple
from langchain_aws import ChatBedrock
from langchain_core.messages import SystemMessage


# Resolver System Prompt
RESOLVER_PROMPT = """You are a helpful customer support agent for EventHub, an event booking platform.

Use the following knowledge base articles to answer the customer's question:

{kb_context}

{tool_context}

Guidelines:
- Be friendly and helpful
- Adjust your tone based on customer sentiment:
  * Negative: Be empathetic and apologetic
  * Neutral: Be professional and helpful
  * Positive: Be friendly and enthusiastic
- Answer based ONLY on the provided context and tool results
- If the answer is not in the context, say "I don't have enough information to fully resolve this. Let me connect you with a specialist."
- Keep responses concise but complete
- For urgent/critical issues: 2-3 sentences (action-focused)
- For medium urgency: 4-5 sentences (balanced)
- For low urgency: 5-7 sentences (detailed, educational)
- If customer needs to take action, provide clear step-by-step instructions
- When showing account information, format it clearly

Ticket Classification:
Category: {category}
Urgency: {urgency}
Sentiment: {sentiment}
Summary: {summary}

Customer question: {question}

Your response:"""


class TicketResolver:
    """
    Ticket resolution agent - CultPass pattern.
    
    Receives pre-fetched tool results and generates customer response.
    Does NOT call tools autonomously - workflow handles tool execution.
    """
    
    def __init__(
        self,
        model_id: str = "us.meta.llama3-3-70b-instruct-v1:0",
        region_name: str | None = None,
        temperature: float = 0.3,
    ):
        """
        Initialize the ticket resolver.
        
        Args:
            model_id: Bedrock model ID (default: Llama 3.3 70B inference profile)
            region_name: AWS region (default: from environment or us-east-1)
            temperature: Model temperature (default: 0.3 for balanced creativity)
        """
        self.model_id = model_id
        self.region_name = region_name or os.getenv("AWS_DEFAULT_REGION", "us-east-1")
        self.temperature = temperature
        
        # Initialize Bedrock LLM (no tool binding - CultPass pattern)
        self.llm = ChatBedrock(
            model=self.model_id,
            model_kwargs={
                "temperature": self.temperature,
                "max_tokens": 2000,
            }
        )
    
    def resolve(
        self,
        ticket_data: Dict[str, Any],
        classification: Dict[str, Any],
        tool_results: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Generate resolution response using pre-fetched tool results.
        
        Args:
            ticket_data: Ticket information (subject, description, user_email, etc.)
            classification: Classification results (category, urgency, sentiment, summary)
            tool_results: Pre-fetched tool results from workflow
                {
                    "kb_results": [...],           # KB search results
                    "user_info": {...},            # User account info (optional)
                    "reservation_info": {...},     # Reservation details (optional)
                    "user_reservations": [...],    # User's bookings (optional)
                    "events": [...],               # Event search results (optional)
                }
        
        Returns:
            Dictionary with resolution results:
            {
                "status": "resolved" | "escalated",
                "response": str,              # Response to customer
                "tool_results": dict,         # Tool results (for human review on escalation)
                "escalation_reason": str,     # Why escalated (if applicable)
                "rag_confidence": float,      # KB relevance score
            }
        """
        # Extract KB confidence
        rag_confidence = 0.0
        kb_results = tool_results.get("kb_results", [])
        if kb_results and isinstance(kb_results, list) and len(kb_results) > 0:
            rag_confidence = kb_results[0].get("relevance", 0.0)
        
        # Build KB context
        if kb_results and isinstance(kb_results, list):
            kb_context = "\n\n---\n\n".join([
                f"**{article.get('title', 'Article')}** (Relevance: {article.get('relevance', 0):.1%})\n{article.get('content', '')}"
                for article in kb_results[:3]
            ])
        else:
            kb_context = "No relevant knowledge base articles found."
        
        # Build tool context from other tool results
        tool_context_parts = []
        
        # User info
        user_info = tool_results.get("user_info")
        if user_info and isinstance(user_info, dict):
            tool_context_parts.append("**User Account Information:**")
            tool_context_parts.append(f"Name: {user_info.get('full_name', 'N/A')}")
            tool_context_parts.append(f"Email: {user_info.get('email', 'N/A')}")
            tool_context_parts.append(f"Subscription: {user_info.get('subscription_tier', 'basic')} ({user_info.get('subscription_status', 'active')})")
        
        # Reservation info
        reservation_info = tool_results.get("reservation_info")
        if reservation_info and isinstance(reservation_info, dict):
            tool_context_parts.append("\n**Reservation Details:**")
            tool_context_parts.append(f"Reservation ID: {reservation_info.get('reservation_id', 'N/A')}")
            tool_context_parts.append(f"Event: {reservation_info.get('event_title', 'N/A')}")
            tool_context_parts.append(f"Date: {reservation_info.get('event_date', 'N/A')}")
            tool_context_parts.append(f"Status: {reservation_info.get('status', 'N/A')}")
            tool_context_parts.append(f"Total: ${reservation_info.get('total_price', 0):.2f}")
        
        # User reservations
        user_reservations = tool_results.get("user_reservations", [])
        if user_reservations and isinstance(user_reservations, list):
            tool_context_parts.append(f"\n**User has {len(user_reservations)} reservation(s)**")
        
        tool_context = "\n".join(tool_context_parts) if tool_context_parts else "No additional account information available."
        
        # Build question
        question = f"{ticket_data.get('subject', '')}. {ticket_data.get('description', '')}"
        
        # Build prompt
        prompt = RESOLVER_PROMPT.format(
            kb_context=kb_context,
            tool_context=tool_context,
            category=classification.get("category", "general"),
            urgency=classification.get("urgency", "medium"),
            sentiment=classification.get("sentiment", "neutral"),
            summary=classification.get("summary", ""),
            question=question
        )
        
        # Generate response using LLM
        try:
            response = self.llm.invoke([SystemMessage(content=prompt)])
            response_text = response.content
            if isinstance(response_text, list):
                response_text = " ".join(str(part) for part in response_text)
            else:
                response_text = str(response_text)
            
            # Make escalation decision (code-based)
            should_escalate, escalation_reason = self._should_escalate(
                classification=classification,
                rag_confidence=rag_confidence,
                kb_results=kb_results,
                response_text=response_text,
                tool_results=tool_results
            )
            
            # Build final result
            result = {
                "status": "escalated" if should_escalate else "resolved",
                "response": response_text,
                "tool_results": tool_results,  # Pass all tool results to human for context
                "escalation_reason": escalation_reason if should_escalate else "",
                "rag_confidence": rag_confidence,
                "classification": classification,
                "ticket_id": ticket_data.get("ticket_id"),
            }
            
            return result
            
        except Exception as e:
            # On error, escalate with context
            return {
                "status": "escalated",
                "response": "",
                "tool_results": tool_results,
                "escalation_reason": f"Resolution error: {str(e)}",
                "rag_confidence": rag_confidence,
                "classification": classification,
                "ticket_id": ticket_data.get("ticket_id"),
                "error": str(e),
            }
    
    def _should_escalate(
        self,
        classification: Dict[str, Any],
        rag_confidence: float,
        kb_results: list,
        response_text: str,
        tool_results: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """
        Determine if ticket should be escalated (code-based, NOT LLM decision).
        
        Args:
            classification: Classification results
            rag_confidence: KB relevance score (0-1)
            kb_results: Knowledge base search results
            response_text: Generated response
            tool_results: All tool results
        
        Returns:
            Tuple of (should_escalate, reason)
        """
        category = classification.get("category", "general")
        urgency = classification.get("urgency", "medium")
        sentiment = classification.get("sentiment", "neutral")
        
        # Rule 1: Always escalate complaints
        if category == "complaint":
            return True, "Complaints require human review for customer satisfaction"
        
        # Rule 2: Low KB confidence (<50% relevance)
        if rag_confidence < 0.5:
            return True, f"Low knowledge base confidence ({rag_confidence:.1%})"
        
        # Rule 3: No KB results found
        if not kb_results or len(kb_results) == 0:
            return True, "No relevant knowledge base articles found"
        
        # Rule 4: Response indicates insufficient information
        insufficient_markers = [
            "don't have enough information",
            "don't have that information",
            "connect you with a specialist",
            "unable to resolve",
            "need to escalate",
            "let me connect you"
        ]
        if any(marker in response_text.lower() for marker in insufficient_markers):
            return True, "Response indicates need for specialist assistance"
        
        # Rule 5: Critical + negative combination (extra scrutiny)
        if urgency == "critical" and sentiment == "negative" and rag_confidence < 0.7:
            return True, f"Critical negative issue with moderate KB confidence ({rag_confidence:.1%})"
        
        # Rule 6: Check for tool errors
        for key, value in tool_results.items():
            if isinstance(value, str) and "error" in value.lower():
                # Tool returned error - might need human intervention
                if category in ["refund", "cancellation"]:
                    # Critical categories - escalate on tool errors
                    return True, f"Tool error in critical category: {value[:100]}"
        
        # Otherwise, can resolve
        return False, ""


# Convenience function for quick resolution
def resolve_ticket(
    ticket_data: Dict[str, Any],
    classification: Dict[str, Any],
    tool_results: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Quick ticket resolution function.
    
    Args:
        ticket_data: Ticket information
        classification: Classification results
        tool_results: Pre-fetched tool results
    
    Returns:
        Resolution result dictionary
    """
    resolver = TicketResolver()
    return resolver.resolve(ticket_data, classification, tool_results)
