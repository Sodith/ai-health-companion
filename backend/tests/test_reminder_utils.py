"""Unit tests for reminder_service utility functions.

Tests parse_frequency and parse_duration_days in complete isolation —
no DB, no HTTP, no fixtures needed.
"""
import pytest
from app.services.reminder_service import parse_frequency, parse_duration_days, REMINDER_TIMES
from datetime import time


# ---------------------------------------------------------------------------
# parse_frequency
# ---------------------------------------------------------------------------

class TestParseFrequency:
    def test_none_returns_1(self):
        assert parse_frequency(None) == 1

    def test_empty_string_returns_1(self):
        assert parse_frequency("") == 1

    def test_once_daily(self):
        assert parse_frequency("once daily") == 1

    def test_1_time_daily(self):
        assert parse_frequency("1 time daily") == 1

    def test_twice_daily(self):
        assert parse_frequency("twice daily") == 2

    def test_2_times_daily(self):
        assert parse_frequency("2 times daily") == 2

    def test_bid(self):
        assert parse_frequency("BID") == 2

    def test_thrice_daily(self):
        assert parse_frequency("thrice daily") == 3

    def test_3_times_daily(self):
        assert parse_frequency("3 times a day") == 3

    def test_four_times_daily(self):
        assert parse_frequency("4 times daily") == 4

    def test_unrecognised_defaults_to_1(self):
        assert parse_frequency("as needed") == 1


# ---------------------------------------------------------------------------
# parse_duration_days
# ---------------------------------------------------------------------------

class TestParseDurationDays:
    def test_none_returns_7(self):
        assert parse_duration_days(None) == 7

    def test_empty_returns_7(self):
        assert parse_duration_days("") == 7

    def test_days(self):
        assert parse_duration_days("30 days") == 30

    def test_day_singular(self):
        assert parse_duration_days("1 day") == 1

    def test_weeks(self):
        assert parse_duration_days("2 weeks") == 14

    def test_week_singular(self):
        assert parse_duration_days("1 week") == 7

    def test_months(self):
        assert parse_duration_days("1 month") == 30

    def test_two_months(self):
        assert parse_duration_days("2 months") == 60

    def test_no_unit_assumes_days(self):
        assert parse_duration_days("10") == 10

    def test_no_number_returns_7(self):
        assert parse_duration_days("indefinitely") == 7


# ---------------------------------------------------------------------------
# REMINDER_TIMES mapping
# ---------------------------------------------------------------------------

class TestReminderTimes:
    def test_1_dose_morning_only(self):
        times = REMINDER_TIMES[1]
        assert times == [time(8, 0)]

    def test_2_doses_morning_evening(self):
        times = REMINDER_TIMES[2]
        assert times == [time(8, 0), time(20, 0)]

    def test_3_doses_spread(self):
        times = REMINDER_TIMES[3]
        assert len(times) == 3
        assert times[0] == time(8, 0)
        assert times[-1] == time(21, 0)

    def test_4_doses_spread(self):
        times = REMINDER_TIMES[4]
        assert len(times) == 4

