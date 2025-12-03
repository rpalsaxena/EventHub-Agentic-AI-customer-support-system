"""
Ticket Classifier Agent

Classifies support tickets into appropriate categories using Llama 3.3 70B via AWS Bedrock.
Uses structured JSON output for reliable category assignment.
"""

import json
import os
from typing import Dict, Optional, Any
from langchain_aws import ChatBedrock
from langchain_core.messages import HumanMessage, SystemMessage

from .prompts.classifier_prompts import (
    TICKET_CATEGORIES,
    CLASSIFIER_SYSTEM_PROMPT,
    get_classifier_prompt,
)


class TicketClassifier:
    """
    Ticket classification agent using Llama 3.3 70B via Bedrock.
    
    Analyzes ticket subject and description to assign the most appropriate category.
    Returns structured classification with confidence score and reasoning.
    """
    
    def __init__(
        self,
        model_id: str = "us.meta.llama3-3-70b-instruct-v1:0",
        region_name: Optional[str] = None,
        temperature: float = 0.1,
    ):
        """
        Initialize the ticket classifier.
        
        Args:
            model_id: Bedrock model ID (default: Llama 3.3 70B inference profile)
            region_name: AWS region (default: from environment or us-east-1)
            temperature: Model temperature for consistency (default: 0.1 for deterministic)
        """
        self.model_id = model_id
        self.region_name = region_name or os.getenv("AWS_DEFAULT_REGION", "us-east-1")
        self.temperature = temperature
        self.categories = list(TICKET_CATEGORIES.keys())
        
        # Initialize Bedrock LLM with cross-region inference profile
        self.llm = ChatBedrock(
            model=self.model_id,
            model_kwargs={
                "temperature": self.temperature,
                "max_tokens": 500,
            }
        ) # type: ignore
    
    def classify(
        self,
        subject: str,
        description: str,
        ticket_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Classify a support ticket into category, urgency, and sentiment.
        
        Args:
            subject: Ticket subject line
            description: Ticket description/body text
            ticket_id: Optional ticket ID for logging/tracking
        
        Returns:
            Dictionary with classification results:
            {
                "category": str,      # refund, cancellation, general, technical, complaint
                "urgency": str,       # low, medium, high, critical
                "sentiment": str,     # positive, neutral, negative
                "summary": str,       # One-line summary of the issue
                "ticket_id": str,     # Original ticket ID (if provided)
            }
        
        Example:
            classifier = TicketClassifier()
            result = classifier.classify(
                subject="Need refund for cancelled event",
                description="The event I booked was cancelled and I want my money back"
            )
            print(result["category"])  # "refund"
            print(result["urgency"])   # "high"
            print(result["sentiment"]) # "negative"
        """
        # Generate prompt
        user_prompt = get_classifier_prompt(subject, description)
        
        # Create messages
        messages = [
            SystemMessage(content=CLASSIFIER_SYSTEM_PROMPT),
            HumanMessage(content=user_prompt)
        ]
        
        # Call LLM
        try:
            response = self.llm.invoke(messages)
            # Handle response content (can be str or list)
            response_text = response.content
            if isinstance(response_text, list):
                # Join list of content parts
                response_text = " ".join(str(part) for part in response_text)
            
            # Parse JSON response
            classification = self._parse_response(str(response_text))
            
            # Validate category
            category = classification.get("category", "general").lower()
            if category not in self.categories:
                category = "general"
            
            # Build result
            result = {
                "category": category,
                "urgency": classification.get("urgency", "medium"),
                "sentiment": classification.get("sentiment", "neutral"),
                "summary": classification.get("summary", ""),
            }
            
            if ticket_id:
                result["ticket_id"] = ticket_id
            
            return result
            
        except Exception as e:
            # Handle errors gracefully
            return {
                "category": "general",
                "urgency": "medium",
                "sentiment": "neutral",
                "summary": f"Classification error: {str(e)}",
                "error": str(e),
                "ticket_id": ticket_id,
            }
    
    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse JSON response from LLM.
        
        Args:
            response_text: Raw response text from LLM
        
        Returns:
            Parsed JSON dictionary
        
        Raises:
            ValueError: If JSON parsing fails
        """
        # Try to extract JSON from response
        # Sometimes LLM adds extra text before/after JSON
        try:
            # Find JSON object in response
            start_idx = response_text.find("{")
            end_idx = response_text.rfind("}") + 1
            
            if start_idx != -1 and end_idx > start_idx:
                json_str = response_text[start_idx:end_idx]
                return json.loads(json_str)
            else:
                # No JSON found, try parsing entire response
                return json.loads(response_text)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON response: {e}\nResponse: {response_text}")
    
    def classify_batch(
        self,
        tickets: list[Dict[str, str]]
    ) -> list[Dict[str, Any]]:
        """
        Classify multiple tickets in batch.
        
        Args:
            tickets: List of ticket dictionaries with 'subject', 'description', and optional 'ticket_id'
        
        Returns:
            List of classification results
        
        Example:
            tickets = [
                {"subject": "Refund request", "description": "..."},
                {"subject": "Can't login", "description": "..."},
            ]
            results = classifier.classify_batch(tickets)
        """
        results = []
        for ticket in tickets:
            result = self.classify(
                subject=ticket.get("subject", ""),
                description=ticket.get("description", ""),
                ticket_id=ticket.get("ticket_id")
            )
            results.append(result)
        return results
    
    def get_category_distribution(
        self,
        classifications: list[Dict[str, Any]]
    ) -> Dict[str, int]:
        """
        Get distribution of categories from classification results.
        
        Args:
            classifications: List of classification results
        
        Returns:
            Dictionary mapping category to count
        """
        distribution = {category: 0 for category in self.categories}
        
        for result in classifications:
            category = result.get("category", "general")
            distribution[category] = distribution.get(category, 0) + 1
        
        return distribution


# Convenience function for quick classification
def classify_ticket(subject: str, description: str, ticket_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Quick classification function without instantiating classifier.
    
    Args:
        subject: Ticket subject
        description: Ticket description
        ticket_id: Optional ticket ID
    
    Returns:
        Classification result dictionary
    """
    classifier = TicketClassifier()
    return classifier.classify(subject, description, ticket_id)