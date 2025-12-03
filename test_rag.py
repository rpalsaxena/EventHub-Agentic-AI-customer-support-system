"""Quick test of RAG search functionality"""

import sys
sys.path.insert(0, '.')

from agentic.tools.rag_tools import search_knowledge_base

print("=" * 80)
print("Testing RAG Search")
print("=" * 80)

# Test 1: Refund policy
print("\n🔍 Query 1: What is the refund policy?\n")
results = search_knowledge_base.invoke({
    'query': 'What is the refund policy?',
    'top_k': 3
})

for i, r in enumerate(results, 1):
    print(f"{i}. {r['title']}")
    print(f"   Category: {r['category']}")
    print(f"   Relevance: {r['relevance_score']:.1%}")
    print(f"   Preview: {r['content'][:]}...")
    print()

# Test 2: Premium benefits
print("\n" + "=" * 80)
print("\n🔍 Query 2: What are premium membership benefits?\n")
results = search_knowledge_base.invoke({
    'query': 'What are the benefits of premium membership?',
    'top_k': 3
})

for i, r in enumerate(results, 1):
    print(f"{i}. {r['title']}")
    print(f"   Relevance: {r['relevance_score']:.1%}")
    print()

# Test 3: Booking issues
print("\n" + "=" * 80)
print("\n🔍 Query 3: My booking is not confirmed\n")
results = search_knowledge_base.invoke({
    'query': 'My booking is not confirmed',
    'top_k': 3
})

for i, r in enumerate(results, 1):
    print(f"{i}. {r['title']}")
    print(f"   Relevance: {r['relevance_score']:.1%}")
    print()

print("=" * 80)
print("✅ RAG Search Test Complete!")
print("=" * 80)
