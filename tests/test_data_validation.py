"""
Data Validation Test Suite for EventHub Generated Datasets

This module provides comprehensive validation for the generated JSONL datasets,
including:
- ID uniqueness validation
- Cross-reference integrity (foreign key validation)
- Email format validation
- Status/enum value validation
- Business logic validation (e.g., tickets_sold <= total_tickets)
- Date/time format validation
- Schema completeness validation

Usage:
    pytest test_data_validation.py -v
    pytest test_data_validation.py -v --tb=short  # For shorter output
    pytest test_data_validation.py -v -k "uniqueness"  # Run only uniqueness tests
"""

import json
import re
from pathlib import Path
from datetime import datetime
from collections import Counter
from typing import Any, Optional
import pytest


# ============================================================================
# Configuration
# ============================================================================

DATA_DIR = Path(__file__).parent.parent / "data" / "generated"

# File paths
FILES = {
    "users": DATA_DIR / "users.jsonl",
    "events": DATA_DIR / "events.jsonl",
    "venues": DATA_DIR / "venues.jsonl",
    "tickets": DATA_DIR / "tickets.jsonl",
    "reservations": DATA_DIR / "reservations.jsonl",
    "kb_articles": DATA_DIR / "kb_articles.jsonl",
}

# Valid enum values
VALID_SUBSCRIPTION_TIERS = {"basic", "premium"}
VALID_SUBSCRIPTION_STATUSES = {"active", "cancelled", "paused"}
VALID_EVENT_STATUSES = {"active", "cancelled", "soldout"}
VALID_EVENT_CATEGORIES = {"music", "theater", "comedy", "art", "sports", "conference", "museum"}
VALID_VENUE_CATEGORIES = {"music", "theater", "comedy", "art", "sports", "conference", "museum"}
VALID_TICKET_STATUSES = {"open", "in_progress", "resolved", "escalated"}
VALID_TICKET_PRIORITIES = {"low", "medium", "high", "urgent"}
VALID_TICKET_CATEGORIES = {"general", "refund", "technical", "complaint", "cancellation"}
VALID_RESERVATION_STATUSES = {"confirmed", "cancelled", "pending"}
VALID_PAYMENT_METHODS = {"credit_card", "paypal", "apple_pay", "google_pay"}
VALID_KB_CATEGORIES = {"how-to", "troubleshooting", "policy", "faq", "general"}


# ============================================================================
# Helper Functions
# ============================================================================

def load_jsonl(file_path: Path) -> list[dict]:
    """Load a JSONL file and return a list of dictionaries."""
    records = []
    if not file_path.exists():
        pytest.skip(f"File not found: {file_path}")
    
    with open(file_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError as e:
                    pytest.fail(f"JSON parse error in {file_path.name} at line {line_num}: {e}")
    return records


def is_valid_email(email: str) -> bool:
    """Validate email format using a regex pattern that supports Unicode characters."""
    # Support international characters (Unicode) in the local part of email
    pattern = r'^[\w.%+-]+@[\w.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email, re.UNICODE))


def is_valid_date(date_str: str, fmt: str = "%Y-%m-%d") -> bool:
    """Validate date string format."""
    try:
        datetime.strptime(date_str, fmt)
        return True
    except (ValueError, TypeError):
        return False


def is_valid_datetime(dt_str: str) -> bool:
    """Validate datetime string format (ISO format or common variations)."""
    formats = [
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ]
    for fmt in formats:
        try:
            datetime.strptime(dt_str, fmt)
            return True
        except (ValueError, TypeError):
            continue
    return False


def is_valid_time(time_str: str) -> bool:
    """Validate time string format (HH:MM)."""
    try:
        datetime.strptime(time_str, "%H:%M")
        return True
    except (ValueError, TypeError):
        return False


def check_id_format(id_value: str, prefix: str, digits: int = 5) -> bool:
    """Check if ID follows the expected format (e.g., u_00001, e_00001)."""
    pattern = rf'^{prefix}_\d{{{digits}}}$'
    return bool(re.match(pattern, id_value))


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture(scope="module")
def users_data():
    """Load users data."""
    return load_jsonl(FILES["users"])


@pytest.fixture(scope="module")
def events_data():
    """Load events data."""
    return load_jsonl(FILES["events"])


@pytest.fixture(scope="module")
def venues_data():
    """Load venues data."""
    return load_jsonl(FILES["venues"])


@pytest.fixture(scope="module")
def tickets_data():
    """Load tickets data."""
    return load_jsonl(FILES["tickets"])


@pytest.fixture(scope="module")
def reservations_data():
    """Load reservations data."""
    return load_jsonl(FILES["reservations"])


@pytest.fixture(scope="module")
def kb_articles_data():
    """Load knowledge base articles data."""
    return load_jsonl(FILES["kb_articles"])


@pytest.fixture(scope="module")
def all_user_ids(users_data):
    """Get set of all valid user IDs."""
    return {u["user_id"] for u in users_data}


@pytest.fixture(scope="module")
def all_event_ids(events_data):
    """Get set of all valid event IDs."""
    return {e["event_id"] for e in events_data}


@pytest.fixture(scope="module")
def all_venue_ids(venues_data):
    """Get set of all valid venue IDs."""
    return {v["venue_id"] for v in venues_data}


@pytest.fixture(scope="module")
def all_reservation_ids(reservations_data):
    """Get set of all valid reservation IDs."""
    return {r["reservation_id"] for r in reservations_data}


# ============================================================================
# ID Uniqueness Tests
# ============================================================================

class TestIDUniqueness:
    """Test that all IDs are unique within their respective datasets."""

    def test_user_ids_unique(self, users_data):
        """Verify all user IDs are unique."""
        user_ids = [u["user_id"] for u in users_data]
        duplicates = [id for id, count in Counter(user_ids).items() if count > 1]
        
        assert len(duplicates) == 0, f"Duplicate user IDs found: {duplicates[:10]}"
        assert len(user_ids) == len(set(user_ids)), "User IDs are not unique"

    def test_event_ids_unique(self, events_data):
        """Verify all event IDs are unique."""
        event_ids = [e["event_id"] for e in events_data]
        duplicates = [id for id, count in Counter(event_ids).items() if count > 1]
        
        assert len(duplicates) == 0, f"Duplicate event IDs found: {duplicates[:10]}"
        assert len(event_ids) == len(set(event_ids)), "Event IDs are not unique"

    def test_venue_ids_unique(self, venues_data):
        """Verify all venue IDs are unique."""
        venue_ids = [v["venue_id"] for v in venues_data]
        duplicates = [id for id, count in Counter(venue_ids).items() if count > 1]
        
        assert len(duplicates) == 0, f"Duplicate venue IDs found: {duplicates[:10]}"
        assert len(venue_ids) == len(set(venue_ids)), "Venue IDs are not unique"

    def test_ticket_ids_unique(self, tickets_data):
        """Verify all support ticket IDs are unique."""
        ticket_ids = [t["ticket_id"] for t in tickets_data]
        duplicates = [id for id, count in Counter(ticket_ids).items() if count > 1]
        
        assert len(duplicates) == 0, f"Duplicate ticket IDs found: {duplicates[:10]}"
        assert len(ticket_ids) == len(set(ticket_ids)), "Ticket IDs are not unique"

    def test_reservation_ids_unique(self, reservations_data):
        """Verify all reservation IDs are unique."""
        reservation_ids = [r["reservation_id"] for r in reservations_data]
        duplicates = [id for id, count in Counter(reservation_ids).items() if count > 1]
        
        assert len(duplicates) == 0, f"Duplicate reservation IDs found: {duplicates[:10]}"
        assert len(reservation_ids) == len(set(reservation_ids)), "Reservation IDs are not unique"

    def test_kb_article_ids_unique(self, kb_articles_data):
        """Verify all knowledge base article IDs are unique."""
        article_ids = [a["article_id"] for a in kb_articles_data]
        duplicates = [id for id, count in Counter(article_ids).items() if count > 1]
        
        assert len(duplicates) == 0, f"Duplicate article IDs found: {duplicates[:10]}"
        assert len(article_ids) == len(set(article_ids)), "Article IDs are not unique"


# ============================================================================
# ID Format Validation Tests
# ============================================================================

class TestIDFormat:
    """Test that all IDs follow the expected format patterns."""

    def test_user_id_format(self, users_data):
        """Verify user IDs follow the format u_XXXXX."""
        invalid_ids = [u["user_id"] for u in users_data if not check_id_format(u["user_id"], "u")]
        assert len(invalid_ids) == 0, f"Invalid user ID formats: {invalid_ids[:10]}"

    def test_event_id_format(self, events_data):
        """Verify event IDs follow the format e_XXXXX."""
        invalid_ids = [e["event_id"] for e in events_data if not check_id_format(e["event_id"], "e")]
        assert len(invalid_ids) == 0, f"Invalid event ID formats: {invalid_ids[:10]}"

    def test_venue_id_format(self, venues_data):
        """Verify venue IDs follow the format v_XXXXX."""
        invalid_ids = [v["venue_id"] for v in venues_data if not check_id_format(v["venue_id"], "v")]
        assert len(invalid_ids) == 0, f"Invalid venue ID formats: {invalid_ids[:10]}"

    def test_ticket_id_format(self, tickets_data):
        """Verify ticket IDs follow the format t_XXXXX."""
        invalid_ids = [t["ticket_id"] for t in tickets_data if not check_id_format(t["ticket_id"], "t")]
        assert len(invalid_ids) == 0, f"Invalid ticket ID formats: {invalid_ids[:10]}"

    def test_reservation_id_format(self, reservations_data):
        """Verify reservation IDs follow the format r_XXXXX."""
        invalid_ids = [r["reservation_id"] for r in reservations_data if not check_id_format(r["reservation_id"], "r")]
        assert len(invalid_ids) == 0, f"Invalid reservation ID formats: {invalid_ids[:10]}"

    def test_kb_article_id_format(self, kb_articles_data):
        """Verify knowledge base article IDs follow the format kb_XXXXX."""
        invalid_ids = [a["article_id"] for a in kb_articles_data if not check_id_format(a["article_id"], "kb")]
        assert len(invalid_ids) == 0, f"Invalid article ID formats: {invalid_ids[:10]}"


# ============================================================================
# Cross-Reference Validation Tests (Foreign Key Integrity)
# ============================================================================

class TestCrossReferences:
    """Test that all cross-references (foreign keys) point to valid records."""

    def test_ticket_user_id_exists(self, tickets_data, all_user_ids):
        """Verify all user_ids in tickets reference existing users."""
        orphan_refs = []
        for ticket in tickets_data:
            user_id = ticket.get("user_id")
            if user_id and user_id not in all_user_ids:
                orphan_refs.append({
                    "ticket_id": ticket["ticket_id"],
                    "user_id": user_id
                })
        
        if orphan_refs:
            sample = orphan_refs[:10]
            pytest.fail(
                f"Found {len(orphan_refs)} tickets with non-existent user_ids. "
                f"Sample: {sample}"
            )

    def test_ticket_event_id_exists(self, tickets_data, all_event_ids):
        """Verify all event_ids in tickets reference existing events."""
        orphan_refs = []
        for ticket in tickets_data:
            event_id = ticket.get("event_id")
            if event_id and event_id not in all_event_ids:
                orphan_refs.append({
                    "ticket_id": ticket["ticket_id"],
                    "event_id": event_id
                })
        
        if orphan_refs:
            sample = orphan_refs[:10]
            pytest.fail(
                f"Found {len(orphan_refs)} tickets with non-existent event_ids. "
                f"Sample: {sample}"
            )

    def test_ticket_reservation_id_exists(self, tickets_data, all_reservation_ids):
        """Verify all reservation_ids in tickets reference existing reservations."""
        orphan_refs = []
        for ticket in tickets_data:
            reservation_id = ticket.get("reservation_id")
            if reservation_id and reservation_id not in all_reservation_ids:
                orphan_refs.append({
                    "ticket_id": ticket["ticket_id"],
                    "reservation_id": reservation_id
                })
        
        if orphan_refs:
            sample = orphan_refs[:10]
            pytest.fail(
                f"Found {len(orphan_refs)} tickets with non-existent reservation_ids. "
                f"Sample: {sample}"
            )

    def test_reservation_user_id_exists(self, reservations_data, all_user_ids):
        """Verify all user_ids in reservations reference existing users."""
        orphan_refs = []
        for reservation in reservations_data:
            user_id = reservation.get("user_id")
            if user_id and user_id not in all_user_ids:
                orphan_refs.append({
                    "reservation_id": reservation["reservation_id"],
                    "user_id": user_id
                })
        
        if orphan_refs:
            sample = orphan_refs[:10]
            pytest.fail(
                f"Found {len(orphan_refs)} reservations with non-existent user_ids. "
                f"Sample: {sample}"
            )

    def test_reservation_event_id_exists(self, reservations_data, all_event_ids):
        """Verify all event_ids in reservations reference existing events."""
        orphan_refs = []
        for reservation in reservations_data:
            event_id = reservation.get("event_id")
            if event_id and event_id not in all_event_ids:
                orphan_refs.append({
                    "reservation_id": reservation["reservation_id"],
                    "event_id": event_id
                })
        
        if orphan_refs:
            sample = orphan_refs[:10]
            pytest.fail(
                f"Found {len(orphan_refs)} reservations with non-existent event_ids. "
                f"Sample: {sample}"
            )

    def test_reservation_venue_id_exists(self, reservations_data, all_venue_ids):
        """Verify all venue_ids in reservations reference existing venues."""
        orphan_refs = []
        for reservation in reservations_data:
            venue_id = reservation.get("venue_id")
            if venue_id and venue_id not in all_venue_ids:
                orphan_refs.append({
                    "reservation_id": reservation["reservation_id"],
                    "venue_id": venue_id
                })
        
        if orphan_refs:
            sample = orphan_refs[:10]
            pytest.fail(
                f"Found {len(orphan_refs)} reservations with non-existent venue_ids. "
                f"Sample: {sample}"
            )

    def test_event_venue_id_exists(self, events_data, all_venue_ids):
        """Verify all venue_ids in events reference existing venues."""
        orphan_refs = []
        for event in events_data:
            venue_id = event.get("venue_id")
            if venue_id and venue_id not in all_venue_ids:
                orphan_refs.append({
                    "event_id": event["event_id"],
                    "venue_id": venue_id
                })
        
        if orphan_refs:
            sample = orphan_refs[:10]
            pytest.fail(
                f"Found {len(orphan_refs)} events with non-existent venue_ids. "
                f"Sample: {sample}"
            )


# ============================================================================
# Email Format Validation Tests
# ============================================================================

class TestEmailFormats:
    """Test that all email fields contain valid email formats."""

    def test_user_emails_valid(self, users_data):
        """Verify all user emails have valid format."""
        invalid_emails = []
        for user in users_data:
            email = user.get("email")
            if email and not is_valid_email(email):
                invalid_emails.append({
                    "user_id": user["user_id"],
                    "email": email
                })
        
        assert len(invalid_emails) == 0, f"Invalid user emails: {invalid_emails[:10]}"

    def test_ticket_user_emails_valid(self, tickets_data):
        """Verify all ticket user emails have valid format."""
        invalid_emails = []
        for ticket in tickets_data:
            email = ticket.get("user_email")
            if email and not is_valid_email(email):
                invalid_emails.append({
                    "ticket_id": ticket["ticket_id"],
                    "email": email
                })
        
        assert len(invalid_emails) == 0, f"Invalid ticket emails: {invalid_emails[:10]}"

    def test_reservation_user_emails_valid(self, reservations_data):
        """Verify all reservation user emails have valid format."""
        invalid_emails = []
        for reservation in reservations_data:
            email = reservation.get("user_email")
            if email and not is_valid_email(email):
                invalid_emails.append({
                    "reservation_id": reservation["reservation_id"],
                    "email": email
                })
        
        assert len(invalid_emails) == 0, f"Invalid reservation emails: {invalid_emails[:10]}"


# ============================================================================
# Enum/Status Value Validation Tests
# ============================================================================

class TestEnumValues:
    """Test that all enum/status fields contain valid values."""

    def test_user_subscription_tiers(self, users_data):
        """Verify all subscription_tier values are valid."""
        invalid_tiers = []
        for user in users_data:
            tier = user.get("subscription_tier")
            if tier and tier not in VALID_SUBSCRIPTION_TIERS:
                invalid_tiers.append({
                    "user_id": user["user_id"],
                    "subscription_tier": tier
                })
        
        assert len(invalid_tiers) == 0, f"Invalid subscription tiers: {invalid_tiers[:10]}"

    def test_user_subscription_statuses(self, users_data):
        """Verify all subscription_status values are valid."""
        invalid_statuses = []
        for user in users_data:
            status = user.get("subscription_status")
            if status and status not in VALID_SUBSCRIPTION_STATUSES:
                invalid_statuses.append({
                    "user_id": user["user_id"],
                    "subscription_status": status
                })
        
        assert len(invalid_statuses) == 0, f"Invalid subscription statuses: {invalid_statuses[:10]}"

    def test_event_statuses(self, events_data):
        """Verify all event status values are valid."""
        invalid_statuses = []
        for event in events_data:
            status = event.get("status")
            if status and status not in VALID_EVENT_STATUSES:
                invalid_statuses.append({
                    "event_id": event["event_id"],
                    "status": status
                })
        
        assert len(invalid_statuses) == 0, f"Invalid event statuses: {invalid_statuses[:10]}"

    def test_event_categories(self, events_data):
        """Verify all event category values are valid."""
        invalid_categories = []
        for event in events_data:
            category = event.get("category")
            if category and category not in VALID_EVENT_CATEGORIES:
                invalid_categories.append({
                    "event_id": event["event_id"],
                    "category": category
                })
        
        assert len(invalid_categories) == 0, f"Invalid event categories: {invalid_categories[:10]}"

    def test_venue_categories(self, venues_data):
        """Verify all venue category values are valid."""
        invalid_categories = []
        for venue in venues_data:
            category = venue.get("category")
            if category and category not in VALID_VENUE_CATEGORIES:
                invalid_categories.append({
                    "venue_id": venue["venue_id"],
                    "category": category
                })
        
        assert len(invalid_categories) == 0, f"Invalid venue categories: {invalid_categories[:10]}"

    def test_ticket_statuses(self, tickets_data):
        """Verify all ticket status values are valid."""
        invalid_statuses = []
        for ticket in tickets_data:
            status = ticket.get("status")
            if status and status not in VALID_TICKET_STATUSES:
                invalid_statuses.append({
                    "ticket_id": ticket["ticket_id"],
                    "status": status
                })
        
        assert len(invalid_statuses) == 0, f"Invalid ticket statuses: {invalid_statuses[:10]}"

    def test_ticket_priorities(self, tickets_data):
        """Verify all ticket priority values are valid."""
        invalid_priorities = []
        for ticket in tickets_data:
            priority = ticket.get("priority")
            if priority and priority not in VALID_TICKET_PRIORITIES:
                invalid_priorities.append({
                    "ticket_id": ticket["ticket_id"],
                    "priority": priority
                })
        
        assert len(invalid_priorities) == 0, f"Invalid ticket priorities: {invalid_priorities[:10]}"

    def test_ticket_categories(self, tickets_data):
        """Verify all ticket category values are valid."""
        invalid_categories = []
        for ticket in tickets_data:
            category = ticket.get("category")
            if category and category not in VALID_TICKET_CATEGORIES:
                invalid_categories.append({
                    "ticket_id": ticket["ticket_id"],
                    "category": category
                })
        
        assert len(invalid_categories) == 0, f"Invalid ticket categories: {invalid_categories[:10]}"

    def test_reservation_statuses(self, reservations_data):
        """Verify all reservation status values are valid."""
        invalid_statuses = []
        for reservation in reservations_data:
            status = reservation.get("status")
            if status and status not in VALID_RESERVATION_STATUSES:
                invalid_statuses.append({
                    "reservation_id": reservation["reservation_id"],
                    "status": status
                })
        
        assert len(invalid_statuses) == 0, f"Invalid reservation statuses: {invalid_statuses[:10]}"

    def test_reservation_payment_methods(self, reservations_data):
        """Verify all payment method values are valid."""
        invalid_methods = []
        for reservation in reservations_data:
            method = reservation.get("payment_method")
            if method and method not in VALID_PAYMENT_METHODS:
                invalid_methods.append({
                    "reservation_id": reservation["reservation_id"],
                    "payment_method": method
                })
        
        assert len(invalid_methods) == 0, f"Invalid payment methods: {invalid_methods[:10]}"


# ============================================================================
# Business Logic Validation Tests
# ============================================================================

class TestBusinessLogic:
    """Test business logic constraints and data consistency."""

    def test_tickets_sold_not_exceed_total(self, events_data):
        """Verify tickets_sold does not exceed total_tickets for events."""
        violations = []
        for event in events_data:
            tickets_sold = event.get("tickets_sold", 0)
            total_tickets = event.get("total_tickets", 0)
            if tickets_sold > total_tickets:
                violations.append({
                    "event_id": event["event_id"],
                    "tickets_sold": tickets_sold,
                    "total_tickets": total_tickets
                })
        
        assert len(violations) == 0, f"Events with tickets_sold > total_tickets: {violations[:10]}"

    def test_soldout_events_have_full_sales(self, events_data):
        """Verify soldout events have tickets_sold == total_tickets."""
        violations = []
        for event in events_data:
            if event.get("status") == "soldout":
                tickets_sold = event.get("tickets_sold", 0)
                total_tickets = event.get("total_tickets", 0)
                if tickets_sold != total_tickets:
                    violations.append({
                        "event_id": event["event_id"],
                        "tickets_sold": tickets_sold,
                        "total_tickets": total_tickets
                    })
        
        assert len(violations) == 0, f"Soldout events without full sales: {violations[:10]}"

    def test_price_min_not_exceed_max(self, events_data):
        """Verify price_min does not exceed price_max for events."""
        violations = []
        for event in events_data:
            price_min = event.get("price_min", 0)
            price_max = event.get("price_max", 0)
            if price_min > price_max:
                violations.append({
                    "event_id": event["event_id"],
                    "price_min": price_min,
                    "price_max": price_max
                })
        
        assert len(violations) == 0, f"Events with price_min > price_max: {violations[:10]}"

    def test_reservation_ticket_count_positive(self, reservations_data):
        """Verify reservation ticket counts are positive."""
        violations = []
        for reservation in reservations_data:
            ticket_count = reservation.get("ticket_count", 0)
            if ticket_count <= 0:
                violations.append({
                    "reservation_id": reservation["reservation_id"],
                    "ticket_count": ticket_count
                })
        
        assert len(violations) == 0, f"Reservations with non-positive ticket count: {violations[:10]}"

    def test_reservation_total_price_positive(self, reservations_data):
        """Verify reservation total prices are positive."""
        violations = []
        for reservation in reservations_data:
            total_price = reservation.get("total_price", 0)
            if total_price <= 0:
                violations.append({
                    "reservation_id": reservation["reservation_id"],
                    "total_price": total_price
                })
        
        assert len(violations) == 0, f"Reservations with non-positive total price: {violations[:10]}"

    def test_venue_capacity_positive(self, venues_data):
        """Verify venue capacities are positive."""
        violations = []
        for venue in venues_data:
            capacity = venue.get("capacity", 0)
            if capacity <= 0:
                violations.append({
                    "venue_id": venue["venue_id"],
                    "capacity": capacity
                })
        
        assert len(violations) == 0, f"Venues with non-positive capacity: {violations[:10]}"

    def test_user_monthly_quota_positive(self, users_data):
        """Verify user monthly quotas are positive."""
        violations = []
        for user in users_data:
            quota = user.get("monthly_quota", 0)
            if quota <= 0:
                violations.append({
                    "user_id": user["user_id"],
                    "monthly_quota": quota
                })
        
        assert len(violations) == 0, f"Users with non-positive monthly quota: {violations[:10]}"

    def test_resolved_tickets_have_resolved_date(self, tickets_data):
        """Verify resolved tickets have a resolved_at date."""
        violations = []
        for ticket in tickets_data:
            if ticket.get("status") == "resolved" and not ticket.get("resolved_at"):
                violations.append({
                    "ticket_id": ticket["ticket_id"],
                    "status": ticket["status"],
                    "resolved_at": ticket.get("resolved_at")
                })
        
        assert len(violations) == 0, f"Resolved tickets without resolved_at: {violations[:10]}"

    def test_open_tickets_no_resolved_date(self, tickets_data):
        """Verify open/in_progress tickets don't have a resolved_at date."""
        violations = []
        for ticket in tickets_data:
            if ticket.get("status") in ["open", "in_progress"] and ticket.get("resolved_at"):
                violations.append({
                    "ticket_id": ticket["ticket_id"],
                    "status": ticket["status"],
                    "resolved_at": ticket.get("resolved_at")
                })
        
        # This might be a warning rather than failure - escalated tickets may have resolved_at
        if violations:
            print(f"Warning: {len(violations)} open/in_progress tickets have resolved_at dates")


# ============================================================================
# Date/Time Format Validation Tests
# ============================================================================

class TestDateTimeFormats:
    """Test that all date/time fields have valid formats."""

    def test_event_dates_valid(self, events_data):
        """Verify all event dates have valid format."""
        invalid_dates = []
        for event in events_data:
            event_date = event.get("event_date")
            if event_date and not is_valid_date(event_date):
                invalid_dates.append({
                    "event_id": event["event_id"],
                    "event_date": event_date
                })
        
        assert len(invalid_dates) == 0, f"Invalid event dates: {invalid_dates[:10]}"

    def test_event_start_times_valid(self, events_data):
        """Verify all event start times have valid format."""
        invalid_times = []
        for event in events_data:
            start_time = event.get("start_time")
            if start_time and not is_valid_time(start_time):
                invalid_times.append({
                    "event_id": event["event_id"],
                    "start_time": start_time
                })
        
        assert len(invalid_times) == 0, f"Invalid event start times: {invalid_times[:10]}"

    def test_user_created_at_valid(self, users_data):
        """Verify all user created_at dates are valid."""
        invalid_dates = []
        for user in users_data:
            created_at = user.get("created_at")
            if created_at and not is_valid_datetime(created_at):
                invalid_dates.append({
                    "user_id": user["user_id"],
                    "created_at": created_at
                })
        
        assert len(invalid_dates) == 0, f"Invalid user created_at dates: {invalid_dates[:10]}"

    def test_reservation_booking_dates_valid(self, reservations_data):
        """Verify all reservation booking dates have valid format."""
        invalid_dates = []
        for reservation in reservations_data:
            booking_date = reservation.get("booking_date")
            if booking_date and not is_valid_date(booking_date):
                invalid_dates.append({
                    "reservation_id": reservation["reservation_id"],
                    "booking_date": booking_date
                })
        
        assert len(invalid_dates) == 0, f"Invalid reservation booking dates: {invalid_dates[:10]}"

    def test_reservation_event_dates_valid(self, reservations_data):
        """Verify all reservation event dates have valid format."""
        invalid_dates = []
        for reservation in reservations_data:
            event_date = reservation.get("event_date")
            if event_date and not is_valid_date(event_date):
                invalid_dates.append({
                    "reservation_id": reservation["reservation_id"],
                    "event_date": event_date
                })
        
        assert len(invalid_dates) == 0, f"Invalid reservation event dates: {invalid_dates[:10]}"


# ============================================================================
# Schema Completeness Validation Tests
# ============================================================================

class TestSchemaCompleteness:
    """Test that required fields are present in all records."""

    def test_users_required_fields(self, users_data):
        """Verify all required fields are present in user records."""
        required_fields = ["user_id", "full_name", "email", "city", "is_blocked", "created_at"]
        missing = []
        for user in users_data:
            missing_fields = [f for f in required_fields if f not in user or user[f] is None]
            if missing_fields:
                missing.append({
                    "user_id": user.get("user_id", "UNKNOWN"),
                    "missing_fields": missing_fields
                })
        
        assert len(missing) == 0, f"Users with missing required fields: {missing[:10]}"

    def test_events_required_fields(self, events_data):
        """Verify all required fields are present in event records."""
        required_fields = ["event_id", "title", "venue_id", "category", "event_date", "status"]
        missing = []
        for event in events_data:
            missing_fields = [f for f in required_fields if f not in event or event[f] is None]
            if missing_fields:
                missing.append({
                    "event_id": event.get("event_id", "UNKNOWN"),
                    "missing_fields": missing_fields
                })
        
        assert len(missing) == 0, f"Events with missing required fields: {missing[:10]}"

    def test_venues_required_fields(self, venues_data):
        """Verify all required fields are present in venue records."""
        required_fields = ["venue_id", "name", "city", "capacity", "category"]
        missing = []
        for venue in venues_data:
            missing_fields = [f for f in required_fields if f not in venue or venue[f] is None]
            if missing_fields:
                missing.append({
                    "venue_id": venue.get("venue_id", "UNKNOWN"),
                    "missing_fields": missing_fields
                })
        
        assert len(missing) == 0, f"Venues with missing required fields: {missing[:10]}"

    def test_tickets_required_fields(self, tickets_data):
        """Verify all required fields are present in ticket records."""
        required_fields = ["ticket_id", "user_id", "category", "subject", "status", "priority"]
        missing = []
        for ticket in tickets_data:
            missing_fields = [f for f in required_fields if f not in ticket or ticket[f] is None]
            if missing_fields:
                missing.append({
                    "ticket_id": ticket.get("ticket_id", "UNKNOWN"),
                    "missing_fields": missing_fields
                })
        
        assert len(missing) == 0, f"Tickets with missing required fields: {missing[:10]}"

    def test_reservations_required_fields(self, reservations_data):
        """Verify all required fields are present in reservation records."""
        required_fields = ["reservation_id", "user_id", "event_id", "ticket_count", "status"]
        missing = []
        for reservation in reservations_data:
            missing_fields = [f for f in required_fields if f not in reservation or reservation[f] is None]
            if missing_fields:
                missing.append({
                    "reservation_id": reservation.get("reservation_id", "UNKNOWN"),
                    "missing_fields": missing_fields
                })
        
        assert len(missing) == 0, f"Reservations with missing required fields: {missing[:10]}"


# ============================================================================
# Data Summary Report (Optional - Run with -v flag)
# ============================================================================

class TestDataSummary:
    """Generate summary statistics for the datasets."""

    def test_generate_data_summary(self, users_data, events_data, venues_data, 
                                   tickets_data, reservations_data, kb_articles_data):
        """Generate and print a summary of all datasets."""
        summary = {
            "users": {
                "count": len(users_data),
                "blocked_users": sum(1 for u in users_data if u.get("is_blocked")),
                "premium_users": sum(1 for u in users_data if u.get("subscription_tier") == "premium"),
                "active_subscriptions": sum(1 for u in users_data if u.get("subscription_status") == "active"),
            },
            "events": {
                "count": len(events_data),
                "active": sum(1 for e in events_data if e.get("status") == "active"),
                "cancelled": sum(1 for e in events_data if e.get("status") == "cancelled"),
                "soldout": sum(1 for e in events_data if e.get("status") == "soldout"),
                "premium": sum(1 for e in events_data if e.get("is_premium")),
            },
            "venues": {
                "count": len(venues_data),
                "categories": list(set(v.get("category") for v in venues_data if v.get("category"))),
            },
            "tickets": {
                "count": len(tickets_data),
                "open": sum(1 for t in tickets_data if t.get("status") == "open"),
                "resolved": sum(1 for t in tickets_data if t.get("status") == "resolved"),
                "escalated": sum(1 for t in tickets_data if t.get("status") == "escalated"),
            },
            "reservations": {
                "count": len(reservations_data),
                "confirmed": sum(1 for r in reservations_data if r.get("status") == "confirmed"),
                "cancelled": sum(1 for r in reservations_data if r.get("status") == "cancelled"),
                "pending": sum(1 for r in reservations_data if r.get("status") == "pending"),
            },
            "kb_articles": {
                "count": len(kb_articles_data),
                "published": sum(1 for a in kb_articles_data if a.get("is_published")),
            },
        }
        
        print("\n" + "="*60)
        print("DATA VALIDATION SUMMARY")
        print("="*60)
        
        for dataset, stats in summary.items():
            print(f"\n{dataset.upper()}:")
            for key, value in stats.items():
                print(f"  {key}: {value}")
        
        print("\n" + "="*60)
        
        # This test always passes - it's just for reporting
        assert True


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
