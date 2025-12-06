"""
Database Tools for EventHub Agents

Provides tools for querying user info, reservations, events, and performing actions.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, date
from sqlalchemy import create_engine, and_, or_, func
from langchain_core.tools import tool
import json

from utils import get_session, model_to_dict
from data.models.eventhub import User, Event, Venue, Reservation, Ticket


# Database configuration
DB_PATH = "data/db/eventhub.db"
engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)


@tool
def get_user_info(user_id: Optional[str] = None, email: Optional[str] = None) -> Dict[str, Any]:
    """
    Get user information by user_id or email.
    
    Args:
        user_id: User ID (e.g., "u_00001")
        email: User email address
    
    Returns:
        Dictionary with user details including subscription info
    
    Example:
        user = get_user_info(email="john@example.com")
        print(f"User: {user['full_name']}, Tier: {user['subscription_tier']}")
    """
    with get_session(engine) as session:
        if user_id:
            user = session.query(User).filter(User.user_id == user_id).first()
        elif email:
            user = session.query(User).filter(User.email == email).first()
        else:
            return {"error": "Either user_id or email must be provided"}
        
        if not user:
            return {"error": "User not found"}
        
        user_dict = model_to_dict(user)
        
        # Add subscription info
        user_dict["subscription"] = {
            "tier": user.subscription_tier,
            "status": user.subscription_status,
            "monthly_quota": user.monthly_quota,
            "started_at": str(user.subscription_started_at) if user.subscription_started_at else None,
            "ended_at": str(user.subscription_ended_at) if user.subscription_ended_at else None,
        }
        
        return user_dict


@tool
def get_reservation_info(reservation_id: str) -> Dict[str, Any]:
    """
    Get detailed information about a reservation.
    
    Args:
        reservation_id: Reservation ID (e.g., "r_00001")
    
    Returns:
        Dictionary with reservation details including event and venue info
    
    Example:
        reservation = get_reservation_info("r_00123")
        print(f"Event: {reservation['event_title']}, Status: {reservation['status']}")
    """
    with get_session(engine) as session:
        reservation = session.query(Reservation).filter(
            Reservation.reservation_id == reservation_id
        ).first()
        
        if not reservation:
            return {"error": "Reservation not found"}
        
        res_dict = model_to_dict(reservation)
        
        # Add formatted dates
        if reservation.event_date:
            res_dict["event_date_formatted"] = reservation.event_date.strftime("%B %d, %Y")
        if reservation.booking_date:
            res_dict["booking_date_formatted"] = reservation.booking_date.strftime("%B %d, %Y %I:%M %p")
        
        return res_dict


@tool
def search_events(
    category: Optional[str] = None,
    city: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    is_premium: Optional[bool] = None,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Search for events with filters.
    
    Args:
        category: Event category (e.g., "Music", "Sports", "Arts")
        city: City name
        date_from: Start date (YYYY-MM-DD)
        date_to: End date (YYYY-MM-DD)
        is_premium: Filter for premium events only
        limit: Maximum number of results (default: 10)
    
    Returns:
        List of events matching the criteria
    
    Example:
        events = search_events(category="Music", city="Mumbai", limit=5)
        for event in events:
            print(f"{event['title']} at {event['venue_name']}")
    """
    with get_session(engine) as session:
        query = session.query(Event).filter(Event.status == "active")
        
        if category:
            query = query.filter(Event.category == category)
        
        if city:
            query = query.filter(Event.city == city)
        
        if date_from:
            try:
                start_date = datetime.strptime(date_from, "%Y-%m-%d").date()
                query = query.filter(Event.event_date >= start_date)
            except ValueError:
                pass
        
        if date_to:
            try:
                end_date = datetime.strptime(date_to, "%Y-%m-%d").date()
                query = query.filter(Event.event_date <= end_date)
            except ValueError:
                pass
        
        if is_premium is not None:
            query = query.filter(Event.is_premium == is_premium)
        
        events = query.limit(limit).all()
        
        return [
            {
                **model_to_dict(event),
                "event_date_formatted": event.event_date.strftime("%B %d, %Y") if event.event_date else None,
                "available_tickets": event.total_tickets - event.tickets_sold,
            }
            for event in events
        ]


@tool
def cancel_reservation(reservation_id: str, reason: str) -> Dict[str, str]:
    """
    Cancel a reservation and update its status.
    
    Args:
        reservation_id: Reservation ID to cancel
        reason: Reason for cancellation
    
    Returns:
        Confirmation message with cancellation details
    
    Example:
        result = cancel_reservation("r_00123", "User requested cancellation")
        print(result["message"])
    """
    with get_session(engine) as session:
        reservation = session.query(Reservation).filter(
            Reservation.reservation_id == reservation_id
        ).first()
        
        if not reservation:
            return {"error": "Reservation not found", "success": False}
        
        if reservation.status == "cancelled":
            return {"error": "Reservation already cancelled", "success": False}
        
        # Update status
        old_status = reservation.status
        reservation.status = "cancelled"
        session.commit()
        
        return {
            "success": True,
            "message": f"Reservation {reservation_id} cancelled successfully",
            "reservation_id": reservation_id,
            "event_title": reservation.event_title,
            "previous_status": old_status,
            "new_status": "cancelled",
            "reason": reason,
        }


@tool
def get_user_reservations(user_id: Optional[str] = None, email: Optional[str] = None, status: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get all reservations for a specific user by user_id or email.
    
    Args:
        user_id: User ID (e.g., "u_00001")
        email: User email address
        status: Filter by status (confirmed, cancelled, pending)
        limit: Maximum number of results
    
    Returns:
        List of user's reservations with event details
    
    Example:
        reservations = get_user_reservations(email="john@example.com")
        for r in reservations:
            print(f"{r['event_title']} - {r['status']}")
    """
    with get_session(engine) as session:
        # First resolve user_id if email provided
        target_user_id = user_id
        if email and not user_id:
            user = session.query(User).filter(User.email == email).first()
            if user:
                target_user_id = user.user_id
            else:
                return [{"error": f"User with email {email} not found"}]
        
        if not target_user_id:
            return [{"error": "Either user_id or email must be provided"}]
        
        query = session.query(Reservation).filter(Reservation.user_id == target_user_id)
        
        if status:
            query = query.filter(Reservation.status == status)
        
        reservations = query.order_by(Reservation.booking_date.desc()).limit(limit).all()
        
        return [
            {
                **model_to_dict(res),
                "event_date_formatted": res.event_date.strftime("%B %d, %Y") if res.event_date else None,
            }
            for res in reservations
        ]


@tool
def get_user_tickets(user_id: Optional[str] = None, email: Optional[str] = None, status: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get support tickets for a specific user by user_id or email.
    
    Args:
        user_id: User ID (e.g., "u_00001")
        email: User email address
        status: Filter by status (open, in_progress, resolved, closed)
        limit: Maximum number of results
    
    Returns:
        List of user's support tickets
    
    Example:
        tickets = get_user_tickets(email="john@example.com")
        for t in tickets:
            print(f"{t['subject']} - {t['status']}")
    """
    with get_session(engine) as session:
        # First resolve user_id if email provided
        target_user_id = user_id
        if email and not user_id:
            user = session.query(User).filter(User.email == email).first()
            if user:
                target_user_id = user.user_id
            else:
                return [{"error": f"User with email {email} not found"}]
        
        if not target_user_id:
            return [{"error": "Either user_id or email must be provided"}]
        
        query = session.query(Ticket).filter(Ticket.user_id == target_user_id)
        
        if status:
            query = query.filter(Ticket.status == status)
        
        tickets = query.order_by(Ticket.created_at.desc()).limit(limit).all()
        
        return [model_to_dict(ticket) for ticket in tickets]


def create_support_ticket(
    ticket_id: str,
    subject: str,
    description: str,
    category: str,
    priority: str,
    status: str,
    user_email: Optional[str] = None,
    reservation_id: Optional[str] = None,
    agent_notes: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a new support ticket in the database.
    
    This is NOT a tool for the LLM - it's called by the workflow
    to persist tickets after processing.
    
    Args:
        ticket_id: Unique ticket ID (e.g., "CHAT-ABC12345")
        subject: Ticket subject/title
        description: Full ticket description
        category: Category (refund, cancellation, general, technical, complaint, off_topic)
        priority: Priority level (low, medium, high, critical)
        status: Ticket status (open, resolved, escalated)
        user_email: User's email address (optional)
        reservation_id: Related reservation ID (optional)
        agent_notes: Notes from AI agent (optional)
    
    Returns:
        Dictionary with created ticket info or error
    """
    with get_session(engine) as session:
        try:
            # Look up user_id from email if provided
            resolved_user_id: str = "u_anonymous"
            if user_email:
                user = session.query(User).filter(User.email == user_email).first()
                if user:
                    resolved_user_id = str(user.user_id)
            
            # Create the ticket
            ticket = Ticket(
                ticket_id=ticket_id,
                user_id=resolved_user_id,
                user_email=user_email,
                subject=subject,
                description=description,
                category=category,
                priority=priority,
                status=status,
                reservation_id=reservation_id,
                agent_notes=agent_notes,
                created_at=datetime.now(),
            )
            
            session.add(ticket)
            session.commit()
            
            return {
                "success": True,
                "ticket_id": ticket_id,
                "message": f"Ticket {ticket_id} created successfully"
            }
            
        except Exception as e:
            session.rollback()
            return {
                "success": False,
                "error": str(e),
                "ticket_id": ticket_id
            }
