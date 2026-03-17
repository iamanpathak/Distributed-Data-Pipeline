from fastapi import FastAPI, Depends, Request, HTTPException
from sqlalchemy.orm import Session
from celery import Celery
from celery.result import AsyncResult
from api.database import init_db, SessionLocal, JobRecord
import uuid
import json
import redis

# Redis Cache connection
redis_client = redis.Redis(host='redis', port=6379, db=0, decode_responses=True)

app = FastAPI(title="Distributed Data Pipeline API")
init_db()

# Configure Celery to talk to Redis
# 'redis:6379' is the internal Docker hostname and port for our queue
celery_app = Celery(
    "tasks",
    broker="redis://redis:6379/0",
    backend="redis://redis:6379/0"
)

@app.post("/submit-job")
def submit_job(request: Request, data_size: int = 5):
    """Submits a job, but protected by Redis Rate Limiting!"""
    
    # 1. Extract the client's IP address
    client_ip = request.client.host
    redis_key = f"rate_limit:{client_ip}"
    
    # 2. Increment the request count for this IP in Redis
    request_count = redis_client.incr(redis_key)
    
    # 3. If it's the first request, set a 60-second TTL (Time-To-Live)
    if request_count == 1:
        redis_client.expire(redis_key, 60)
        
    # 4. THE BLOCKER: Block the request if the count exceeds 5 per minute!
    if request_count > 5:
        print(f"SECURITY ALERT: Rate limit exceeded for IP: {client_ip}")
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please wait 60 seconds before submitting new jobs.")

    # 5. GENERATE UNIQUE ID (Prevents overlapping points in the UI graph)
    import uuid
    new_job_id = f"JOB-{str(uuid.uuid4())[:6]}"
    
    # Send to Celery
    task = celery_app.send_task("worker.tasks.process_heavy_data", args=[new_job_id, data_size])
    return {"message": "Job successfully sent to the Vault processing queue!", "job_id": task.id}


@app.get("/job-status/{job_id}")
async def get_job_status(job_id: str):
    """
    Endpoint to check the status of a background job.
    """
    # Fetch the task result from Redis using the job_id
    task_result = AsyncResult(job_id, app=celery_app)
    
    # task_result.state will tell us if it's PENDING, SUCCESS, or FAILURE
    # task_result.info contains the data returned by the worker when finished
    return {
        "job_id": job_id,
        "status": task_result.state,
        "result": task_result.info if task_result.state == "SUCCESS" else None
    }

# --- Database session dependency setup ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/all-jobs")
def get_all_jobs(db: Session = Depends(get_db)):
    # 1. CHECK THE REDIS CACHE FIRST
    cached_data = redis_client.get("vault_cache")
    if cached_data:
        print("⚡ SPEED DEMON: Serving from Redis Cache! (0.001 seconds)")
        return json.loads(cached_data)

    # 2. IF CACHE IS EMPTY, FETCH FROM THE POSTGRESQL VAULT
    print("🐢 SLOW MO: Fetching from PostgreSQL Vault...")
    jobs = db.query(JobRecord).all()
    
    jobs_history = []
    for job in jobs:
        # Format the timestamp into a clean string (YYYY-MM-DD HH:MM:SS)
        time_str = job.created_at.strftime("%Y-%m-%d %H:%M:%S") if job.created_at else "N/A"
        
        jobs_history.append({
            "job_id": job.job_id,
            "status": job.status,
            "data_size": job.data_size,
            "result_data": job.result_data,
            "created_at": time_str  # <--- Appended created_at timestamp
        })
        
    response_data = {
        "total_jobs_completed": len(jobs),
        "jobs_history": jobs_history
    }
    
    # 3. AFTER FETCHING FROM DB, SAVE RESULTS IN REDIS CACHE FOR 10 SECONDS
    redis_client.setex("vault_cache", 10, json.dumps(response_data))
    
    return response_data