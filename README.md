# 📚 Multi-Tenant Bookstore API - Developer Onboarding Guide

Welcome to the Bookstore API! This document contains the complete end-to-end explanation of the project's architecture, folder structure, and startup instructions so you can quickly explain the system to your team.

---

## 🏗️ 1. Project Overview & Architecture

This is a production-grade **Multi-Tenant REST API**. "Multi-tenant" means that this single application and single database serves many different bookstores (tenants) at the exact same time, while keeping their data completely invisible to each other.

To achieve blazing-fast performance and strict security, the architecture relies on:

1. **FastAPI**: The core web framework to handle asynchronous HTTP requests.
2. **PostgreSQL 16**: The permanent, relational database. We utilize **Row-Level Isolation**. Instead of spinning up a new database for every single company, all companies share the same database tables (`authors`, `books`, etc.). However, every row has a `tenant_id` attached to it.
3. **Redis 7**: An ultra-fast, in-memory database used for two things:
   - **Rate Limiting:** We use an atomic Lua script in Redis to calculate sliding-window rate limits (preventing companies from making too many API requests per minute).
   - **Caching:** We cache tenant credentials in Redis so we don't have to hit PostgreSQL on every single API request.
4. **SQLAlchemy 2.0**: The ORM that interacts with PostgreSQL. We wrote an advanced **Event Hook** (`do_orm_execute`) that automatically intercepts *every single database query* and injects a `WHERE tenant_id = '...' AND deleted_at IS NULL` clause. This guarantees data never leaks across companies, even if a developer forgets to filter it!

---

## 📂 2. Folder Structure Explanation

The project uses a standard, enterprise-grade Domain-Driven Design layout:

```text
bookstore-api/
├── app/                        # 🧠 Main Application Source Code
│   ├── main.py                 # The FastAPI application factory and route registration
│   ├── config.py               # Environment variable loading (Pydantic BaseSettings)
│   ├── database.py             # SQLAlchemy Async Engine and connection pooling
│   │
│   ├── routers/                # 🚦 API Endpoints (Controllers)
│   │   ├── admin.py            # Super-Admin routes to provision/delete tenants
│   │   ├── authors.py          # Tenant routes to manage authors
│   │   ├── books.py            # Tenant routes to manage books
│   │   └── categories.py       # Tenant routes to manage categories
│   │
│   ├── schemas/                # 📝 Pydantic Models (Input/Output Validation)
│   │   ├── author.py           # e.g., AuthorCreate, AuthorResponse, etc.
│   │   ├── book.py
│   │   └── tenant.py
│   │
│   ├── models/                 # 💾 Database Models (SQLAlchemy Tables)
│   │   ├── base.py             # **CRITICAL**: Contains the TenantScopedMixin & Security Event Hook
│   │   ├── author.py
│   │   ├── book.py
│   │   ├── category.py
│   │   └── tenant.py
│   │
│   ├── repositories/           # 🗄️ Database Access Layer (Direct SQL Interactions)
│   │   ├── base.py             # Base repository with common CRUD functions
│   │   └── ...                 # Author, Book, Category repos
│   │
│   ├── services/               # ⚙️ Business Logic Layer
│   │   └── tenant.py           # Logic to securely hash API keys and manage quotas
│   │
│   ├── middleware/             # 🛡️ Request Interceptors
│   │   ├── rate_limit.py       # Intercepts requests, checks Redis, enforces quotas
│   │   └── tenant.py           # Parses 'X-Tenant-ID' headers and verifies identity
│   │
│   └── dependencies/           # 💉 Dependency Injection
│       └── auth.py             # Generates specific database sessions for the verified tenant
│
├── alembic/                    # 🔄 Database Migration Scripts (Schema versions)
├── tests/                      # 🧪 Pytest Integration & Unit Tests
├── .env                        # Local Environment Variables
├── docker-compose.yml          # Container configuration for isolated development
└── pyproject.toml              # Python Dependencies lockfile
```

---

## 🚀 3. How to Run the Project (Native Ubuntu)

If you are running the project natively on an Ubuntu system (without Docker containers for the backend), follow these steps:

**Step 1: Ensure your services are running**
Because you installed PostgreSQL and Redis as native software, you can verify they are alive:
```bash
sudo systemctl status postgresql
sudo systemctl status redis-server
```

**Step 2: Start the FastAPI Server**
Open your terminal inside the `bookstore-api` folder, activate the environment, and start `uvicorn`:
```bash
cd ~/Documents/practices_Folder/bookstore-api
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```
Your API Swagger documentation is now available at: **http://localhost:8000/docs**

---

## 🐳 4. How to Run the Project (Using Docker)

If you have a new team member joining who is on Mac or Windows, and they don't want to install PostgreSQL natively, they can spin up the entire isolated stack using the `docker-compose.yml` file.

**Step 1: Start the Docker Stack**
```bash
sudo docker compose up -d
```
*(This commands pulls PostgreSQL, Redis, and launches the entire network seamlessly without touching their host operating system).*

**Step 2: Run Initial Database Migrations**
To create the necessary tables in the new Docker database:
```bash
sudo docker compose exec api alembic upgrade head
```
*(Your API documentation will immediately be available at http://localhost:8000/docs).*

**Step 3: Shutting it Down**
To turn off the project and remove the containers:
```bash
sudo docker compose down
```

---

## 🔐 5. How to use the API

### Provisioning a New Tenant (Super Admin Only)
You must use your `SUPER_ADMIN_KEY` to provision a new company.
- **Endpoint:** `POST /admin/tenants`
- **Headers:** `X-Admin-Key: super-secret-admin-key-change-me`
- **Body:** `{ "name": "Apple", "slug": "apple-inc", "plan": "free" }`

### Acting as a Tenant (Regular endpoints)
Once a tenant is created, use their ID on the regular endpoints.
- **Endpoint:** `POST /authors`
- **Headers:** `X-Tenant-ID: <id-from-provisioning>`
- **Body:** `{ "first_name": "Steve", "last_name": "Jobs", "email": "steve@apple.com" }`

### Viewing Data in DBeaver (Desktop DB UI)
To view raw table data, open the **DBeaver** desktop application and connect using:
- **Host:** `localhost`
- **Port:** `5432`
- **Database:** `bookstore`
- **User/Pass:** `bookstore`
