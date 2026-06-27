# Automated Event-Driven Payroll & Analytics Pipeline

An end-to-end serverless data engineering pipeline that automates the ingestion, transformation, calculation, and serving of occupational health contractor shift data. This system transitions raw operational CSV data into a fully optimized star-schema analytics data warehouse.

## Architecture Overview

The pipeline leverages a decoupled, event-driven architecture designed for infinite scalability and low idle costs:

1. **Ingestion (Bronze):** Raw contractor shifts are uploaded to an Amazon S3 bucket.
2. **Serverless ETL (Silver):** An S3 event notification triggers an AWS Lambda function, initializing an AWS Glue Spark job that schema-validates, sanitizes, and cleans the dataset before appending it to a Silver S3 bucket.
3. **Application Ingestion:** A secondary AWS Lambda function acts as a webhook, issuing an HTTP POST request to a FastAPI application running on AWS ECS Fargate.
4. **Calculations & Storage:** The container downloads the clean file, computes specialized payroll premiums and taxable/non-taxable metrics via Python logic, and safely writes records to an Amazon RDS PostgreSQL database.
5. **Data Transformation (Gold):** dbt (Data Build Tool) transforms raw database tables into pre-computed analytics marts structured for instant dashboard consumption.

## Tech Stack

* **Storage / Lakehouse:** Amazon S3 (Bronze & Silver Layers)
* **Compute / Orchestration:** AWS Glue (Apache Spark), AWS Lambda, AWS ECS Fargate
* **API / Backend Framework:** FastAPI (Uvicorn), Python 3.12, Pydantic, SQLAlchemy
* **Database / Warehouse:** Amazon RDS (PostgreSQL)
* **Data Transformation & Modeling:** dbt (Data Build Tool)
* **Containerization:** Docker, Docker Compose, AWS ECR

## Key Engineering Features

### 🛠️ Idempotency & Deduplication Guard
To protect the analytics layer from network retries or duplicate user uploads, an inside-the-loop deduplication guard is implemented within the FastAPI ingestion layer. Before executing database writes or resource-intensive business logic, the application verifies the data uniqueness:
```python
duplicate_check = db.query(models.Shift).filter(
    models.Shift.contractor_id == shift_data.contractor_id,
    models.Shift.time_left_home == shift_data.time_left_home
).first()

if duplicate_check:
    continue # Safely bypasses reprocessing and prevents record duplication
