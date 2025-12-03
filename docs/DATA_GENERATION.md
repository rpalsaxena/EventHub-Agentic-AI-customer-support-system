# EventHub Data Generation Guide

This document outlines the data generation strategy for EventHub using AWS Bedrock.

---

## 1. Overview

### Purpose
Generate realistic synthetic data for the EventHub customer support AI system.

### Approach
- **Top-Down Planning**: Define domain → entities → user stories → implementation
- **Hybrid Execution**: Use LLM for creative content, Python for structured data
- **Multi-Model Support**: Configurable models (Mistral, Claude, Llama, Titan)

### Model Configuration

```python
# In config.py - switch models easily
AVAILABLE_MODELS = {
    "mistral-7b": "mistral.mistral-7b-instruct-v0:2",      # ⚡ Fast (default)
    "claude-3-haiku": "anthropic.claude-3-haiku-20240307-v1:0",
    "llama3-8b": "meta.llama3-8b-instruct-v1:0",
    "titan-express": "amazon.titan-text-express-v1",
}

ACTIVE_MODEL = "mistral-7b"  # Change this to switch models
```

---

## 2. Domain Definition

### What is EventHub?

| Aspect | Description |
|--------|-------------|
| **Product** | Customer support platform for event ticketing |
| **Model** | Subscription-based access (like CultPass) |
| **Users** | People who book tickets for events |

### Core Offering

| Feature | Description |
|---------|-------------|
| Browse events | Concerts, comedy, theater, sports, workshops |
| Book tickets | Select event, pay, get confirmation |
| Manage bookings | View, cancel, reschedule |
| Support | AI-powered customer support |

---

## 3. Data Architecture

### Two Databases

| Database | Purpose | Contents |
|----------|---------|----------|
| `eventhub.db` | Business data | Users, Events, Venues, Reservations, Subscriptions |
| `udahub.db` | Support system | Tickets, Messages, KB Articles, User History |

---

## 4. Entity Definitions

### Business Entities (`eventhub.db`)

| Entity | Fields | Description |
|--------|--------|-------------|
| **User** | id, name, email, city, is_blocked, created_at | Customer accounts |
| **Subscription** | id, user_id, tier, status, monthly_quota, started_at, ended_at | Basic/Premium plans |
| **Venue** | id, name, city, category | Event locations |
| **Event** | id, title, category, venue_id, city, description, when, slots_available, is_premium | Available events |
| **Reservation** | id, user_id, event_id, status, created_at | Bookings |

### Support Entities (`udahub.db`)

| Entity | Purpose |
|--------|---------|
| **Account** | Client account (EventHub) |
| **User** | Support user (links to business user) |
| **Ticket** | Support conversation |
| **TicketMessage** | Individual messages in conversation |
| **TicketMetadata** | Status, tags, issue type |
| **Knowledge** | KB articles for RAG |
| **UserHistory** | Past interactions |

### Subscription Tiers

| Tier | Monthly Quota | Description |
|------|---------------|-------------|
| Basic | 5 events | Lower cost plan |
| Premium | 10 events | Higher cost, priority access |

### Event Categories

| Category | Examples |
|----------|----------|
| Music | Concerts, Live bands |
| Art | Exhibitions, Galleries |
| Theater | Plays, Musicals |
| Comedy | Stand-up, Improv |
| Workshop | Classes, Seminars |

---

## 5. Data Volumes

| Entity | Count | Generation Method |
|--------|-------|-------------------|
| Users | 10,000 | Claude 3 Haiku |
| Venues | 50 | Claude 3 Haiku |
| Events | 500 | Claude 3 Haiku |
| Reservations | 50,000 | Rule-based (random user + event) |
| KB Articles | 100 | Claude 3 Haiku |
| Support Tickets | 5,000 | Claude 3 Haiku |

### Batch Sizes (per LLM call)

| Entity | Batch Size | Total Calls |
|--------|------------|-------------|
| Users | 50 | 200 |
| Venues | 10 | 5 |
| Events | 20 | 25 |
| KB Articles | 5 | 20 |
| Tickets | 25 | 200 |

---

## 6. Cost Estimation

### Claude 3 Haiku Pricing

| Metric | Cost |
|--------|------|
| Input tokens | $0.25 / 1M tokens |
| Output tokens | $1.25 / 1M tokens |

### Estimated Usage

| Data | Records | Est. Tokens | Est. Cost |
|------|---------|-------------|-----------|
| Users | 10,000 | 200K | ~$0.30 |
| Venues | 50 | 20K | ~$0.03 |
| Events | 500 | 100K | ~$0.15 |
| KB Articles | 100 | 50K | ~$0.08 |
| Support Tickets | 5,000 | 500K | ~$0.75 |
| **Total** | | | **~$1.30** |

---

## 7. Project Structure

```
eventhub/
├── data_generation/           # Data generation scripts
│   ├── __init__.py
│   ├── config.py              # Bedrock config, counts, helpers
│   ├── generate_all.py        # Master orchestrator script
│   ├── generate_users.py      # 10,000 users with subscriptions
│   ├── generate_venues.py     # 40 SF Bay Area venues
│   ├── generate_events.py     # 400 events linked to venues
│   ├── generate_reservations.py # 5,000 bookings
│   ├── generate_kb_articles.py  # 100 KB articles for RAG
│   └── generate_tickets.py    # 500 support tickets
│
├── data/
│   ├── models/
│   │   └── eventhub.py        # SQLAlchemy models
│   ├── generated/             # Output JSONLs
│   │   ├── users.jsonl
│   │   ├── events.jsonl
│   │   ├── venues.jsonl
│   │   ├── reservations.jsonl
│   │   ├── kb_articles.jsonl
│   │   └── tickets.jsonl
│   └── eventhub.db            # Final SQLite DB
│
├── docs/
│   └── DATA_GENERATION.md     # This file
│
├── agentic/                   # AI agents (later)
└── app.py                     # CLI app (later)
```

---

## 8. Configuration (`config.py`)

### Purpose

The `config.py` file serves as the **central configuration hub** for all data generation scripts. It provides:

1. **Centralized Settings** - All paths, counts, and model parameters in one place
2. **Reusable Helpers** - Common functions used by all generator scripts
3. **AWS Bedrock Integration** - Client setup and LLM invocation wrappers
4. **Consistency** - Same settings across all data generation scripts

### Overview

```
config.py
    │
    ├── PATHS ─────────────── Where files are stored
    │
    ├── DATA_COUNTS ───────── How many records to generate
    │
    ├── BEDROCK CONFIG ────── AWS model settings
    │
    ├── LLM HELPERS ───────── invoke_claude(), invoke_claude_json()
    │
    ├── FILE HELPERS ──────── save_to_jsonl(), load_from_jsonl()
    │
    └── PROGRESS HELPER ───── print_progress()
```

### Key Components

| Section | Contents |
|---------|----------|
| **Paths** | BASE_DIR, DATA_DIR, GENERATED_DIR, output files |
| **Counts** | DATA_COUNTS dictionary |
| **Bedrock Config** | AWS_REGION, MODEL_ID, MODEL_PARAMS |
| **LLM Helpers** | invoke_claude(), invoke_claude_json(), invoke_claude_json_list() |
| **File Helpers** | save_to_jsonl(), append_to_jsonl(), load_from_jsonl() |
| **Progress** | print_progress() for visual feedback |

### AWS Bedrock Settings

```python
# Available models
AVAILABLE_MODELS = {
    # Mistral (fast!)
    "mistral-7b": "mistral.mistral-7b-instruct-v0:2",        # ⚡ Default
    "mixtral-8x7b": "mistral.mixtral-8x7b-instruct-v0:1",
    
    # Anthropic Claude
    "claude-3-haiku": "anthropic.claude-3-haiku-20240307-v1:0",
    "claude-3-sonnet": "anthropic.claude-3-sonnet-20240229-v1:0",
    
    # Meta Llama
    "llama3-8b": "meta.llama3-8b-instruct-v1:0",
    "llama3-70b": "meta.llama3-70b-instruct-v1:0",
    
    # Amazon Titan (cheapest)
    "titan-lite": "amazon.titan-text-lite-v1",
    "titan-express": "amazon.titan-text-express-v1",
}

ACTIVE_MODEL = "mistral-7b"  # Change to switch models
MODEL_ID = AVAILABLE_MODELS[ACTIVE_MODEL]

MODEL_PARAMS = {
    "max_tokens": 4096,
    "temperature": 0.7,
    "top_p": 0.9,
}
```

The `invoke_model()` function auto-detects model family and uses the correct API format.

### Key Functions

| Function | Purpose |
|----------|---------|
| `get_bedrock_client()` | Create AWS Bedrock runtime client |
| `invoke_claude(prompt)` | Get raw text response from Claude |
| `invoke_claude_json(prompt)` | Parse JSON response from Claude |
| `invoke_claude_json_list(prompt)` | Parse JSON array response from Claude |
| `save_to_jsonl(data, path)` | Save list of dicts to JSONL file |
| `append_to_jsonl(data, path)` | Append to existing JSONL file |
| `load_from_jsonl(path)` | Load JSONL file to list of dicts |
| `clear_file(path)` | Clear/create empty file |
| `print_progress(current, total, entity)` | Show progress bar |

### Usage in Generator Scripts

```python
from config import (
    invoke_claude_json_list,
    save_to_jsonl,
    print_progress,
    DATA_COUNTS,
    BATCH_SIZES,
    OUTPUT_FILES,
)

# Use in any generator script
data = invoke_claude_json_list(prompt)
save_to_jsonl(data, OUTPUT_FILES["users"])
```

---

## 9. Generation Scripts

### 9.1 `generate_users.py`

#### Purpose
Generates realistic user data with subscription information using Claude 3 Haiku.

#### User Schema

| Field | Type | Description |
|-------|------|-------------|
| `user_id` | str | Unique ID (e.g., "u_a1b2c3") |
| `full_name` | str | Full name (diverse nationalities) |
| `email` | str | Email matching name |
| `city` | str | Major city worldwide |
| `is_blocked` | bool | Account blocked status (1% true) |
| `created_at` | str | ISO datetime (2022-2024) |
| `subscription_tier` | str | "basic" or "premium" |
| `subscription_status` | str | "active", "cancelled", or "paused" |
| `monthly_quota` | int | 5 (basic) or 10 (premium) |
| `subscription_started_at` | str | ISO datetime |
| `subscription_ended_at` | str/null | ISO datetime if cancelled |

#### Distribution

| Attribute | Distribution |
|-----------|--------------|
| Subscription Tier | 70% basic, 30% premium |
| Subscription Status | 90% active, 7% cancelled, 3% paused |
| Blocked Users | 1% blocked |

#### How It Works

```
1. Generate users via LLM (name, email, city, dates)
         │
         ▼
2. Assign subscription (tier, status, quota) via Python
         │
         ▼
3. Append to users.jsonl
         │
         ▼
4. Repeat until 10,000 users generated
```

#### Usage

```bash
cd eventhub/data_generation
python generate_users.py
```

#### Sample Output

```json
{
  "user_id": "u_b1001",
  "full_name": "Priya Sharma",
  "email": "priya.sharma@gmail.com",
  "city": "Mumbai",
  "is_blocked": false,
  "created_at": "2023-05-15T10:30:00",
  "subscription_tier": "premium",
  "subscription_status": "active",
  "monthly_quota": 10,
  "subscription_started_at": "2023-05-20T10:30:00",
  "subscription_ended_at": null
}
```

---

## 10. Generation Order

| Step | Script | Dependencies |
|------|--------|--------------|
| 1 | `generate_users.py` | None |
| 2 | `generate_venues.py` | None |
| 3 | `generate_events.py` | Venues |
| 4 | `generate_kb_articles.py` | None |
| 5 | `generate_reservations.py` | Users, Events |
| 6 | `generate_tickets.py` | Users, Events, Reservations |
| 7 | `generate_all.py` | Orchestrates all above |

### Dependency Graph

```
Users (independent) ──────────────────────┐
                                          ├──> Reservations ──┐
Venues (independent) ──> Events ──────────┘                   │
                                                              ├──> Tickets
KB Articles (independent) ────────────────────────────────────┘
```

---

## 10.5 SF Bay Area Location Focus

All venues and events are focused on the San Francisco Bay Area for:
- **Realism**: Interviewers may recognize real neighborhoods
- **Consistency**: Single metro area avoids timezone complexity
- **Portfolio Quality**: Shows attention to detail

### Regional Distribution

| Region | Venues | Percentage | Cities |
|--------|--------|------------|--------|
| San Francisco | 20 | 50% | SF proper |
| East Bay | 10 | 25% | Oakland, Berkeley, Emeryville |
| South Bay | 10 | 25% | San Jose, Palo Alto, Mountain View |

### Neighborhoods Used

| Region | Neighborhoods |
|--------|---------------|
| SF | SOMA, Mission, Castro, Marina, North Beach, Haight-Ashbury |
| East Bay | Downtown Oakland, Jack London Square, Uptown, Temescal |
| South Bay | Downtown San Jose, Santana Row, Willow Glen |

---

## 10. Support Scenarios

### Issue Categories

| Category | Example Issues |
|----------|----------------|
| **Booking** | "Where are my tickets?", "Wrong date selected" |
| **Refund** | "Event cancelled, want refund", "Can't attend" |
| **Technical** | "Can't login", "Payment failed", "App crashed" |
| **Event Info** | "What time does it start?", "Is parking available?" |
| **Account** | "Update email", "Delete account", "Cancel subscription" |

### Escalation Triggers

| Condition | Action |
|-----------|--------|
| Urgency = Critical | Escalate |
| Sentiment = Very Negative | Escalate |
| RAG Confidence < 0.4 | Escalate |
| Repeated failures | Escalate |

---

## 11. Running Data Generation

### Prerequisites

```bash
# AWS credentials configured
aws configure

# Required packages
pip install boto3
```

### Generate All Data (Recommended)

```bash
cd eventhub/data_generation

# Generate all data in correct dependency order
python generate_all.py

# Test mode (small datasets for quick testing)
python generate_all.py --test

# Rewrite mode (clear and regenerate all data)
python generate_all.py --rewrite

# Skip specific generators
python generate_all.py --skip users venues
```

### Generate Individual Entities

```bash
# Independent generators (can run in any order)
python generate_users.py [--test] [--rewrite]
python generate_venues.py [--test] [--rewrite]
python generate_kb_articles.py [--test] [--rewrite]

# Dependent generators (require prior data)
python generate_events.py [--test] [--rewrite]      # Requires venues
python generate_reservations.py [--test] [--rewrite] # Requires users + events
python generate_tickets.py [--test] [--rewrite]     # Requires users + events + reservations
```

### Command Line Flags

| Flag | Description |
|------|-------------|
| `--test` | Generate small dataset for quick testing |
| `--rewrite` | Clear existing data and regenerate |
| (none) | Append to existing data (default) |

---

## 12. Output Format

### JSONL Files

Each entity is stored as one JSON object per line:

```jsonl
{"user_id": "u001", "full_name": "Alice Smith", "email": "alice@example.com", ...}
{"user_id": "u002", "full_name": "Bob Johnson", "email": "bob@example.com", ...}
```

### Final Database

SQLite database created from JSONL files:
- `eventhub.db` - Business data
- `udahub.db` - Support data (reused from starter)

---

## 13. Next Steps

After data generation:

1. **Create SQLAlchemy Models** - `data/models/eventhub.py`
2. **Build Tools** - db_tools, rag_tools, memory_tools
3. **Build Agents** - classifier, resolver, escalation
4. **Build Workflow** - LangGraph StateGraph
5. **Build CLI** - app.py

---

## 14. Generator Details & Edge Cases

### 14.1 `generate_users.py` - User Accounts

#### Generation Method
**Hybrid**: LLM generates names/emails, Python generates IDs/dates/subscriptions

#### Schema

| Field | Type | Generated By | Description |
|-------|------|--------------|-------------|
| `user_id` | str | Python | Sequential ID (e.g., "u_00001") |
| `full_name` | str | LLM | Diverse names |
| `email` | str | LLM | Matching email |
| `phone` | str | LLM | Phone number |
| `subscription_tier` | str | Python | "basic" (70%) / "premium" (30%) |
| `subscription_status` | str | Python | "active" / "cancelled" / "paused" |
| `joined_at` | str | Python | Relative date (last 2 years) |
| `subscription_started_at` | str | Python | After joined_at |
| `subscription_ended_at` | str/null | Python | Only if cancelled/paused |
| `is_blocked` | bool | Python | 1% blocked |

#### Edge Cases Handled

| Edge Case | Problem | Solution |
|-----------|---------|----------|
| Duplicate IDs | LLM might repeat IDs | Python sequential generator |
| Future dates | Hardcoded years become outdated | Relative dates from `datetime.now()` |
| `ended_at` before `started_at` | Invalid temporal logic | Force to `active` if not enough time passed |
| `ended_at` in future | Invalid cancellation | Cap to today's date |

#### Distribution

```
Subscription Tier:   70% basic, 30% premium
Subscription Status: 90% active, 7% cancelled, 3% paused
Blocked Users:       1%
```

---

### 14.2 `generate_venues.py` - SF Bay Area Venues

#### Generation Method
**Hybrid**: LLM generates names/addresses, Python generates IDs/capacity

#### Schema

| Field | Type | Generated By | Description |
|-------|------|--------------|-------------|
| `venue_id` | str | Python | Sequential ID (e.g., "v_00001") |
| `name` | str | LLM | Creative venue name |
| `address` | str | LLM | Realistic SF address |
| `neighborhood` | str | LLM | Real SF neighborhood |
| `city` | str | LLM | SF Bay Area cities only |
| `state` | str | Python | "California" |
| `capacity` | int | Python | Based on category |
| `category` | str | LLM | music/theater/comedy/art/sports |

#### Regional Distribution

| Region | Count | Cities |
|--------|-------|--------|
| San Francisco | 20 (50%) | SF proper |
| East Bay | 10 (25%) | Oakland, Berkeley, Emeryville |
| South Bay | 10 (25%) | San Jose, Palo Alto, Mountain View |

#### Capacity by Category

| Category | Capacity Range |
|----------|---------------|
| Music | 200 - 3,000 |
| Theater | 300 - 2,000 |
| Comedy | 100 - 500 |
| Art | 50 - 300 |
| Sports | 5,000 - 20,000 |
| Conference | 200 - 1,500 |

---

### 14.3 `generate_events.py` - Events at Venues

#### Generation Method
**Hybrid**: LLM generates titles/descriptions, Python generates dates/pricing

#### Schema

| Field | Type | Generated By | Description |
|-------|------|--------------|-------------|
| `event_id` | str | Python | Sequential ID (e.g., "e_00001") |
| `title` | str | LLM | Creative event title |
| `description` | str | LLM | 2-3 sentence description |
| `venue_id` | str | Python | From venues.jsonl |
| `venue_name` | str | Python | Denormalized |
| `city` | str | Python | From venue |
| `category` | str | Python | Matches venue category |
| `event_date` | str | Python | Future date (next 6 months) |
| `start_time` | str | Python | Realistic time |
| `duration_minutes` | int | Python | By category |
| `price_min` | float | Python | By category |
| `price_max` | float | Python | By category |
| `total_tickets` | int | Python | Based on venue capacity |
| `tickets_sold` | int | Python | By status |
| `is_premium` | bool | Python | 30% premium |
| `status` | str | Python | 70% active, 20% soldout, 10% cancelled |

#### Edge Cases Handled

| Edge Case | Solution |
|-----------|----------|
| Event without venue | Load venues.jsonl first, validate |
| Invalid venue_id | Only use IDs from existing venues |
| Capacity mismatch | total_tickets ≤ venue.capacity |

---

### 14.4 `generate_reservations.py` - Ticket Bookings

#### Generation Method
**100% Python** - No LLM needed! Just links existing users to events.

#### Schema

| Field | Type | Description |
|-------|------|-------------|
| `reservation_id` | str | Sequential ID (e.g., "r_00001") |
| `user_id` | str | From users.jsonl |
| `user_email` | str | Denormalized |
| `event_id` | str | From events.jsonl |
| `event_title` | str | Denormalized |
| `venue_id` | str | From event |
| `venue_name` | str | Denormalized |
| `event_date` | str | From event |
| `ticket_count` | int | 1-6 tickets |
| `total_price` | float | Calculated with discounts |
| `status` | str | 85% confirmed, 10% cancelled, 5% pending |
| `booking_date` | str | Before event date |
| `payment_method` | str | credit_card/paypal/apple_pay/google_pay |
| `is_premium_booking` | bool | Premium user discount applied |

#### Edge Cases Handled (Critical!)

| Edge Case | Problem | Solution |
|-----------|---------|----------|
| **Duplicate booking** | Same user books same event twice | Track `(user_id, event_id)` pairs in `booked_pairs` set |
| **Capacity exceeded** | More tickets sold than venue holds | Track `event_tickets_sold[event_id]` counter |
| **Premium event + Basic user** | Basic user books premium-only event | Validate `user.tier == "premium"` for premium events |
| **Blocked user** | Blocked user has active booking | Force all blocked user reservations to `status: "cancelled"` |
| **Booking after event** | booking_date > event_date | Ensure `booking_date < event_date` |
| **Booking before subscription** | User books before subscribing | Ensure `booking_date >= subscription_started_at` |
| **Cancelled event** | Booking for cancelled event | Filter out `status: "cancelled"` events before selection |

#### Tracking State

```python
# Prevent duplicate bookings
booked_pairs: set = set()  # {(user_id, event_id), ...}

# Prevent overselling
event_tickets_sold: dict = defaultdict(int)  # {event_id: count}
```

#### User Pool Distribution

```
80% - Active users (premium + basic)
15% - Inactive users (cancelled/paused subscriptions)
5%  - Blocked users (all reservations cancelled)
```

---

### 14.5 `generate_kb_articles.py` - Knowledge Base for RAG

#### Generation Method
**Hybrid**: LLM generates content, Python generates metadata

#### Schema

| Field | Type | Generated By | Description |
|-------|------|--------------|-------------|
| `article_id` | str | Python | Sequential ID (e.g., "kb_00001") |
| `title` | str | LLM | Searchable title |
| `content` | str | LLM | 3-5 paragraphs |
| `category` | str | Python | policy/how-to/faq/troubleshooting |
| `tags` | list | LLM | 3-5 keywords |
| `last_updated` | str | Python | Recent date |
| `is_published` | bool | Python | Always true |
| `view_count` | int | Python | Random 50-5000 |
| `helpful_votes` | int | Python | Random 10-500 |

#### Category Distribution

| Category | % | Topics |
|----------|---|--------|
| policy | 25% | Refund policy, cancellation, terms |
| how-to | 30% | Step-by-step guides |
| faq | 25% | Common questions |
| troubleshooting | 20% | Technical issues |

---

### 14.6 `generate_tickets.py` - Support Tickets

#### Generation Method
**Hybrid**: LLM generates subject/description, Python generates metadata + links

#### Schema

| Field | Type | Generated By | Description |
|-------|------|--------------|-------------|
| `ticket_id` | str | Python | Sequential ID (e.g., "t_00001") |
| `user_id` | str | Python | From users.jsonl |
| `user_email` | str | Python | Denormalized |
| `category` | str | Python | refund/cancellation/technical/general/complaint |
| `subject` | str | LLM | Brief subject line |
| `description` | str | LLM | Customer message |
| `reservation_id` | str/null | Python | Linked reservation (if applicable) |
| `event_id` | str/null | Python | Related event |
| `event_title` | str/null | Python | Denormalized |
| `status` | str | Python | open/in_progress/resolved/escalated |
| `priority` | str | Python | low/medium/high/urgent |
| `created_at` | str | Python | Last 30 days |
| `resolved_at` | str/null | Python | If resolved |
| `agent_notes` | str/null | Python | Internal notes |

#### Edge Cases Handled

| Edge Case | Problem | Solution |
|-----------|---------|----------|
| **Ticket references wrong user's reservation** | Ticket user ≠ reservation user | Only link if `ticket.user_id == reservation.user_id` |
| **Refund ticket for user without bookings** | User has no reservations | Prefer users WITH reservations for refund/cancellation tickets |
| **Event mismatch** | Ticket mentions event user didn't book | Get event from user's actual reservation |

#### Category Distribution

| Category | % | Priority Chance |
|----------|---|-----------------|
| refund | 40% | 30% high/urgent |
| cancellation | 25% | 20% high/urgent |
| technical | 15% | 40% high/urgent |
| general | 10% | 5% high/urgent |
| complaint | 10% | 60% high/urgent |

---

## 15. Data Integrity Guarantees

### Foreign Key Relationships

All relationships are validated at generation time:

```
reservations.user_id    → EXISTS in users.jsonl
reservations.event_id   → EXISTS in events.jsonl
reservations.venue_id   → EXISTS in venues.jsonl
events.venue_id         → EXISTS in venues.jsonl
tickets.user_id         → EXISTS in users.jsonl
tickets.reservation_id  → EXISTS in reservations.jsonl (if linked)
tickets.event_id        → EXISTS in events.jsonl (if linked)
```

### SQL Join Safety

```sql
-- All these JOINs will return 100% matches (no NULLs from missing FKs)

SELECT r.*, u.full_name 
FROM reservations r 
JOIN users u ON r.user_id = u.user_id;  -- ✅ Always matches

SELECT r.*, e.title, v.name 
FROM reservations r 
JOIN events e ON r.event_id = e.event_id
JOIN venues v ON e.venue_id = v.venue_id;  -- ✅ Always matches

SELECT t.*, r.event_title 
FROM tickets t 
LEFT JOIN reservations r ON t.reservation_id = r.reservation_id
WHERE t.user_id = r.user_id OR r.user_id IS NULL;  -- ✅ Consistent linking
```

---

## 16. Performance Insights

### LLM vs Python Generation

| Generator | Method | Speed | Cost |
|-----------|--------|-------|------|
| `generate_users.py` | Hybrid (LLM + Python) | Slow | $$ |
| `generate_venues.py` | Hybrid (LLM + Python) | Medium | $ |
| `generate_events.py` | Hybrid (LLM + Python) | Medium | $ |
| `generate_reservations.py` | **100% Python** | ⚡ Instant | Free |
| `generate_kb_articles.py` | Hybrid (LLM + Python) | Medium | $ |
| `generate_tickets.py` | Hybrid (LLM + Python) | Slow | $$ |

### Model Speed Comparison

| Model | Speed | Quality | Cost |
|-------|-------|---------|------|
| `mistral-7b` | ⚡⚡⚡ Very Fast | Good | $ |
| `claude-3-haiku` | ⚡⚡ Fast | Very Good | $$ |
| `llama3-8b` | ⚡⚡ Fast | Good | $ |
| `titan-express` | ⚡⚡⚡ Very Fast | Decent | $ |

---

## 17. Lessons Learned

### Key Insights

| Insight | Explanation |
|---------|-------------|
| **Don't trust LLM for IDs** | Use Python sequential generators |
| **Relative dates** | Use `datetime.now()` instead of hardcoded years |
| **Validate temporal logic** | end_date > start_date, booking < event |
| **Track state for constraints** | Sets for uniqueness, dicts for capacity |
| **Load dependencies first** | Check file exists before using foreign keys |
| **Python-only when possible** | Reservations need no LLM (instant generation) |
| **Denormalize for convenience** | Include `user_email`, `event_title` in reservations |

### What Could Go Wrong

| Problem | Symptom | Prevention |
|---------|---------|------------|
| Missing dependency | `FileNotFoundError` | Check `file.exists()` with clear error message |
| Infinite loop | Script hangs | `max_attempts` counter |
| Memory overflow | OOM on large datasets | Batch + append pattern |
| Inconsistent state | Resume generates duplicates | Rebuild tracking state from existing file |
