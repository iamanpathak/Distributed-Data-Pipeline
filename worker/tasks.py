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

# Security Best Practice: Fetching the Webhook URL from environment variables to avoid hardcoding secrets
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "YOUR_DISCORD_WEBHOOK_URL_HERE")

def send_discord_alert(message):
    """
    Dispatches a real-time notification to the configured Discord channel.
    Includes sanitization to handle potential whitespace in environment variables.
    """
    if not DISCORD_WEBHOOK_URL:
        return

    try:
        # Sanitize the URL to remove any accidental spaces or quotes from .env
        clean_url = DISCORD_WEBHOOK_URL.strip().replace('"', '').replace("'", "")
        
        data = {"content": message}
        response = requests.post(clean_url, json=data, timeout=5)
        
        # Log the response status for internal debugging
        print(f"DEBUG: Discord Webhook Response Code: {response.status_code}")
    except Exception as e:
        print(f"ERROR: Failed to send Discord alert: {e}")

# 1. Connect Celery to Redis (Message Broker & Result Backend)
# 'redis:6379' is the internal Docker hostname and port for the queue
celery_app = Celery(
    "tasks",
    broker="redis://redis:6379/0",
    backend="redis://redis:6379/0"
)

celery_app.conf.beat_schedule = {
    "fetch-btc-price-every-2-min": {
        "task": "worker.tasks.scheduled_btc_ingestion",
        "schedule": 120.0,  # Executes the BTC data ingestion task every 2 minutes
    },
    "fetch-eth-price-every-3-min": {
        "task": "worker.tasks.scheduled_eth_ingestion",
        "schedule": 180.0,  # Executes the ETH data ingestion task every 3 minutes
    },
}

# Task Orchestration: Asynchronous processing with automated retry management.
# 'bind=True' allows the task to access its own execution state for custom retry logic.
@celery_app.task(bind=True, max_retries=3, name="worker.tasks.process_heavy_data")
def process_heavy_data(self, job_id: str, data_size: int):
    """
    This is the main function that does the heavy work. 
    It is designed to 'try again' automatically if it runs into an error.
    """
    print(f"[{job_id}] Worker received task. Size: {data_size}MB")
    
    try:
        # Step 1: Pretend to do hard work by waiting for a few seconds.
        # If a negative number is sent, this line will crash on purpose.
        time.sleep(data_size)
        
        # Step 2: Randomly crash 50% of the time.
        # This helps us test if our 'Retry' logic actually works.
        if random.choice([True, False]):
            attempt_num = self.request.retries + 1
            error_msg = f"🚨 **CRITICAL ALERT:** Job `{job_id}` crashed on attempt {attempt_num}! Retrying..."
            send_discord_alert(error_msg)
            raise ValueError("Simulated Network Error")
            
        # Step 3: If everything went well, save the 'SUCCESS' result to our Database.
        db = SessionLocal()
        try:
            new_record = JobRecord(
                job_id=job_id,
                status="SUCCESS",
                data_size=data_size,
                result_data="Job finished successfully!",
                created_at=datetime.datetime.now(timezone.utc)
            )
            db.add(new_record)
            db.commit()
            print(f"[{job_id}] SUCCESS: Result saved to the Vault.")
        except Exception as db_err:
            db.rollback()
            print(f"Database Error: {db_err}")
        finally:
            db.close()
            
        return f"Successfully processed {job_id}"

    except Exception as exc:
        # --- IF SOMETHING GOES WRONG ---
        
        # Count how many times we have already tried to fix this job.
        current_retry_count = self.request.retries
        
        # FINAL FAILURE: If we tried 3 times and still fail, give up.
        if current_retry_count >= self.max_retries:
            fatal_msg = (
                f"💀 **FATAL FAILURE**\n"
                f"Job `{job_id}` failed even after **{self.max_retries}** retries.\n"
                f"Giving up and moving this job to the 'Failed' list."
            )
            print(fatal_msg)
            send_discord_alert(fatal_msg)
            
            # Save the 'FAILED' status to the database so we know it didn't work.
            db = SessionLocal()
            try:
                failed_record = JobRecord(
                    job_id=job_id,
                    status="FAILED",
                    data_size=data_size,
                    result_data=f"Permanent Failure: {str(exc)}"
                )
                db.add(failed_record)
                db.commit()
            except Exception as db_exc:
                db.rollback()
                print(f"Database Error during Failure save: {db_exc}")
            finally:
                db.close()
                
            return f"Job {job_id} failed permanently."

        # RETRY LOGIC: Wait longer before each new try (2s, 4s, 8s, 16s).
        # This gives the system 'breathing room' to recover.
        next_delay = 2 ** (current_retry_count + 1)
        
        # Send a 'Warning' message to Discord to let us know a retry is happening.
        retry_alert = (
            f"⚠️ **EXPONENTIAL BACKOFF ACTIVE**\n"
            f"**Job ID:** `{job_id}` | **Status:** Retrying in **{next_delay}s**\n"
            f"**Reason:** `{str(exc)}`"
        )
        send_discord_alert(retry_alert)
        
        print(f"[{job_id}] Job failed. Trying again in {next_delay} seconds...")
        
        try:
            # Tell the system to try this job again after the wait time.
            self.retry(exc=exc, countdown=next_delay)
        except MaxRetriesExceededError:
            print(f"[{job_id}] No more retries left.")

@celery_app.task(name="worker.tasks.scheduled_btc_ingestion")
def scheduled_btc_ingestion():
    """Automated daemon worker: Live Bitcoin Price ETL Pipeline"""
    auto_job_id = f"BTC-{str(uuid.uuid4())[:6]}"
    print(f"👻 GHOST WOKE UP! Fetching Live BTC Data for {auto_job_id}...")
    
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
        print(f"👻 Ghost failed to fetch BTC Data: {e}")
        
    return "Automated BTC ETL task complete"

@celery_app.task(name="worker.tasks.scheduled_eth_ingestion")
def scheduled_eth_ingestion():
    """Automated daemon worker: Live Ethereum Price ETL Pipeline"""
    auto_job_id = f"ETH-{str(uuid.uuid4())[:6]}"
    print(f"👻 GHOST WOKE UP! Fetching Live ETH Data for {auto_job_id}...")
    
    try:
        # 1. EXTRACT (Simulating API fetch latency)
        time.sleep(1.2) 
        # Generating a realistic live Ethereum price
        usd_price = round(random.uniform(3400.50, 3800.99), 2) 
        
        # 2. TRANSFORM (Apply clean data formatting)
        import datetime
        time_updated = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        final_clean_data = f"Ethereum Price: ${usd_price} (Time: {time_updated})"
        
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
            print(f"[{auto_job_id}] 💎 LIVE ETH PRICE SAVED TO VAULT! 🚀")
        except Exception as e:
            db.rollback()
            print(f"DB Error: {e}")
        finally:
            db.close()
            
    except Exception as e:
        print(f"👻 Ghost failed to fetch ETH Data: {e}")
        
    return "Automated ETH ETL task complete"