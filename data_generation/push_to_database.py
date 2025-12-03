"""
Push Generated Data to SQLite Database

This script loads all JSONL data files and populates a single EventHub database.
Database: eventhub.db

Tables:
- users: Customer information
- venues: Event venue details  
- events: Event listings
- reservations: User event bookings
- tickets: Support tickets
- kb_articles: Knowledge base articles
- conversations: Agent conversation history (empty, populated at runtime)
- escalations: Escalated tickets (empty, populated at runtime)
"""

import json
import sqlite3
from pathlib import Path
from datetime import datetime

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "generated"
DB_DIR = PROJECT_ROOT / "data" / "db"


def load_jsonl(filepath: Path) -> list[dict]:
    """Load data from a JSONL file."""
    data = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                data.append(json.loads(line))
    return data


def create_eventhub_db(db_path: Path):
    """Create and populate the EventHub database."""
    print(f"\n{'='*60}")
    print("Creating EventHub Database (eventhub.db)")
    print(f"{'='*60}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # ========== USERS TABLE ==========
    # Matches: user_id, full_name, email, city, is_blocked, created_at,
    #          subscription_tier, subscription_status, monthly_quota,
    #          subscription_started_at, subscription_ended_at
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            full_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            city TEXT,
            is_blocked INTEGER DEFAULT 0,
            created_at TEXT,
            subscription_tier TEXT DEFAULT 'basic',
            subscription_status TEXT DEFAULT 'active',
            monthly_quota INTEGER DEFAULT 5,
            subscription_started_at TEXT,
            subscription_ended_at TEXT
        )
    """)
    
    # ========== VENUES TABLE ==========
    # Matches: venue_id, name, address, neighborhood, city, state, capacity, category
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS venues (
            venue_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            address TEXT,
            neighborhood TEXT,
            city TEXT,
            state TEXT,
            capacity INTEGER,
            category TEXT
        )
    """)
    
    # ========== EVENTS TABLE ==========
    # Matches: event_id, title, description, venue_id, venue_name, city, neighborhood,
    #          category, event_date, start_time, duration_minutes, price_min, price_max,
    #          total_tickets, tickets_sold, is_premium, status
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            event_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            venue_id TEXT,
            venue_name TEXT,
            city TEXT,
            neighborhood TEXT,
            category TEXT,
            event_date TEXT,
            start_time TEXT,
            duration_minutes INTEGER,
            price_min REAL,
            price_max REAL,
            total_tickets INTEGER,
            tickets_sold INTEGER DEFAULT 0,
            is_premium INTEGER DEFAULT 0,
            status TEXT DEFAULT 'active',
            FOREIGN KEY (venue_id) REFERENCES venues(venue_id)
        )
    """)
    
    # ========== RESERVATIONS TABLE ==========
    # Matches: reservation_id, user_id, user_email, event_id, event_title,
    #          venue_id, venue_name, event_date, ticket_count, total_price,
    #          status, booking_date, payment_method, is_premium_booking
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reservations (
            reservation_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            user_email TEXT,
            event_id TEXT NOT NULL,
            event_title TEXT,
            venue_id TEXT,
            venue_name TEXT,
            event_date TEXT,
            ticket_count INTEGER DEFAULT 1,
            total_price REAL,
            status TEXT DEFAULT 'confirmed',
            booking_date TEXT,
            payment_method TEXT,
            is_premium_booking INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (event_id) REFERENCES events(event_id),
            FOREIGN KEY (venue_id) REFERENCES venues(venue_id)
        )
    """)
    
    # ========== TICKETS (Support Tickets) TABLE ==========
    # Matches: ticket_id, user_id, user_email, category, subject, description,
    #          status, priority, created_at, resolved_at, agent_notes,
    #          event_id, event_title, reservation_id
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            ticket_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            user_email TEXT,
            category TEXT,
            subject TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'open',
            priority TEXT DEFAULT 'medium',
            created_at TEXT,
            resolved_at TEXT,
            agent_notes TEXT,
            event_id TEXT,
            event_title TEXT,
            reservation_id TEXT,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (event_id) REFERENCES events(event_id),
            FOREIGN KEY (reservation_id) REFERENCES reservations(reservation_id)
        )
    """)
    
    # ========== KB_ARTICLES TABLE ==========
    # Matches: article_id, title, content, category, tags, last_updated,
    #          is_published, view_count, helpful_votes
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS kb_articles (
            article_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            category TEXT,
            tags TEXT,
            last_updated TEXT,
            is_published INTEGER DEFAULT 1,
            view_count INTEGER DEFAULT 0,
            helpful_votes INTEGER DEFAULT 0
        )
    """)
    
    # ========== CONVERSATIONS TABLE (for agent memory) ==========
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            thread_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            ticket_id TEXT,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            agent_type TEXT,
            metadata TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (ticket_id) REFERENCES tickets(ticket_id)
        )
    """)
    
    # ========== ESCALATIONS TABLE ==========
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS escalations (
            escalation_id TEXT PRIMARY KEY,
            ticket_id TEXT NOT NULL,
            thread_id TEXT,
            reason TEXT NOT NULL,
            priority TEXT DEFAULT 'high',
            summary TEXT,
            recommended_actions TEXT,
            assigned_to TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            resolved_at TEXT,
            resolution_notes TEXT,
            FOREIGN KEY (ticket_id) REFERENCES tickets(ticket_id)
        )
    """)
    
    # ========== INDEXES ==========
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_tier ON users(subscription_tier)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_status ON users(subscription_status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_city ON users(city)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_venues_city ON venues(city)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_venues_category ON venues(category)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_venue ON events(venue_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_date ON events(event_date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_category ON events(category)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_status ON events(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_reservations_user ON reservations(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_reservations_event ON reservations(event_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_reservations_status ON reservations(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tickets_user ON tickets(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tickets_category ON tickets(category)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tickets_priority ON tickets(priority)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_kb_category ON kb_articles(category)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_conversations_thread ON conversations(thread_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_escalations_ticket ON escalations(ticket_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_escalations_status ON escalations(status)")
    
    conn.commit()
    
    # ========== LOAD DATA ==========
    
    # Load Users
    print("\n📥 Loading users...")
    users = load_jsonl(DATA_DIR / "users.jsonl")
    for user in users:
        cursor.execute("""
            INSERT OR REPLACE INTO users 
            (user_id, full_name, email, city, is_blocked, created_at,
             subscription_tier, subscription_status, monthly_quota,
             subscription_started_at, subscription_ended_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user["user_id"],
            user["full_name"],
            user["email"],
            user.get("city"),
            1 if user.get("is_blocked") else 0,
            user.get("created_at"),
            user.get("subscription_tier", "basic"),
            user.get("subscription_status", "active"),
            user.get("monthly_quota", 5),
            user.get("subscription_started_at"),
            user.get("subscription_ended_at")
        ))
    print(f"   ✅ Loaded {len(users):,} users")
    
    # Load Venues
    print("\n📥 Loading venues...")
    venues = load_jsonl(DATA_DIR / "venues.jsonl")
    for venue in venues:
        cursor.execute("""
            INSERT OR REPLACE INTO venues 
            (venue_id, name, address, neighborhood, city, state, capacity, category)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            venue["venue_id"],
            venue["name"],
            venue.get("address"),
            venue.get("neighborhood"),
            venue.get("city"),
            venue.get("state"),
            venue.get("capacity"),
            venue.get("category")
        ))
    print(f"   ✅ Loaded {len(venues):,} venues")
    
    # Load Events
    print("\n📥 Loading events...")
    events = load_jsonl(DATA_DIR / "events.jsonl")
    for event in events:
        cursor.execute("""
            INSERT OR REPLACE INTO events 
            (event_id, title, description, venue_id, venue_name, city, neighborhood,
             category, event_date, start_time, duration_minutes, price_min, price_max,
             total_tickets, tickets_sold, is_premium, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event["event_id"],
            event["title"],
            event.get("description"),
            event.get("venue_id"),
            event.get("venue_name"),
            event.get("city"),
            event.get("neighborhood"),
            event.get("category"),
            event.get("event_date"),
            event.get("start_time"),
            event.get("duration_minutes"),
            event.get("price_min"),
            event.get("price_max"),
            event.get("total_tickets"),
            event.get("tickets_sold", 0),
            1 if event.get("is_premium") else 0,
            event.get("status", "active")
        ))
    print(f"   ✅ Loaded {len(events):,} events")
    
    # Load Reservations
    print("\n📥 Loading reservations...")
    reservations = load_jsonl(DATA_DIR / "reservations.jsonl")
    for res in reservations:
        cursor.execute("""
            INSERT OR REPLACE INTO reservations 
            (reservation_id, user_id, user_email, event_id, event_title,
             venue_id, venue_name, event_date, ticket_count, total_price,
             status, booking_date, payment_method, is_premium_booking)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            res["reservation_id"],
            res["user_id"],
            res.get("user_email"),
            res["event_id"],
            res.get("event_title"),
            res.get("venue_id"),
            res.get("venue_name"),
            res.get("event_date"),
            res.get("ticket_count", 1),
            res.get("total_price"),
            res.get("status", "confirmed"),
            res.get("booking_date"),
            res.get("payment_method"),
            1 if res.get("is_premium_booking") else 0
        ))
    print(f"   ✅ Loaded {len(reservations):,} reservations")
    
    # Load Support Tickets
    print("\n📥 Loading support tickets...")
    tickets = load_jsonl(DATA_DIR / "tickets.jsonl")
    for ticket in tickets:
        cursor.execute("""
            INSERT OR REPLACE INTO tickets 
            (ticket_id, user_id, user_email, category, subject, description,
             status, priority, created_at, resolved_at, agent_notes,
             event_id, event_title, reservation_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ticket["ticket_id"],
            ticket["user_id"],
            ticket.get("user_email"),
            ticket.get("category"),
            ticket["subject"],
            ticket.get("description"),
            ticket.get("status", "open"),
            ticket.get("priority", "medium"),
            ticket.get("created_at"),
            ticket.get("resolved_at"),
            ticket.get("agent_notes"),
            ticket.get("event_id"),
            ticket.get("event_title"),
            ticket.get("reservation_id")
        ))
    print(f"   ✅ Loaded {len(tickets):,} support tickets")
    
    # Load Knowledge Base Articles
    print("\n📥 Loading knowledge base articles...")
    articles = load_jsonl(DATA_DIR / "kb_articles.jsonl")
    for article in articles:
        cursor.execute("""
            INSERT OR REPLACE INTO kb_articles 
            (article_id, title, content, category, tags, last_updated,
             is_published, view_count, helpful_votes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            article["article_id"],
            article["title"],
            article["content"],
            article.get("category"),
            json.dumps(article.get("tags", [])),
            article.get("last_updated"),
            1 if article.get("is_published", True) else 0,
            article.get("view_count", 0),
            article.get("helpful_votes", 0)
        ))
    print(f"   ✅ Loaded {len(articles):,} knowledge base articles")
    
    conn.commit()
    conn.close()
    
    print(f"\n✅ EventHub database created at: {db_path}")


def verify_database(db_path: Path):
    """Verify the database was created correctly and display statistics."""
    print(f"\n{'='*60}")
    print("Database Verification & Statistics")
    print(f"{'='*60}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Table counts
    print("\n📊 Table Record Counts:")
    tables = ["users", "venues", "events", "reservations", "tickets", 
              "kb_articles", "conversations", "escalations"]
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"   • {table}: {count:,} records")
    
    # User statistics
    print("\n👥 User Statistics:")
    cursor.execute("""
        SELECT subscription_tier, COUNT(*) as count
        FROM users
        GROUP BY subscription_tier
        ORDER BY count DESC
    """)
    for row in cursor.fetchall():
        print(f"   • {row[0]}: {row[1]:,} users")
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE is_blocked = 1")
    blocked = cursor.fetchone()[0]
    print(f"   • Blocked users: {blocked:,}")
    
    # Event statistics
    print("\n🎭 Event Statistics:")
    cursor.execute("""
        SELECT status, COUNT(*) as count
        FROM events
        GROUP BY status
        ORDER BY count DESC
    """)
    for row in cursor.fetchall():
        print(f"   • {row[0]}: {row[1]:,} events")
    
    # Reservation statistics
    print("\n🎟️ Reservation Statistics:")
    cursor.execute("""
        SELECT status, COUNT(*) as count
        FROM reservations
        GROUP BY status
        ORDER BY count DESC
    """)
    for row in cursor.fetchall():
        print(f"   • {row[0]}: {row[1]:,} reservations")
    
    cursor.execute("SELECT SUM(total_price) FROM reservations WHERE status = 'confirmed'")
    total_revenue = cursor.fetchone()[0] or 0
    print(f"   • Total confirmed revenue: ${total_revenue:,.2f}")
    
    # Support ticket statistics
    print("\n🎫 Support Ticket Statistics:")
    cursor.execute("""
        SELECT status, COUNT(*) as count
        FROM tickets
        GROUP BY status
        ORDER BY count DESC
    """)
    for row in cursor.fetchall():
        print(f"   • {row[0]}: {row[1]:,} tickets")
    
    cursor.execute("""
        SELECT category, COUNT(*) as count
        FROM tickets
        GROUP BY category
        ORDER BY count DESC
    """)
    print("\n   By category:")
    for row in cursor.fetchall():
        print(f"   • {row[0]}: {row[1]:,} tickets")
    
    cursor.execute("""
        SELECT priority, COUNT(*) as count
        FROM tickets
        GROUP BY priority
        ORDER BY 
            CASE priority 
                WHEN 'urgent' THEN 1 
                WHEN 'high' THEN 2 
                WHEN 'medium' THEN 3 
                WHEN 'low' THEN 4 
            END
    """)
    print("\n   By priority:")
    for row in cursor.fetchall():
        print(f"   • {row[0]}: {row[1]:,} tickets")
    
    # Top events by reservations
    print("\n🏆 Top 5 Events by Reservations:")
    cursor.execute("""
        SELECT e.title, COUNT(r.reservation_id) as bookings
        FROM events e
        LEFT JOIN reservations r ON e.event_id = r.event_id
        GROUP BY e.event_id
        HAVING bookings > 0
        ORDER BY bookings DESC
        LIMIT 5
    """)
    for row in cursor.fetchall():
        title = row[0][:45] + "..." if len(row[0]) > 45 else row[0]
        print(f"   • {title}: {row[1]} bookings")
    
    conn.close()


def main():
    """Main function to create and populate the database."""
    print("\n" + "="*60)
    print("   EVENTHUB DATABASE INITIALIZATION")
    print("   Pushing generated data to SQLite database")
    print("="*60)
    
    # Ensure db directory exists
    DB_DIR.mkdir(parents=True, exist_ok=True)
    
    # Database path - single database
    db_path = DB_DIR / "eventhub.db"
    
    # Remove existing database for clean start
    if db_path.exists():
        db_path.unlink()
        print(f"\n🗑️  Removed existing {db_path.name}")
    
    # Create and populate database
    create_eventhub_db(db_path)
    
    # Verify and show statistics
    verify_database(db_path)
    
    print("\n" + "="*60)
    print("   ✅ DATABASE INITIALIZATION COMPLETE!")
    print("="*60)
    print(f"\n   📁 Database created: {db_path}")
    print(f"   📊 Tables: users, venues, events, reservations,")
    print(f"             tickets, kb_articles, conversations, escalations")
    print("\n")


if __name__ == "__main__":
    main()