"""
EventHub AI Support - Simple Chat API with Streaming
"""

import sys
import uuid
import asyncio
import json
from pathlib import Path
from typing import Optional, List

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy import create_engine, func, text
from sqlalchemy.orm import sessionmaker

from agentic.workflow import run_ticket

# Database setup
DB_PATH = Path(__file__).parent.parent / "data" / "db" / "eventhub.db"
engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
SessionLocal = sessionmaker(bind=engine)

# Initialize FastAPI
app = FastAPI(title="EventHub AI Support", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files
frontend_path = Path(__file__).parent / "static"
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")


# ============================================================================
# SCHEMAS (Simple - just 2)
# ============================================================================

class ChatRequest(BaseModel):
    """User message input."""
    message: str
    email: Optional[str] = None
    reservation_id: Optional[str] = None


class ChatResponse(BaseModel):
    """AI response output."""
    status: str  # "resolved" or "escalated"
    response: str
    category: str
    urgency: str
    sentiment: str
    confidence: float


# ============================================================================
# ENDPOINTS
# ============================================================================

@app.get("/")
async def serve_frontend():
    """Serve the chat interface."""
    index_path = frontend_path / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"message": "Frontend not found. Use /chat endpoint."}


@app.get("/dashboard")
async def serve_dashboard():
    """Serve the dashboard interface."""
    dashboard_path = frontend_path / "dashboard.html"
    if dashboard_path.exists():
        return FileResponse(str(dashboard_path))
    return {"message": "Dashboard not found."}


@app.get("/health")
async def health():
    """Health check."""
    return {"status": "ok", "service": "EventHub AI Support"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Process a chat message through the AI workflow.
    Returns complete response (non-streaming).
    """
    ticket_id = f"CHAT-{uuid.uuid4().hex[:8].upper()}"
    
    result = run_ticket(
        ticket_id=ticket_id,
        subject=request.message[:100],  # First 100 chars as subject
        description=request.message,
        user_email=request.email,
        reservation_id=request.reservation_id
    )
    
    return ChatResponse(
        status=result["final_status"],
        response=result["final_response"],
        category=result["classification"]["category"],
        urgency=result["classification"]["urgency"],
        sentiment=result["classification"]["sentiment"],
        confidence=result["rag_confidence"]
    )


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    Process a chat message with streaming response.
    Streams the AI response word by word like ChatGPT.
    """
    ticket_id = f"CHAT-{uuid.uuid4().hex[:8].upper()}"
    
    # Get the full response first (our workflow isn't natively streaming)
    result = run_ticket(
        ticket_id=ticket_id,
        subject=request.message[:100],
        description=request.message,
        user_email=request.email,
        reservation_id=request.reservation_id
    )
    
    async def generate():
        """Stream response word by word."""
        # First, send metadata as JSON
        import json
        metadata = {
            "type": "metadata",
            "status": result["final_status"],
            "category": result["classification"]["category"],
            "urgency": result["classification"]["urgency"],
            "sentiment": result["classification"]["sentiment"],
            "confidence": result["rag_confidence"]
        }
        yield f"data: {json.dumps(metadata)}\n\n"
        
        # Then stream the response text word by word
        response_text = result["final_response"]
        words = response_text.split(" ")
        
        for i, word in enumerate(words):
            # Add space before word (except first)
            if i > 0:
                word = " " + word
            
            chunk = {"type": "content", "content": word}
            yield f"data: {json.dumps(chunk)}\n\n"
            
            # Small delay for streaming effect
            await asyncio.sleep(0.03)
        
        # Send done signal
        yield f"data: {json.dumps({'type': 'done'})}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


# ============================================================================
# DASHBOARD API ENDPOINTS
# ============================================================================

@app.get("/api/stats")
async def get_stats():
    """Get dashboard statistics."""
    with SessionLocal() as session:
        stats = {}
        
        # Count users
        result = session.execute(text("SELECT COUNT(*) FROM users"))
        stats["users"] = result.scalar() or 0
        
        # Count events
        result = session.execute(text("SELECT COUNT(*) FROM events"))
        stats["events"] = result.scalar() or 0
        
        # Count KB articles
        result = session.execute(text("SELECT COUNT(*) FROM kb_articles"))
        stats["kb_articles"] = result.scalar() or 0
        
        # Count venues
        result = session.execute(text("SELECT COUNT(*) FROM venues"))
        stats["venues"] = result.scalar() or 0
        
        # Count reservations
        result = session.execute(text("SELECT COUNT(*) FROM reservations"))
        stats["reservations"] = result.scalar() or 0
        
        # Count tickets
        result = session.execute(text("SELECT COUNT(*) FROM tickets"))
        stats["tickets"] = result.scalar() or 0
        
        # Count active users (with at least 1 reservation)
        result = session.execute(text("""
            SELECT COUNT(DISTINCT user_id) FROM reservations
        """))
        stats["active_users"] = result.scalar() or 0
        
        return stats


@app.get("/api/users/active")
async def get_active_users():
    """Get users sorted by activity (reservations + tickets)."""
    with SessionLocal() as session:
        # Get users with reservation and ticket counts
        result = session.execute(text("""
            SELECT 
                u.user_id,
                u.email,
                u.full_name,
                u.city,
                u.subscription_tier,
                u.created_at,
                COALESCE(r.res_count, 0) as reservation_count,
                COALESCE(t.tix_count, 0) as ticket_count
            FROM users u
            LEFT JOIN (
                SELECT user_id, COUNT(*) as res_count 
                FROM reservations 
                GROUP BY user_id
            ) r ON u.user_id = r.user_id
            LEFT JOIN (
                SELECT user_id, COUNT(*) as tix_count 
                FROM tickets 
                GROUP BY user_id
            ) t ON u.user_id = t.user_id
            ORDER BY (COALESCE(r.res_count, 0) + COALESCE(t.tix_count, 0)) DESC
            LIMIT 20
        """))
        
        users = []
        for row in result:
            users.append({
                "user_id": row[0],
                "email": row[1],
                "name": row[2],
                "city": row[3],
                "membership_tier": row[4],
                "created_at": row[5],
                "reservation_count": row[6],
                "ticket_count": row[7]
            })
        
        return users


@app.get("/api/users/{email}/details")
async def get_user_details(email: str):
    """Get full user details including reservations and tickets."""
    with SessionLocal() as session:
        # Get user
        result = session.execute(
            text("SELECT user_id, email, full_name, city, subscription_tier, created_at FROM users WHERE email = :email"),
            {"email": email}
        )
        user_row = result.fetchone()
        
        if not user_row:
            return {"error": "User not found", "user": None, "reservations": [], "tickets": []}
        
        user = {
            "user_id": user_row[0],
            "email": user_row[1],
            "name": user_row[2],
            "city": user_row[3],
            "membership_tier": user_row[4],
            "created_at": user_row[5]
        }
        
        # Get reservations (already has event_title embedded)
        result = session.execute(text("""
            SELECT 
                reservation_id,
                event_id,
                event_title,
                ticket_count,
                total_price,
                status,
                created_at
            FROM reservations
            WHERE user_id = :user_id
            ORDER BY created_at DESC
        """), {"user_id": user["user_id"]})
        
        reservations = []
        for row in result:
            reservations.append({
                "reservation_id": row[0],
                "event_id": row[1],
                "event_name": row[2],
                "num_tickets": row[3],
                "total_amount": row[4],
                "status": row[5],
                "created_at": row[6]
            })
        
        # Get tickets
        result = session.execute(text("""
            SELECT 
                ticket_id,
                subject,
                description,
                category,
                status,
                reservation_id,
                created_at
            FROM tickets
            WHERE user_id = :user_id
            ORDER BY created_at DESC
        """), {"user_id": user["user_id"]})
        
        tickets = []
        for row in result:
            tickets.append({
                "ticket_id": row[0],
                "subject": row[1],
                "description": row[2],
                "category": row[3],
                "status": row[4],
                "reservation_id": row[5],
                "created_at": row[6]
            })
        
        return {
            "user": user,
            "reservations": reservations,
            "tickets": tickets
        }


@app.get("/api/tickets/recent")
async def get_recent_tickets(limit: int = 20):
    """Get recent support tickets across all users."""
    with SessionLocal() as session:
        result = session.execute(text("""
            SELECT 
                t.ticket_id,
                t.subject,
                t.category,
                t.priority,
                t.status,
                t.created_at,
                t.user_email,
                u.full_name
            FROM tickets t
            LEFT JOIN users u ON t.user_id = u.user_id
            ORDER BY t.created_at DESC
            LIMIT :limit
        """), {"limit": limit})
        
        tickets = []
        for row in result:
            tickets.append({
                "ticket_id": row[0],
                "subject": row[1],
                "category": row[2],
                "priority": row[3],
                "status": row[4],
                "created_at": str(row[5]) if row[5] else None,
                "user_email": row[6],
                "user_name": row[7]
            })
        
        return tickets


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
