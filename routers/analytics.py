from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
import models

router = APIRouter(prefix="/analytics", tags=["Analytics"])

@router.get("/summary")
def get_contractor_perfomance_summary(db: Session = Depends(get_db)):
    # The router does NO math. It just reads the table dbt already cooked.
    # PostgreSQL hands this over instantly with zero CPU strain.
    return db.execute("SELECT * FROM analytics.fct_contractor_summary;").fetchall()