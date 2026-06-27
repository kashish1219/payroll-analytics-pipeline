import pytest
from datetime import datetime
from pydantic import ValidationError  # Import Pydantic's native error wrapper
import calculation  
import schemas      

def test_sunday_premium_calculation():

    mock_shift = schemas.ShiftCreate(
        contractor_id=1,
        client_company="Workplace Medical Corp",
        time_left_home=datetime(2026, 5, 31, 7, 0, 0),       # Sunday
        time_reached_company=datetime(2026, 5, 31, 8, 0, 0),
        time_finished_company=datetime(2026, 5, 31, 12, 0, 0),
        time_reached_home=datetime(2026, 5, 31, 13, 0, 0),
        km_driven=50.0,
        overnight_stay=False,
        only_travel_day=False
    )
    base_rate = 30.0
    result = calculation.calculate_shift_payout(mock_shift, base_rate)
    
    assert result["total_hours"] == 6.0
    assert result["taxable_wages"] == 270.00  # 6 hours * $30 * 1.5

def test_weekday_standard_calculation():

    mock_shift = schemas.ShiftCreate(
        contractor_id=1,
        client_company="Workplace Medical Corp",
        time_left_home=datetime(2026, 6, 1, 7, 0, 0),        # Monday
        time_reached_company=datetime(2026, 6, 1, 8, 0, 0),
        time_finished_company=datetime(2026, 6, 1, 16, 0, 0),
        time_reached_home=datetime(2026, 6, 1, 17, 0, 0),
        km_driven=100.0,
        overnight_stay=False,
        only_travel_day=False
    )
    base_rate = 30.0
    result = calculation.calculate_shift_payout(mock_shift, base_rate)
    
    assert result["total_hours"] == 10.0
    assert result["taxable_wages"] == 315.00  # 10 hours * $30 straight standard pay

def test_travel_only_day_calculation():

    mock_shift = schemas.ShiftCreate(
        contractor_id=1,
        client_company="Workplace Medical Corp",
        time_left_home=datetime(2026, 6, 2, 8, 0, 0),        # Tuesday
        time_reached_company=None,                           # No arrival
        time_finished_company=None,                          # No finish
        time_reached_home=datetime(2026, 6, 2, 12, 0, 0),
        km_driven=250.0,
        overnight_stay=False,
        only_travel_day=True
    )
    base_rate = 30.0
    result = calculation.calculate_shift_payout(mock_shift, base_rate)
    
    assert result["total_hours"] == 4.0                      # 4 hours pure driving
    assert result["taxable_wages"] == 120.00                 # 4 hours * $30


def test_schema_rejects_negative_km():

    with pytest.raises(ValidationError) as exc_info:
        schemas.ShiftCreate(
            contractor_id=1,
            client_company="Workplace Medical Corp",
            time_left_home=datetime(2026, 6, 1, 7, 0, 0),
            time_reached_company=datetime(2026, 6, 1, 8, 0, 0),
            time_finished_company=datetime(2026, 6, 1, 16, 0, 0),
            time_reached_home=datetime(2026, 6, 1, 17, 0, 0),
            km_driven=-45.0,  # CRIME: Negative distance
            overnight_stay=False,
            only_travel_day=False
        )
    assert "Input should be greater than or equal to 0" in str(exc_info.value)

def test_schema_rejects_time_travel_timeline():

    with pytest.raises(ValidationError) as exc_info:
        schemas.ShiftCreate(
            contractor_id=1,
            client_company="Workplace Medical Corp",
            time_left_home=datetime(2026, 6, 1, 9, 0, 0),        # Left at 9 AM
            time_reached_company=datetime(2026, 6, 1, 8, 0, 0),   # Arrived at 8 AM (Time Travel)
            time_finished_company=datetime(2026, 6, 1, 16, 0, 0),
            time_reached_home=datetime(2026, 6, 1, 17, 0, 0),
            km_driven=50.0,
            overnight_stay=False,
            only_travel_day=False
        )
    assert "Departure time from home must be before arrival at client" in str(exc_info.value)


def test_midnight_rollover_premium_shift():

    mock_shift = schemas.ShiftCreate(
        contractor_id=1,
        client_company="Workplace Medical Corp",
        time_left_home=datetime(2026, 5, 31, 21, 0, 0),       # Sunday 9 PM
        time_reached_company=datetime(2026, 5, 31, 22, 0, 0),  # Sunday 10 PM
        time_finished_company=datetime(2026, 6, 1, 2, 0, 0),   # Monday 2 AM (Rollover)
        time_reached_home=datetime(2026, 6, 1, 3, 0, 0),       # Monday 3 AM
        km_driven=60.0,
        overnight_stay=False,
        only_travel_day=False
    )
    base_rate = 30.0
    
    result = calculation.calculate_shift_payout(mock_shift, base_rate)
    
    assert result["total_hours"] == 6.0
    
    assert result["taxable_wages"] == 270.00  # 6 hours * $30 * 1.5

def test_schema_rejects_extreme_shift_duration():
    
    with pytest.raises(ValidationError) as exc_info:
        schemas.ShiftCreate(
            contractor_id=1,
            client_company="Workplace Medical Corp",
            time_left_home=datetime(2026, 6, 1, 8, 0, 0),
            time_reached_company=datetime(2026, 6, 1, 9, 0, 0),
            time_finished_company=datetime(2026, 6, 3, 17, 0, 0),  # 58 hours total
            time_reached_home=datetime(2026, 6, 3, 18, 0, 0),
            km_driven=50.0,
            overnight_stay=False,
            only_travel_day=False
        )
    assert "Shift duration cannot exceed 24 hours" in str(exc_info.value)