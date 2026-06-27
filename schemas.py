from pydantic import BaseModel, Field, model_validator
from datetime import datetime
from typing_extensions import Self

class ShiftCreate(BaseModel):
    contractor_id: int
    client_company: str = Field(min_length=1, description="Client company name cannot be blank.")
    time_left_home: datetime
    time_reached_company: datetime | None = None
    time_finished_company: datetime | None = None
    time_reached_home: datetime
    km_driven: float = Field(ge=0, description="Distance cannot be negative.")
    overnight_stay: bool
    only_travel_day: bool

    @model_validator(mode="after")  
    def verify_shift_timeline(self) -> Self:
        
        if (self.time_reached_company is None) != (self.time_finished_company is None):
            raise ValueError(
                "Incomplete shift records. If you log an arrival time at the company, "
                "you must also log a completion time (and vice-versa)."
            )
        
        duration = self.time_reached_home - self.time_left_home
        if duration.total_seconds() > 24*3600:
            raise ValueError("Shift duration cannot exceed 24 hours. Please log multi-day deployments as separate daily shifts.")

        if self.time_reached_company and self.time_finished_company:
            if self.time_left_home >= self.time_reached_company:
                raise ValueError("Departure time from home must be before arrival at client.")
            if self.time_reached_company >= self.time_finished_company:
                raise ValueError("Arrival time must be before shift completion.")
            if self.time_finished_company >= self.time_reached_home:
                raise ValueError("Shift completion must be before arrival back home.")
        else:
            if self.time_left_home >= self.time_reached_home:
                raise ValueError("Departure time from home must be before arrival back home.")

        return self

class ContractorCreate(BaseModel):
    name: str = Field(min_length=1, description="Contractor name cannot be empty.")
    base_rate: float = Field(gt=0, description="Base pay rate must be greater than zero.")

from pydantic import BaseModel, Field

class ContractorPayoutSummary(BaseModel):
    contractor_id: int = Field(..., description="The unique identifier of the medical contractor")
    total_shifts_worked: int = Field(..., description="Total count of completed historical shifts")
    total_accumulated_hours: float = Field(..., description="Total cumulative hours across all shifts")
    aggregate_mileage_payout: float = Field(..., description="Total tax-free travel reimbursement paid out")
    aggregate_hotel_payout: float = Field(..., description="Total hotel stipends accumulated")
    aggregate_shift_stipend: float = Field(..., description="Total long-duration shift stipends accumulated")
    total_tax_free_reimbursements: float = Field(..., description="Sum total of all tax-free payouts")

    class Config:
        from_attributes = True