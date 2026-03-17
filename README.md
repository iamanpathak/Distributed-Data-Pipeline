# Distributed Data Pipeline Architecture

An end-to-end, resilient, and highly available data processing pipeline built on a decoupled microservices architecture. 

Rather than relying on a single server, this system is designed to ingest, process, and store large volumes of data across multiple isolated compute nodes. It actively breaks down heavy workloads into asynchronous tasks, ensuring that data flows continuously without bottlenecking the main application.

Engineered to handle these workloads in real-time, the architecture is built to survive partial node crashes, mitigate severe traffic spikes via API rate-limiting, and guarantee data integrity. It demonstrates production-grade engineering principles including distributed message brokering, automated ETL (Extract, Transform, Load) processes, high-speed volatile caching, and zero-data-loss failure handling through Dead Letter Queues (DLQ), all monitored via a real-time telemetry dashboard.

## System Architecture & Data Flow

The system is designed with a decoupled microservices architecture to ensure high availability and prevent bottlenecks during heavy data processing.

```text
    [Streamlit UI] ──(HTTP POST)──> [FastAPI Gateway]
                                         │
                                         ├─(Rate Limiter)─> [Redis Cache] (Blocks DDoS)
                                         │
                                         └─(Queue Task)───> [Redis Broker]
                                                                 │
                                                                 v
                                                         [Celery Workers] (Scalable Nodes)
                                                                 │
                                                                 ├─(Success)─> [PostgreSQL Vault]
                                                                 │
                                                                 ├─(Crash)───> [Auto-Retry Logic]
                                                                 │
                                                                 └─(Failure)─> [DLQ (Failed Status)] ──> [Discord Alert]
```

### Request Lifecycle
1. **Client Request:** A user submits a job via the Streamlit dashboard.
2. **API Gateway & Security:** FastAPI receives the request. It first checks Redis to enforce IP-based rate limiting. If the limit is exceeded, a `429 Too Many Requests` is returned.
3. **Task Delegation:** If validated, FastAPI assigns a unique `JOB-ID` and pushes the task to the Redis message broker. FastAPI immediately returns a 200 OK response to the client, keeping the gateway unblocked.
4. **Asynchronous Processing:** A pool of Celery workers continuously polls Redis. An available worker picks up the job and begins heavy computation.
5. **Fault Tolerance & DLQ:** If a network failure or processing error occurs, the worker automatically retries the task (up to 3 times) with exponential backoff. If all retries fail, the task is routed to a Dead Letter Queue (DLQ) strategy, saving the record as `FAILED` in PostgreSQL, and firing a live Discord Webhook alert.
6. **Data Persistence & Analytics:** Upon success, the clean data is committed to the PostgreSQL Vault. When the client requests analytics, FastAPI fetches the data from PostgreSQL and caches it in Redis for sub-millisecond retrieval on subsequent calls.

## Core Engineering Features

* **Fault Tolerance & Auto-Healing:** Implements `max_retries` with countdown for transient network failures.
* **Dead Letter Queue (DLQ):** Tasks that fail consistently are caught and logged into the database Vault with a `FAILED` state to ensure zero data loss.
* **API Rate Limiting:** Redis-backed request throttling (e.g., max 5 requests/minute per IP) to prevent DDoS attacks and API abuse.
* **Sub-Millisecond Caching:** Frequent dashboard queries are served directly from Redis RAM, bypassing the PostgreSQL disk entirely.
* **Automated ETL (Celery Beat):** Scheduled cron jobs that extract, transform, and load simulated external API data at regular intervals.
* **Real-time Alerting:** Integration with Discord Webhooks for immediate production-level alerts on critical system failures.

## Technology Stack

* **Backend Gateway:** Python 3.10, FastAPI, SQLAlchemy
* **Message Broker & Cache:** Celery, Redis
* **Database Vault:** PostgreSQL 15
* **Monitoring UI:** Streamlit, Pandas
* **Infrastructure & Containerization:** Docker, Docker Compose

## Local Setup & Deployment

### 1. Clone the repository
```bash
git clone [https://github.com/iamanpathak/Distributed-Data-Pipeline.git](https://github.com/iamanpathak/Distributed-Data-Pipeline.git)
cd Distributed-Data-Pipeline
```

### 2. Configure Environment Variables
Create a `.env` file in the root directory using the provided template to enable Discord alerts:
```bash
cp .env.example .env
# Edit .env to add your actual Discord Webhook URL
```

### 3. Build and Spin Up the Cluster
This command provisions the database, cache, API, UI, and scales the worker nodes to 3 concurrent processes.
```bash
docker-compose up --build --scale worker=3
```

### 4. Access the Services
* **Live Dashboard:** `http://localhost:8501`
* **API Swagger Docs:** `http://localhost:8000/docs`
* **Celery Task Monitor (Flower):** `http://localhost:5555`