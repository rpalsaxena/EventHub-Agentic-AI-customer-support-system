"""Master Data Generation Script for EventHub

Orchestrates all data generation scripts in the correct order.
Ensures dependencies are generated before dependent data.

Generation Order (dependency-based):
    1. Users (independent)
    2. Venues (independent)
    3. Events (depends on venues)
    4. Reservations (depends on users + events)
    5. KB Articles (independent, but last for completeness)
    6. Tickets (depends on users + events + reservations)

Usage:
    python generate_all.py              # Generate all data
    python generate_all.py --test       # Test mode (small datasets)
    python generate_all.py --rewrite    # Clear and regenerate all
    python generate_all.py --skip users # Skip specific generators
    
Examples:
    python generate_all.py --test --rewrite    # Fresh test generation
    python generate_all.py --skip users venues # Only generate events onwards
"""

import subprocess
import sys
from pathlib import Path
from datetime import datetime


# ============================================
# CONFIGURATION
# ============================================

GENERATORS = [
    {
        "name": "Users",
        "script": "generate_users.py",
        "description": "10,000 users with subscriptions",
        "test_count": 100,
    },
    {
        "name": "Venues",
        "script": "generate_venues.py",
        "description": "40 venues in SF Bay Area",
        "test_count": 5,
    },
    {
        "name": "Events",
        "script": "generate_events.py",
        "description": "400 events linked to venues",
        "test_count": 10,
        "depends_on": ["generate_venues.py"],
    },
    {
        "name": "KB Articles",
        "script": "generate_kb_articles.py",
        "description": "100 knowledge base articles",
        "test_count": 10,
    },
    {
        "name": "Reservations",
        "script": "generate_reservations.py",
        "description": "5,000 reservations linking users to events",
        "test_count": 100,
        "depends_on": ["generate_users.py", "generate_events.py"],
    },
    {
        "name": "Tickets",
        "script": "generate_tickets.py",
        "description": "500 support tickets",
        "test_count": 20,
        "depends_on": ["generate_users.py", "generate_events.py", "generate_reservations.py"],
    },
]


# ============================================
# RUNNER FUNCTIONS
# ============================================

def run_generator(script: str, test_mode: bool, rewrite_mode: bool) -> bool:
    """Run a single generator script."""
    
    script_path = Path(__file__).parent / script
    
    if not script_path.exists():
        print(f"   ❌ Script not found: {script}")
        return False
    
    # Build command
    cmd = [sys.executable, str(script_path)]
    if test_mode:
        cmd.append("--test")
    if rewrite_mode:
        cmd.append("--rewrite")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=False,
            text=True,
        )
        return result.returncode == 0
    except Exception as e:
        print(f"   ❌ Error running {script}: {e}")
        return False


def print_header():
    """Print generation header."""
    print("\n" + "=" * 60)
    print("   🎫 EventHub Data Generation Pipeline")
    print("=" * 60)
    print(f"   Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60 + "\n")


def print_summary(results: dict):
    """Print generation summary."""
    print("\n" + "=" * 60)
    print("   📊 Generation Summary")
    print("=" * 60)
    
    success_count = sum(1 for v in results.values() if v)
    total_count = len(results)
    
    for name, success in results.items():
        status = "✅" if success else "❌"
        print(f"   {status} {name}")
    
    print("-" * 60)
    print(f"   Total: {success_count}/{total_count} successful")
    print(f"   Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60 + "\n")


def generate_all(test_mode: bool, rewrite_mode: bool, skip: list):
    """Run all generators in order."""
    
    print_header()
    
    if test_mode:
        print("🧪 TEST MODE: Generating small datasets\n")
    if rewrite_mode:
        print("🔄 REWRITE MODE: Clearing existing data\n")
    if skip:
        print(f"⏭️  SKIP: {', '.join(skip)}\n")
    
    results = {}
    
    for generator in GENERATORS:
        name = generator["name"]
        script = generator["script"]
        
        # Check if should skip
        if name.lower() in [s.lower() for s in skip]:
            print(f"⏭️  Skipping {name}...")
            results[name] = True  # Consider skipped as success
            continue
        
        print(f"\n{'=' * 50}")
        print(f"📦 Generating {name}...")
        print(f"   {generator['description']}")
        if test_mode:
            print(f"   Test mode: ~{generator['test_count']} records")
        print("=" * 50 + "\n")
        
        success = run_generator(script, test_mode, rewrite_mode)
        results[name] = success
        
        if not success:
            print(f"\n⚠️  Warning: {name} generation had issues")
            # Continue anyway to try other generators
    
    print_summary(results)
    
    return all(results.values())


# ============================================
# ENTRY POINT
# ============================================

if __name__ == "__main__":
    test_mode = "--test" in sys.argv
    rewrite_mode = "--rewrite" in sys.argv
    
    # Parse skip arguments
    skip = []
    if "--skip" in sys.argv:
        skip_idx = sys.argv.index("--skip")
        for arg in sys.argv[skip_idx + 1:]:
            if arg.startswith("--"):
                break
            skip.append(arg)
    
    success = generate_all(test_mode, rewrite_mode, skip)
    
    sys.exit(0 if success else 1)
