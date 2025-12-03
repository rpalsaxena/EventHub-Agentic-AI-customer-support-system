# EventHub Agent Tools

This directory contains reusable tools for the EventHub agentic support system.

## 📁 Structure

```
tools/
├── __init__.py          # Tool exports
├── rag_tools.py         # Knowledge base semantic search
└── db_tools.py          # Database query tools
```

## 🔧 Available Tools

### RAG Tools (Knowledge Base Search)

#### `search_knowledge_base(query, top_k=3)`
Semantic search over KB articles using Cohere embeddings + ChromaDB.

**Parameters:**
- `query` (str): User's question or search query
- `top_k` (int): Number of results to return (default: 3)

**Returns:**
- List of relevant articles with title, content, category, and relevance score

**Example:**
```python
from agentic.tools import search_knowledge_base

results = search_knowledge_base.invoke({
    "query": "How do I cancel my reservation?",
    "top_k": 3
})

for article in results:
    print(f"{article['title']}: {article['relevance_score']:.1%}")
```

---

### Database Tools

#### `get_user_info(user_id=None, email=None)`
Retrieve user account details and subscription information.

**Example:**
```python
from agentic.tools import get_user_info

user = get_user_info.invoke({"email": "john@example.com"})
print(f"Tier: {user['subscription']['tier']}")
```

#### `get_reservation_info(reservation_id)`
Get detailed reservation information including event details.

**Example:**
```python
reservation = get_reservation_info.invoke({"reservation_id": "r_00123"})
print(f"Event: {reservation['event_title']}")
print(f"Status: {reservation['status']}")
```

#### `search_events(category, city, date_from, date_to, is_premium, limit)`
Search for events with flexible filters.

**Parameters:**
- `category` (str, optional): Event category (Music, Sports, Arts, etc.)
- `city` (str, optional): City name
- `date_from` (str, optional): Start date (YYYY-MM-DD)
- `date_to` (str, optional): End date (YYYY-MM-DD)
- `is_premium` (bool, optional): Filter premium events
- `limit` (int): Max results (default: 10)

**Example:**
```python
events = search_events.invoke({
    "category": "Music",
    "city": "Mumbai",
    "limit": 5
})
```

#### `cancel_reservation(reservation_id, reason)`
Cancel a user's reservation and update status.

**Example:**
```python
result = cancel_reservation.invoke({
    "reservation_id": "r_00123",
    "reason": "User requested cancellation"
})
print(result["message"])
```

#### `get_user_reservations(user_id, status=None, limit=10)`
Get all reservations for a specific user.

**Example:**
```python
reservations = get_user_reservations.invoke({
    "user_id": "u_00001",
    "status": "confirmed"
})
```

#### `get_user_tickets(user_id, status=None, limit=10)`
Get support tickets for a user.

**Example:**
```python
tickets = get_user_tickets.invoke({
    "user_id": "u_00001",
    "status": "open"
})
```

---

## 🚀 Usage in Agents

All tools are LangChain-compatible and can be bound to agents:

```python
from langchain_aws import ChatBedrock
from agentic.tools import (
    search_knowledge_base,
    get_user_info,
    search_events,
    cancel_reservation,
)

# Initialize Llama model
llm = ChatBedrock(
    model_id="meta.llama3-3-70b-instruct-v1:0",
    region_name="us-east-1"
)

# Bind tools to agent
agent_tools = [
    search_knowledge_base,
    get_user_info,
    search_events,
    cancel_reservation,
]

llm_with_tools = llm.bind_tools(agent_tools)
```

---

## 🔑 Configuration

### Environment Variables

Create a `.env` file with:

```env
# AWS Bedrock (for Llama models and Cohere embeddings)
AWS_ACCESS_KEY_ID=your_aws_key
AWS_SECRET_ACCESS_KEY=your_aws_secret
AWS_DEFAULT_REGION=us-east-1
```

### ChromaDB Setup

Before using RAG tools, run the setup script:

```bash
cd eventhub
python agentic/rag_setup.py
```

This will:
1. Load KB articles from database
2. Generate Cohere embeddings
3. Store in ChromaDB with ANN indexing (HNSW)
4. Enable semantic search

---

## 📊 Technical Details

### RAG Configuration

- **Embedding Model:** Cohere `embed-english-v3` via AWS Bedrock (1024 dimensions)
- **Vector DB:** ChromaDB (persistent)
- **Indexing:** HNSW (Hierarchical Navigable Small World)
- **Distance Metric:** Cosine similarity
- **ANN Parameters:**
  - `construction_ef`: 200 (build quality)
  - `M`: 16 (connections per layer)

### Database Configuration

- **Database:** SQLite (`data/db/eventhub.db`)
- **ORM:** SQLAlchemy
- **Tables:** users, events, venues, reservations, tickets, kb_articles

---

## 🧪 Testing

Run the test notebook:

```bash
jupyter notebook eventhub/02_rag_test.ipynb
```

Or test individual tools:

```python
# Test RAG search
from agentic.tools import search_knowledge_base

results = search_knowledge_base.invoke({
    "query": "refund policy",
    "top_k": 3
})

for article in results:
    print(f"{article['title']}: {article['relevance_score']:.0%}")
```

---

## 📝 Notes

- All tools use LangChain's `@tool` decorator for automatic schema generation
- Tools return structured dictionaries for easy parsing
- Error handling included (e.g., user not found, invalid dates)
- Tools are stateless and can be used concurrently

---

## 🔗 Related Files

- `eventhub/agentic/rag_setup.py` - RAG initialization script
- `eventhub/02_rag_test.ipynb` - Comprehensive testing notebook
- `eventhub/data/models/eventhub.py` - SQLAlchemy models
- `eventhub/utils.py` - Database utilities
