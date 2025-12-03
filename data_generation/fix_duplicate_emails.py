"""
Fix duplicate emails in users.jsonl by appending user_id to the email label.

This script reads the users.jsonl file, identifies duplicate emails,
and updates them to be unique by appending the user_id before the @ symbol.

Example:
    Original: isabella.rossi@outlook.it (duplicate)
    Fixed:    isabella.rossi_u00123@outlook.it
"""

import json
from pathlib import Path
from collections import Counter

# Path to users file
USERS_FILE = Path(__file__).parent.parent / "data" / "generated" / "users.jsonl"


def fix_duplicate_emails():
    """Fix duplicate emails in users.jsonl file."""
    
    print(f"📂 Reading users from: {USERS_FILE}")
    
    # Load all users
    users = []
    with open(USERS_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                users.append(json.loads(line))
    
    print(f"   Total users loaded: {len(users):,}")
    
    # Count email occurrences
    email_counts = Counter(user['email'] for user in users)
    duplicates = {email: count for email, count in email_counts.items() if count > 1}
    
    print(f"   Unique emails: {len(email_counts):,}")
    print(f"   Duplicate email addresses: {len(duplicates):,}")
    
    if not duplicates:
        print("\n✅ No duplicate emails found. File is already clean!")
        return
    
    # Calculate total duplicate entries
    total_duplicates = sum(count - 1 for count in duplicates.values())
    print(f"   Total entries to fix: {total_duplicates:,}")
    
    # Show sample duplicates
    print(f"\n📋 Sample duplicates (first 10):")
    for i, (email, count) in enumerate(list(duplicates.items())[:10]):
        print(f"   {email}: appears {count} times")
    
    # Track seen emails and fix duplicates
    seen_emails = set()
    fixed_count = 0
    
    for user in users:
        email = user['email']
        
        if email in seen_emails:
            # This is a duplicate - fix it
            user_id = user['user_id']
            
            if '@' in email:
                local_part, domain = email.rsplit('@', 1)
                new_email = f"{local_part}_{user_id}@{domain}"
            else:
                new_email = f"{email}_{user_id}"
            
            user['email'] = new_email
            fixed_count += 1
            
            # Also add the new email to seen set
            seen_emails.add(new_email)
        else:
            seen_emails.add(email)
    
    print(f"\n🔧 Fixed {fixed_count:,} duplicate emails")
    
    # Verify uniqueness
    final_emails = [user['email'] for user in users]
    final_unique = len(set(final_emails))
    
    print(f"\n✅ Verification:")
    print(f"   Total users: {len(users):,}")
    print(f"   Unique emails after fix: {final_unique:,}")
    
    if final_unique == len(users):
        print(f"   Status: ALL EMAILS NOW UNIQUE ✓")
    else:
        print(f"   ⚠️  Warning: Still have {len(users) - final_unique} duplicates")
        return
    
    # Backup original file
    backup_file = USERS_FILE.with_suffix('.jsonl.bak')
    print(f"\n💾 Creating backup: {backup_file}")
    
    with open(USERS_FILE, 'r', encoding='utf-8') as src:
        with open(backup_file, 'w', encoding='utf-8') as dst:
            dst.write(src.read())
    
    # Write fixed data
    print(f"📝 Writing fixed data to: {USERS_FILE}")
    
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        for user in users:
            f.write(json.dumps(user, ensure_ascii=False) + '\n')
    
    print(f"\n🎉 Done! Fixed {fixed_count:,} duplicate emails.")
    print(f"   Backup saved to: {backup_file}")


if __name__ == "__main__":
    fix_duplicate_emails()
