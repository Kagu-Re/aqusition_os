"""Unit tests for Money Board column mapping."""

from pathlib import Path

from ae.console_routes_money_board import _map_status_to_column


def test_map_status_to_column_pending():
    """NEW, PACKAGE_SELECTED, TIME_WINDOW_SET, DEPOSIT_REQUESTED -> pending."""
    assert _map_status_to_column("NEW") == "pending"
    assert _map_status_to_column("new") == "pending"
    assert _map_status_to_column("PACKAGE_SELECTED") == "pending"
    assert _map_status_to_column("package_selected") == "pending"
    assert _map_status_to_column("TIME_WINDOW_SET") == "pending"
    assert _map_status_to_column("time_window_set") == "pending"
    assert _map_status_to_column("DEPOSIT_REQUESTED") == "pending"
    assert _map_status_to_column("deposit_requested") == "pending"


def test_map_status_to_column_confirmed_complete_closed():
    """CONFIRMED, COMPLETE, CLOSED -> correct columns."""
    assert _map_status_to_column("CONFIRMED") == "confirmed"
    assert _map_status_to_column("confirmed") == "confirmed"
    assert _map_status_to_column("COMPLETE") == "complete"
    assert _map_status_to_column("complete") == "complete"
    assert _map_status_to_column("CLOSED") == "closed"
    assert _map_status_to_column("closed") == "closed"


def test_map_status_to_column_cancelled_expired():
    """CANCELLED, EXPIRED -> closed."""
    assert _map_status_to_column("CANCELLED") == "closed"
    assert _map_status_to_column("cancelled") == "closed"
    assert _map_status_to_column("EXPIRED") == "closed"
    assert _map_status_to_column("expired") == "closed"


def test_map_status_to_column_unknown_defaults_to_pending():
    """Unknown status defaults to pending."""
    assert _map_status_to_column("") == "pending"
    assert _map_status_to_column("UNKNOWN") == "pending"
    assert _map_status_to_column("  ") == "pending"
    assert _map_status_to_column(None) == "pending"
