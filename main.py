from datetime import datetime, timedelta
from datetime import timedelta
import re
from fastapi import FastAPI, Depends, HTTPException, status
from database import get_db, engine
import schemas
import calculation
import models
from sqlalchemy.orm import Session
import boto3
import csv
from io import StringIO
from routers import analytics


app = FastAPI(title="Medical Contractor Pipeline")


@app.get("/")
def read_root():
    """
    A simple baseline check to verify API server is alive
    """
    return {
        "status": "healthy",
        "app": "Medical Contractor Pipeline Backend",
        "version": "1.0.0"
    }

@app.post("/contractor")
def create_contractor(contractor_data:schemas.ContractorCreate, db: Session = Depends(get_db)):
    try:
        db_row = models.Contractor(
            name=contractor_data.name,
            base_rate=contractor_data.base_rate
        )
        db.add(db_row)
        db.commit()
        db.refresh(db_row)
        return {
            "status": "success",
            "contractor_id": db_row.id,
            "base_rate": contractor_data.base_rate
        }
    except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database insertion failed: {str(e)}"
            )

@app.post("/shift")
def create_shift(shift_data: schemas.ShiftCreate, db: Session = Depends(get_db)):
    try:
        contractor_profile = db.query(models.Contractor).filter(models.Contractor.id == shift_data.contractor_id).first()
        if not contractor_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Contractor Profile with ID {shift_data.contractor_id} does not exist. Shift rejected."
            )
        
        base_rate = contractor_profile.base_rate

        payroll_calculation = calculation.calculate_shift_payout(shift_data, base_rate)

        db_row = models.Shift(
            contractor_id=shift_data.contractor_id,
            client_company=shift_data.client_company,
            time_left_home=shift_data.time_left_home,
            time_reached_company=shift_data.time_reached_company,
            time_finished_company=shift_data.time_finished_company,
            time_reached_home=shift_data.time_reached_home,
            km_driven=shift_data.km_driven,
            overnight_stay=shift_data.overnight_stay,
            only_travel_day=shift_data.only_travel_day,

            total_hours=payroll_calculation["total_hours"],
            regular_hours=payroll_calculation["regular_hours"],
            premium_hours=payroll_calculation["premium_hours"],
            taxable_wages=payroll_calculation["taxable_wages"],
            tax_free_reimbursements=payroll_calculation["tax_free_reimbursements"],
            total_take_home=payroll_calculation["total_take_home"]
            )

        db.add(db_row)
        db.commit()
        db.refresh(db_row)

        return {
            "status": "success",
            "shift_id": db_row.id,
            "payroll": payroll_calculation
        }
    except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database insertion failed: {str(e)}"
            )

@app.get("/summary/{contractor_id}")
def get_contractor_summary(contractor_id: int, db: Session = Depends(get_db)):
    
    try:
        anchor_date = datetime(2026, 5, 24)
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        total_days_passed = (today - anchor_date).days
        full_cycles_passed = total_days_passed // 14
        
        current_period_start = anchor_date + timedelta(days=full_cycles_passed * 14)

        
        all_shifts = db.query(models.Shift).filter(models.Shift.contractor_id == contractor_id).all()
        contractor_profile = db.query(models.Contractor).filter(models.Contractor.id == contractor_id).first()
        
        if not contractor_profile:
            raise HTTPException(status_code=404, detail="Contractor not found")

       
        t4_wage = 0.0
        biweekly_wages = 0.0
        total_km = 0.0
        total_hours = 0.0

        for shift in all_shifts:
            t4_wage += shift.taxable_wages 
            total_hours += shift.total_hours
            total_km += shift.km_driven
            
            if shift.time_left_home >= current_period_start:
                biweekly_wages += shift.total_take_home

        return {
            "contractor_name": contractor_profile.name,
            "lifetime_t4a_wages": round(t4_wage, 2),
            "total_km": round(total_km, 2),
            "total_hours_worked": round(total_hours, 2),
            "pending_paycheck_wages": round(biweekly_wages, 2),
            "pay_period_started": current_period_start.strftime("%Y-%m-%d")
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/process-s3-batch")
def process_s3_batch(event_payload: dict, db: Session = Depends(get_db)):
    try:
        detail = event_payload.get("detail", {})
        bucket_name = detail.get("bucket", {}).get("name")
        object_key = detail.get("object", {}).get("key")

        if not bucket_name or not object_key:
            raise HTTPException(status_code=400, detail="Invalid S3 event payload format")

        s3_client = boto3.client('s3')
        csv_obj = s3_client.get_object(Bucket=bucket_name, Key=object_key)
        body = csv_obj['Body'].read().decode('utf-8')

        csv_reader = csv.DictReader(StringIO(body))
        inserted_records = 0  

        for row in csv_reader:
            
            overnight = str(row["overnight_stay"]).strip().lower() == "true"
            only_travel = str(row["only_travel_day"]).strip().lower() == "true"

            shift_data = schemas.ShiftCreate(
                contractor_id=int(row["contractor_id"]),
                client_company=row["client_company"],
                time_left_home=datetime.fromisoformat(row["time_left_home"]),
                time_reached_company=datetime.fromisoformat(row["time_reached_company"]),
                time_finished_company=datetime.fromisoformat(row["time_finished_company"]),
                time_reached_home=datetime.fromisoformat(row["time_reached_home"]),
                km_driven=float(row["km_driven"]),
                overnight_stay=overnight,
                only_travel_day=only_travel
            )

            duplicate_check = db.query(models.Shift).filter(
                models.Shift.contractor_id == shift_data.contractor_id,
                models.Shift.time_left_home == shift_data.time_left_home
            ).first()

            if duplicate_check:
                print(f"--> [SKIP] Shift already exists for Contractor ID {shift_data.contractor_id} on {shift_data.time_left_home}. Passing on it.")
                continue

            
            contractor_profile = db.query(models.Contractor).filter(models.Contractor.id == shift_data.contractor_id).first()
            if not contractor_profile:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Contractor Profile with ID {shift_data.contractor_id} does not exist. Shift rejected."
                )
                
            base_rate = contractor_profile.base_rate    
            payroll_calculation = calculation.calculate_shift_payout(shift_data, base_rate)

            db_row = models.Shift(
                contractor_id=shift_data.contractor_id,
                client_company=shift_data.client_company,
                time_left_home=shift_data.time_left_home,
                time_reached_company=shift_data.time_reached_company,
                time_finished_company=shift_data.time_finished_company,
                time_reached_home=shift_data.time_reached_home,
                km_driven=shift_data.km_driven,
                overnight_stay=shift_data.overnight_stay,
                only_travel_day=shift_data.only_travel_day,

                total_hours=payroll_calculation["total_hours"],
                regular_hours=payroll_calculation["regular_hours"],
                premium_hours=payroll_calculation["premium_hours"],
                taxable_wages=payroll_calculation["taxable_wages"],
                tax_free_reimbursements=payroll_calculation["tax_free_reimbursements"],
                total_take_home=payroll_calculation["total_take_home"]
            )

            db.add(db_row)
            inserted_records += 1
            
        
        db.commit()

        return {"status": "success", "processed_records": inserted_records}

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch processing failed: {str(e)}"
        )

app.include_router(analytics.router)