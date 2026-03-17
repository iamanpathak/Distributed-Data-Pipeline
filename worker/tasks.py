import datetime
import time
from datetime import timezone
import random
from worker.database import SessionLocal, JobRecord
from celery import Celery
import uuid
import requests
from celery.exceptions import MaxRetriesExceededError
import os

# Ensure the Webhook URL is loaded securely from the environment variables
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "YOUR_DISCORD_WEBHOOK_URL_HERE")

def send_discord_alert(message):
    """Sends a live push notification to the configured Discord channel."""
    try:
        data = {"content": message}
        requests.post(DISCORD_WEBHOOK_URL, json=data)
    except Exception as e:
        print(f"Discord Alert Failed: {e}")

# 1. Connect Celery to Redis (Message Broker & Result Backend)
# 'redis:6379' is the internal Docker hostname and port for the queue
celery_app = Celery(
    "tasks",
    broker="redis://redis:6379/0",
    backend="redis://redis:6379/0"
)

# 2. Register the function as a Celery background task
# bind=True and max_retries=3 enable the task to handle its own retry logic
@celery_app.task(bind=True, max_retries=3, name="worker.tasks.process_heavy_data")
def process_heavy_data(self, job_id: str, data_size: int):
    """Processes data and persists the result to the database on success OR failure (DLQ)."""
    print(f"[{job_id}] Worker received task. Size: {data_size}MB")
    
    try:
        # Simulate heavy lifting
        time.sleep(data_size)
        
        # CHAOS MONKEY: 50% chance to simulate a crash for resilience testing
        if random.choice([True, False]):
            attempt_num = self.request.retries + 1
            error_msg = f"🚨 **CRITICAL ALERT:** Job `{job_id}` crashed on attempt {attempt_num}! Retrying..."
            print(error_msg)
            send_discord_alert(error_msg)
            raise ValueError("Simulated Network Error")
            
        # SUCCESS PATH: Persist record to Database
        db = SessionLocal()
        try:
            new_record = JobRecord(
                job_id=job_id,
                status="SUCCESS",
                data_size=data_size,
                result_data="Successfully processed and cleaned.",
                created_at=datetime.datetime.now(timezone.utc)
            )
            db.add(new_record)
            db.commit()
            print(f"[{job_id}] ✅ RECORD SAVED TO VAULT!")
        except Exception as e:
            db.rollback()
        finally:
            db.close()
            
        return f"Processed {data_size}MB for {job_id}"

    except Exception as exc:
        print(f"[{job_id}] ⚠️ Task Failed! Retrying...")
        try:
            # Re-queue the task with a 2-second countdown before the next attempt
            self.retry(exc=exc, countdown=2)
        except MaxRetriesExceededError:
            # DEAD LETTER QUEUE (DLQ) PATH: All retries exhausted
            fatal_msg = f"💀 **PERMANENT FAILURE:** Job `{job_id}` is completely dead. Moving to DLQ Vault."
            print(fatal_msg)
            send_discord_alert(fatal_msg)
            
            # Persist the FAILED state to the Database to ensure zero data loss
            db = SessionLocal()
            try:
                failed_record = JobRecord(
                    job_id=job_id,
                    status="FAILED",  # Flagged for DLQ review
                    data_size=data_size,
                    result_data="DLQ: Task completely failed after 3 retries."
                )
                db.add(failed_record)
                db.commit()
            except Exception as db_exc:
                db.rollback()
            finally:
                db.close()
                
            return f"Job {job_id} failed permanently."

@celery_app.task(name="worker.tasks.scheduled_data_ingestion")
def scheduled_data_ingestion():
    """Automated daemon worker: Live Bitcoin Price ETL Pipeline"""
    auto_job_id = f"BTC-{str(uuid.uuid4())[:6]}"
    print(f"👻 GHOST WOKE UP! Fetching Live Crypto Data for {auto_job_id}...")
    
    try:
        # 1. EXTRACT (Simulating API fetch latency)
        time.sleep(1.5) 
        # Generating a realistic live Bitcoin price
        usd_price = round(random.uniform(64000.50, 68000.99), 2) 
        
        # 2. TRANSFORM (Apply clean data formatting)
        import datetime
        time_updated = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        final_clean_data = f"Bitcoin Price: ${usd_price} (Time: {time_updated})"
        
        # 3. LOAD (Persist formatted data into PostgreSQL Vault)
        db = SessionLocal()
        try:
            new_record = JobRecord(
                job_id=auto_job_id,
                status="SUCCESS",
                data_size=1, # Simulated 1 API call payload size
                result_data=final_clean_data
            )
            db.add(new_record)
            db.commit()
            print(f"[{auto_job_id}] 📈 LIVE BTC PRICE SAVED TO VAULT! 🚀")
        except Exception as e:
            db.rollback()
            print(f"DB Error: {e}")
        finally:
            db.close()
            
    except Exception as e:
        print(f"👻 Ghost failed to fetch Crypto Data: {e}")
        
    return "Automated Crypto ETL task complete"