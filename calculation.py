from datetime import datetime, timedelta
import schemas

def calculate_shift_payout(shift: schemas.ShiftCreate, base_rate: float):
    
    
    duration_delta = shift.time_reached_home - shift.time_left_home
    total_duration = duration_delta.total_seconds() / 3600.0

    regular_hours = 0.0
    premium_hours = 0.0

    # Iterate through time segments to handle midnight rollovers and fractional hours
    current_time = shift.time_left_home
    while current_time < shift.time_reached_home:
        # Determine the next whole hour clock boundary
        next_hour_boundary = (current_time + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
        
        # If we are already sitting exactly on a whole hour, force push to the next hour marker
        if next_hour_boundary <= current_time:
            next_hour_boundary = current_time + timedelta(hours=1)
        
        # Capture the end of this current segment (either the hour boundary or the final end of the shift)
        segment_end = min(next_hour_boundary, shift.time_reached_home)
        
        # Calculate the exact fraction of an hour this segment represents
        segment_hours = (segment_end - current_time).total_seconds() / 3600.0

        # Evaluate constraints for this specific time segment
        is_weekend = current_time.weekday() in [5, 6]
        hour_block = current_time.hour

        if is_weekend:
            # Rule 1: Weekend hours are ALWAYS premium (1.5x), even if it's just a travel day!
            premium_hours += segment_hours
        elif shift.only_travel_day:
            # Rule 2: Weekday travel days have NO premium hours
            regular_hours += segment_hours
        else:
            # Rule 3: Standard weekday window checks (Premium before 8 AM or after/at 5 PM)
            if hour_block < 8 or hour_block >= 17:
                premium_hours += segment_hours
            else:
                regular_hours += segment_hours

        # Move the processing pointer forward to the next chunk
        current_time = segment_end

    # 3. Expense and Stipend Logic
    mileage_payout = shift.km_driven * 0.50
    shift_stipend = 35.0 if total_duration >= 12.0 else 0.0
    hotel_stipend = 50.0 if shift.overnight_stay else 0.0

    # 4. Final Financial Aggregation
    taxable_wages = (regular_hours * base_rate) + (premium_hours * (base_rate * 1.5))
    tax_free_reimbursements = mileage_payout + shift_stipend + hotel_stipend

    return {
        "total_hours": round(total_duration, 2),
        "regular_hours": round(regular_hours, 2),
        "premium_hours": round(premium_hours, 2),
        "taxable_wages": round(taxable_wages, 2),
        "tax_free_reimbursements": round(tax_free_reimbursements, 2),
        "total_take_home": round(taxable_wages + tax_free_reimbursements, 2)
    }