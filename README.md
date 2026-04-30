# Distributed Data Pipeline: Resilience, Scalability & Monitoring

[![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Gateway-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Celery](https://img.shields.io/badge/Celery-Distributed_Tasks-37814A?logo=celery&logoColor=white)](https://docs.celeryq.dev/)
[![Redis](https://img.shields.io/badge/Redis-Broker_&_Cache-DC382D?logo=redis&logoColor=white)](https://redis.io/)
[![Docker](https://img.shields.io/badge/Docker-Containerized-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow)](https://opensource.org/licenses/MIT)

Hey! I’m Aman. I built this project to demonstrate how a production-grade data pipeline handles massive workloads while staying resilient. Instead of a simple script, I engineered a decoupled microservices architecture to ensure that no matter how hard the system crashes, your data remains safe in the "Vault."

---

## 🏗️ System Architecture & Data Flow

I designed this with a "fail-safe" mindset. Each component is isolated so that a crash in one node doesn't halt the entire pipeline.

```text
[Streamlit UI] ──(HTTP POST)──> [FastAPI Gateway]
                                           │
                                           ▼
                 ┌───────────────────────────────────────────────────┐
                 ▼                                                   ▼
          [Redis Cache]                                        [Redis Broker]
        (Rate Limiter/429)                                   (Task Distribution)
                                                                     │
                                                                     ▼
                                                          [Celery Workers (x3)]
                                                         (Distributed Execution)
                 ┌───────────────────────────────────────────────────┴────────────────┐
                 ▼                                                                    ▼
       [PostgreSQL Vault]                                                   [Auto-Retry Logic]
       (Success/DLQ Storage)                                               (Exponential Backoff)
                                                                                      │
                                                                                      ▼
                                                                               [Discord Alerts]
                                                                             (Fatal Failure Hook)
```

---

## 🔄 The Request Lifecycle
1. **The Entry Point:** Jobs are submitted via the Streamlit dashboard or FastAPI Swagger.
2. **Safety First:** I’ve integrated Redis to enforce IP-based rate limiting to prevent API abuse.
3. **Fire & Forget:** FastAPI assigns a JOB-ID and pushes tasks to Redis, returning a response instantly.
4. **Heavy Lifting:** 3 Scalable Celery Workers process tasks in parallel to maximize throughput.
5. **Handling Chaos:** If a task hits a network snag, logic triggers an Exponential Backoff strategy.
6. **The Vault (DLQ):** Results are saved in PostgreSQL; failures are routed to a Dead Letter Queue and Discord.

---

## 📸 System in Action

*Note: These are live captures from my development environment showing the system under load.*

### 1. Central Command Center
The Streamlit dashboard for real-time monitoring of processing loads and system health metrics.
<p align="center"><img src="assets/dashboard.png" width="900"></p>

### 2. Smart Rate Limiting
Protection in action-this is what happens when the Redis-backed request limit is breached.
<p align="center"><img src="assets/rate-limiting.png" width="900"></p>

### 3. Distributed Worker Cluster (Flower)
Monitoring 3 concurrent worker nodes handling parallel execution to maximize throughput.
<p align="center"><img src="assets/celery-workers.png" width="900"></p>

### 4. Resilience & Observability (Discord)
The automatic retry sequence (2s -> 4s -> 8s) before a Fatal Failure is logged.
<p align="center"><img src="assets/discord-alert.png" width="900"></p>

### 5. The PostgreSQL Vault
A peek into the persistent storage where the system tracks every SUCCESS and FAILURE.
<p align="center"><img src="assets/vault-records.png" width="900"></p>

### 6. Automated ETL Pipeline (Celery Beat)
An automated Celery Beat daemon extracting, transforming, and loading live crypto prices into the Vault.
<p align="center"><img src="assets/live-crypto-etl.png" width="900"></p>

### 7. Dead Letter Queue (DLQ) Audit
A direct SQL audit proving that every failed job is preserved for manual recovery.
<p align="center"><img src="assets/database-dlq.png" width="900"></p>

### 8. Interactive API Blueprint
The FastAPI Swagger UI providing an interactive map for third-party integrations.
<p align="center"><img src="assets/api-docs.png" width="900"></p>

---

## 📂 Project Structure

```text
distributed-data-pipeline/
├── api/                  # FastAPI Gateway & Rate Limiting
│   ├── database.py       # SQLAlchemy Models & DB Connection
│   ├── main.py           # Entry point & API Routes
│   └── requirements.txt  # API-specific dependencies
├── assets/               # Live System Screenshots for documentation
├── ui/                   # Monitoring Dashboard (Streamlit)
│   ├── app.py            # Real-time Metrics & Vault UI
│   └── requirements.txt  # UI-specific dependencies
├── worker/               # Distributed Task Execution (Celery)
│   ├── database.py       # SQLAlchemy Models for worker node
│   ├── tasks.py          # Heavy logic, Backoff & Chaos Testing
│   └── requirements.txt  # Worker-specific dependencies
├── .env.example          # Template for environment variables & Webhooks
├── docker-compose.yml    # Multi-container Orchestration
├── LICENSE               # MIT License file
└── README.md             # Project documentation
```

---

## 🔥 Why This Pipeline is Robust

- **Fault Tolerance:** Uses an Exponential Backoff formula (2^n) to avoid overwhelming services.
- **Chaos Engineering:** Built-in logic simulating a 50% failure rate to prove system resilience.
- **Zero Data Loss:** All failed tasks are captured in the Dead Letter Queue (PostgreSQL).
- **Sub-Millisecond Caching:** Dashboard metrics are served from Redis RAM for extreme speed.
- **Scalable by Design:** Scale from 1 to 100+ workers by adjusting a single Docker parameter.

---

## 🧠 Design Decisions

- **Cumulative Metrics:** All system metrics (Total Jobs Processed, Total Data Handled) are intentionally cumulative to reflect continuous system load and real-world pipeline behavior. Reset functionality can be extended if required, but data retention is prioritized for observability and debugging.

- **Data Integrity Handling:** The system ignores invalid or negative data inputs during processing to ensure that only meaningful, positive workloads are executed and reflected in system metrics. This prevents distortion of performance insights and maintains consistency in analytics.

---

## 🚀 Get it Running Locally

1. **Clone & Setup**

```bash
git clone https://github.com/iamanpathak/distributed-data-pipeline.git
cd distributed-data-pipeline
cp .env.example .env # Add your Discord Webhook URL here
```

2. **Launch Infrastructure**
```bash
docker-compose up -d --build --scale worker=3
```

3. **Explore the Services**
* **Live Dashboard:** http://localhost:8501
* **API Swagger Docs:** http://localhost:8000/docs
* **Celery Task Monitor (Flower):** http://localhost:5555

---

## 📄 License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for details.

<p align="center">
  Made with ❤️ by <a href="https://github.com/iamanpathak">Aman Pathak</a>
</p>