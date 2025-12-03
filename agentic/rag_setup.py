"""
RAG Setup for EventHub Knowledge Base

This script:
1. Loads all KB articles from the database
2. Generates embeddings using Cohere embed-english-v3.0
3. Stores vectors in ChromaDB with ANN indexing (HNSW)
4. Enables semantic search for agent tool use

Run this script once to initialize the vector database.
Re-run if KB articles are updated.
"""

import os
import sys
from pathlib import Path
from sqlalchemy import create_engine
from langchain_aws import BedrockEmbeddings
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import get_session
from data.models.eventhub import KBArticle


# Configuration
DB_PATH = "data/db/eventhub.db"
CHROMA_DB_PATH = "data/vectordb"
COLLECTION_NAME = "kb_articles"


def setup_chromadb():
    """Initialize ChromaDB with persistent storage and ANN configuration."""
    # Create directory if it doesn't exist
    os.makedirs(CHROMA_DB_PATH, exist_ok=True)
    
    # Create persistent client
    client = chromadb.PersistentClient(
        path=CHROMA_DB_PATH,
        settings=Settings(
            anonymized_telemetry=False,
            allow_reset=True,
        )
    )
    
    print(f"✅ ChromaDB initialized at: {CHROMA_DB_PATH}")
    return client


def load_kb_articles():
    """Load all published KB articles from the database."""
    engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
    
    with get_session(engine) as session:
        articles = session.query(KBArticle).filter(
            KBArticle.is_published == True
        ).all()
        
        print(f"📚 Loaded {len(articles)} KB articles from database")
        
        # Convert to list of dicts with all fields
        article_data = []
        for article in articles:
            article_data.append({
                "article_id": article.article_id,
                "title": article.title,
                "content": article.content,
                "category": article.category,
                "tags": article.tags,
                "last_updated": str(article.last_updated) if article.last_updated else None,
                "view_count": article.view_count,
                "helpful_votes": article.helpful_votes,
            })
        
        return article_data


def create_embeddings_and_store(articles):
    """
    Generate Cohere embeddings via AWS Bedrock and store in ChromaDB with ANN indexing.
    
    Args:
        articles: List of article dictionaries
    """
    # Initialize Cohere embeddings via Bedrock
    aws_region = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
    
    bedrock_embeddings = BedrockEmbeddings(
        model_id="cohere.embed-english-v3",  # Cohere embedding via Bedrock (1024 dimensions)
        region_name=aws_region,
    )
    
    # Wrap in ChromaDB's embedding function interface
    class BedrockEmbeddingFunction(embedding_functions.EmbeddingFunction):
        def __call__(self, input: list[str]) -> list[list[float]]:
            return bedrock_embeddings.embed_documents(input)
    
    embedding_function = BedrockEmbeddingFunction()
    
    print(f"🔑 Using Cohere embed-english-v3 via AWS Bedrock ({aws_region})")
    
    # Setup ChromaDB
    client = setup_chromadb()
    
    # Delete existing collection if it exists (for clean setup)
    try:
        client.delete_collection(name=COLLECTION_NAME)
        print(f"🗑️  Deleted existing collection: {COLLECTION_NAME}")
    except:
        pass
    
    # Create collection with ANN configuration
    collection = client.create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_function,
        metadata={
            "hnsw:space": "cosine",  # Use cosine similarity for semantic search
            "hnsw:construction_ef": 200,  # Higher value = better quality, slower build
            "hnsw:M": 16,  # Number of connections per layer (affects recall)
            "description": "EventHub knowledge base articles with Cohere embeddings"
        }
    )
    
    print(f"✅ Created ChromaDB collection with ANN (HNSW) indexing")
    print(f"   - Distance metric: Cosine similarity")
    print(f"   - HNSW parameters: construction_ef=200, M=16")
    
    # Prepare data for batch insertion
    documents = []
    metadatas = []
    ids = []
    
    for article in articles:
        # Combine title and content for better semantic search
        document_text = f"Title: {article['title']}\n\n{article['content']}"
        documents.append(document_text)
        
        # Store metadata
        metadatas.append({
            "article_id": article["article_id"],
            "title": article["title"],
            "category": article["category"],
            "tags": article.get("tags", ""),
            "view_count": article.get("view_count", 0),
            "helpful_votes": article.get("helpful_votes", 0),
        })
        
        ids.append(article["article_id"])
    
    # Batch insert with embeddings
    print(f"\n🔄 Generating embeddings and inserting {len(documents)} articles...")
    collection.add(
        documents=documents,
        metadatas=metadatas,
        ids=ids
    )
    
    print(f"✅ Successfully stored {len(documents)} articles in ChromaDB")
    
    return collection


def verify_rag_setup(collection, sample_query="How do I cancel my reservation?"):
    """
    Test the RAG setup with a sample query.
    
    Args:
        collection: ChromaDB collection
        sample_query: Test query string
    """
    print(f"\n{'='*80}")
    print("🧪 Testing RAG Setup")
    print(f"{'='*80}")
    
    print(f"\n📝 Sample query: \"{sample_query}\"")
    
    # Perform semantic search
    results = collection.query(
        query_texts=[sample_query],
        n_results=3,
        include=["documents", "metadatas", "distances"]
    )
    
    print(f"\n🔍 Top 3 Results:\n")
    
    if results and results['documents'] and len(results['documents'][0]) > 0:
        for i in range(len(results['documents'][0])):
            metadata = results['metadatas'][0][i]
            distance = results['distances'][0][i]
            similarity = 1 - distance
            
            print(f"  {i+1}. {metadata['title']}")
            print(f"     Category: {metadata['category']}")
            print(f"     Relevance: {similarity:.1%}")
            print(f"     Article ID: {metadata['article_id']}")
            print(f"     Preview: {results['documents'][0][i][:150]}...")
            print()
    else:
        print("  ⚠️  No results found")
    
    print(f"{'='*80}")


def main():
    """Main function to set up RAG system."""
    print("\n" + "="*80)
    print("   EVENTHUB RAG SYSTEM SETUP")
    print("   Knowledge Base → Cohere Embeddings → ChromaDB (ANN)")
    print("="*80 + "\n")
    
    # Step 1: Load KB articles
    print("STEP 1: Loading Knowledge Base Articles")
    print("-" * 80)
    articles = load_kb_articles()
    
    if not articles:
        print("❌ No articles found in database. Please run the database setup first.")
        return
    
    # Display sample article
    print(f"\n📄 Sample Article:")
    print(f"   Title: {articles[0]['title']}")
    print(f"   Category: {articles[0]['category']}")
    print(f"   Content length: {len(articles[0]['content'])} characters")
    
    # Step 2: Generate embeddings and store
    print(f"\n{'='*80}")
    print("STEP 2: Generating Embeddings & Storing in ChromaDB")
    print("-" * 80)
    collection = create_embeddings_and_store(articles)
    
    # Step 3: Verify setup
    verify_rag_setup(collection)
    
    # Final summary
    print("\n" + "="*80)
    print("   ✅ RAG SYSTEM SETUP COMPLETE!")
    print("="*80)
    print(f"\n📊 Summary:")
    print(f"   • KB Articles processed: {len(articles)}")
    print(f"   • Embedding model: Cohere embed-english-v3 (via AWS Bedrock)")
    print(f"   • Vector DB: ChromaDB (persistent)")
    print(f"   • Indexing: HNSW (ANN with cosine similarity)")
    print(f"   • Storage path: {CHROMA_DB_PATH}/")
    print(f"\n🚀 Ready for agent use via search_knowledge_base() tool")
    print()


if __name__ == "__main__":
    main()
