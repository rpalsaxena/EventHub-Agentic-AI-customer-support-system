"""
RAG Tools for Knowledge Base Search

Provides semantic search over knowledge base articles using ChromaDB.
Uses Cohere embeddings via AWS Bedrock for high-quality vector representations.
"""

from typing import List, Dict, Optional
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from langchain_aws import BedrockEmbeddings
from langchain_core.tools import tool
import os


# ChromaDB client initialization (persistent storage)
CHROMA_DB_PATH = "data/vectordb"
COLLECTION_NAME = "kb_articles"


def get_bedrock_embedding_function():
    """Create a ChromaDB-compatible embedding function using Bedrock."""
    # Create LangChain Bedrock embeddings
    bedrock_embeddings = BedrockEmbeddings(
        model_id="cohere.embed-english-v3",
        region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
    )
    
    # Wrap in ChromaDB's embedding function interface
    class BedrockEmbeddingFunction(embedding_functions.EmbeddingFunction):
        def __call__(self, input: list[str]) -> list[list[float]]:
            return bedrock_embeddings.embed_documents(input)
    
    return BedrockEmbeddingFunction()


# ChromaDB client initialization (persistent storage)
CHROMA_DB_PATH = "data/vectordb"
COLLECTION_NAME = "kb_articles"


def get_chroma_client():
    """Get or create ChromaDB persistent client."""
    os.makedirs(CHROMA_DB_PATH, exist_ok=True)
    client = chromadb.PersistentClient(
        path=CHROMA_DB_PATH,
        settings=Settings(
            anonymized_telemetry=False,
            allow_reset=True,
        )
    )
    return client


def get_or_create_collection():
    """Get or create the KB articles collection."""
    client = get_chroma_client()
    
    # Use Cohere embeddings via AWS Bedrock
    embedding_function = get_bedrock_embedding_function()
    
    try:
        collection = client.get_collection(
            name=COLLECTION_NAME,
            embedding_function=embedding_function
        )
    except:
        collection = client.create_collection(
            name=COLLECTION_NAME,
            embedding_function=embedding_function,
            metadata={
                "hnsw:space": "cosine",  # ANN with cosine similarity
                "hnsw:construction_ef": 200,
                "hnsw:M": 16,
            }
        )
    
    return collection


@tool
def search_knowledge_base(query: str, top_k: int = 3) -> List[Dict[str, str]]:
    """
    Search the knowledge base for relevant articles using semantic search.
    
    Args:
        query: The user's question or search query
        top_k: Number of results to return (default: 3)
    
    Returns:
        List of relevant KB articles with title, content, and category
    
    Example:
        results = search_knowledge_base("How do I cancel my reservation?")
        for article in results:
            print(f"Title: {article['title']}")
            print(f"Content: {article['content']}")
    """
    collection = get_or_create_collection()
    
    # Perform ANN search with ChromaDB
    results = collection.query(
        query_texts=[query],
        n_results=top_k,
        include=["documents", "metadatas", "distances"]
    )
    
    # Format results
    articles = []
    if results and results['documents'] and len(results['documents'][0]) > 0:
        for i in range(len(results['documents'][0])):
            metadata = results['metadatas'][0][i] if results['metadatas'] else {}
            distance = results['distances'][0][i] if results['distances'] else 0.0
            
            articles.append({
                "title": metadata.get("title", "Unknown"),
                "content": results['documents'][0][i],
                "category": metadata.get("category", "General"),
                "article_id": metadata.get("article_id", ""),
                "relevance_score": round(1 - distance, 3),  # Convert distance to similarity
            })
    
    return articles


def search_knowledge_base_raw(query: str, top_k: int = 3) -> str:
    """
    Search knowledge base and return formatted text (for LLM context).
    
    Args:
        query: The user's question
        top_k: Number of results to return
    
    Returns:
        Formatted string with relevant KB articles
    """
    results = search_knowledge_base.invoke({"query": query, "top_k": top_k})
    
    if not results:
        return "No relevant knowledge base articles found."
    
    formatted = "📚 Knowledge Base Articles:\n\n"
    for idx, article in enumerate(results, 1):
        formatted += f"**Article {idx}: {article['title']}** (Category: {article['category']})\n"
        formatted += f"Relevance: {article['relevance_score']:.1%}\n"
        formatted += f"{article['content']}\n\n"
        formatted += "-" * 80 + "\n\n"
    
    return formatted
