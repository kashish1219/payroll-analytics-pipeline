from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

class Shift(Base):

    __tablename__ = "shifts"

    id = Column(Integer, primary_key=True, index=True)
    contractor_id = Column(Integer, ForeignKey("contractors.id"), nullable=False)
    client_company = Column(String, nullable=False)
    time_left_home = Column(DateTime, nullable=False)
    time_reached_company = Column(DateTime)
    time_finished_company = Column(DateTime)
    time_reached_home = Column(DateTime, nullable=False)
    km_driven = Column(Float, nullable=False, default=0.0)
    overnight_stay = Column(Boolean, nullable=False)
    only_travel_day = Column(Boolean, default=False, nullable=False)


    total_hours = Column(Float, nullable=False)
    regular_hours = Column(Float, nullable=False)
    premium_hours = Column(Float, nullable=False)
    taxable_wages = Column(Float, nullable=False)
    tax_free_reimbursements = Column(Float, nullable=False)
    total_take_home = Column(Float, nullable=False)


class Contractor(Base):

    __tablename__ = "contractors"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    base_rate = Column(Float, nullable=False)


class GoldContractorPayout(Base):
    __tablename__ = "gold_contractor_payouts"

    contractor_id = Column(Integer, primary_key=True, index=True)
    total_shifts_worked = Column(Integer, nullable=False)
    total_accumulated_hours = Column(Float, nullable=False)
    aggregate_mileage_payout = Column(Float, nullable=False)
    aggregate_hotel_payout = Column(Float, nullable=False)
    aggregate_shift_stipend = Column(Float, nullable=False)
    total_tax_free_reimbursements = Column(Float, nullable=False)
    last_synced_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())