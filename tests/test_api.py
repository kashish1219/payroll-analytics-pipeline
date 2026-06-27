from pyexpat import model
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
import models

def test_create_contractor_endpoint(client: TestClient):
    # 1. ARRANGE
    payload = {
        "name": "Kashish",
        "base_rate": 35.0
    }
    
    # 2. ACT
    response = client.post("/contractor", json=payload)
    
    # 3. ASSERT
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "success"
    assert "contractor_id" in json_data


def test_create_shift_endpoint(client: TestClient, db_session: Session):
    # 1. ARRANGE: Populate the empty RAM database with a contractor profile first
    mock_contractor = models.Contractor(name="Test Technician", base_rate=30.0)
    db_session.add(mock_contractor)
    db_session.commit()
    db_session.refresh(mock_contractor)
    
    # Build a valid shift payload linking back to the auto-generated ID
    shift_payload = {
        "contractor_id": mock_contractor.id,
        "client_company": "Workplace Medical Corp",
        "time_left_home": "2026-06-10T06:00:00",
        "time_reached_company": "2026-06-10T07:00:00",
        "time_finished_company": "2026-06-10T15:00:00",
        "time_reached_home": "2026-06-10T16:00:00",
        "km_driven": 45.5,
        "overnight_stay": False,
        "only_travel_day": False
    }

    # 2. ACT: Blast the payload at the server endpoint
    response = client.post("/shift", json=shift_payload)

    # 3. ASSERT: Verify the pipeline worked seamlessly end-to-end
    assert response.status_code == 200
    
    json_data = response.json()
    assert json_data["status"] == "success"
    assert "shift_id" in json_data
    assert "payroll" in json_data
    
    # Deep assertion: Verify the calculation engine executed correctly through the network layer
    payroll = json_data["payroll"]
    assert payroll["total_hours"] == 10.0
    assert payroll["taxable_wages"] == 330.0  # 10 hours * $30.0/hr

def test_create_summary_endpoint(client: TestClient, db_session: Session):

    #Arrange
    mock_contractor = models.Contractor(name="Test Contractor", base_rate=30.0)
    db_session.add(mock_contractor)
    db_session.commit()
    db_session.refresh(mock_contractor)

    mock_shift_1 = {
        "contractor_id": mock_contractor.id,
        "client_company": "Workplace Medical Corp",
        "time_left_home": "2026-06-10T06:00:00",
        "time_reached_company": "2026-06-10T07:00:00",
        "time_finished_company": "2026-06-10T15:00:00",
        "time_reached_home": "2026-06-10T16:00:00",
        "km_driven": 45.5,
        "overnight_stay": False,
        "only_travel_day": False
    }

    mock_shift_2 = {
        "contractor_id": mock_contractor.id,
        "client_company": "Workplace Medical Corp",
        "time_left_home": "2026-06-10T06:00:00",
        "time_reached_company": "2026-06-10T07:00:00",
        "time_finished_company": "2026-06-10T15:00:00",
        "time_reached_home": "2026-06-10T16:00:00",
        "km_driven": 45.5,
        "overnight_stay": False,
        "only_travel_day": False
    }

    client.post("/shift", json=mock_shift_1)
    client.post("/shift", json=mock_shift_2)
    #Act
    response = client.get(f"/summary/{mock_contractor.id}")

    #Assert
    json_data = response.json()
    assert json_data["lifetime_t4a_wages"] == 660.0  
    assert json_data["total_hours_worked"] == 20.0   # 10hrs + 10hrs
