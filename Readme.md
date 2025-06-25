````markdown
# ⚙️ Process-Mining Prototype

A demo end-to-end process-mining application, featuring:

- **Django REST API** for:
  - Metrics & bottlenecks  
  - Throughput  
  - Conformance  
  - Process-map visualization  
  - Duration prediction  
  - Model retraining  
- **PostgreSQL** (or SQLite) persistence  
- **Streamlit** frontend for interactive dashboards & “Upload & Predict Risk”  

---

## 🚀 Quickstart with Docker Compose

1. **Clone the repo**  
   ```bash
   git clone https://github.com/your-org/process-mining-prototype.git
   cd process-mining-prototype
````

2. **Create your `.env`**
   Copy the example and edit as needed:

   ```ini
   # .env

   # — PostgreSQL (only if using Postgres) —
   POSTGRES_DB=pm_db
   POSTGRES_USER=pm_user
   POSTGRES_PASSWORD=pm_pass

   # DATABASE_URL may point at Postgres or SQLite:
   #   Postgres:   postgresql://pm_user:pm_pass@db:5432/pm_db
   #   SQLite:     sqlite:///app/db.sqlite3
   DATABASE_URL=sqlite:///app/db.sqlite3

   # Django settings
   SECRET_KEY=replace-me-with-a-secure-one
   DEBUG=True

   # Frontend → API
   API_URL=http://backend:8000
   ```

3. **Build & start all services**

   ```bash
   docker compose up --build -d
   ```

4. **Verify containers**

   ```bash
   docker compose ps
   ```

5. **Create a Django superuser**

   ```bash
   docker compose exec backend python manage.py createsuperuser
   ```

6. **Load initial data**

   ```bash
   # Using built-in management command:
   docker compose exec backend python manage.py load_events

   # Or from fixture:
   docker compose exec backend python manage.py loaddata synthetic_events
   ```

7. **Train / retrain ML models**

   * **Reopen-risk**

     ```bash
     docker compose exec backend \
       python scripts/train_reopen_classifier.py \
       ./backend/data/event_logs/synthetic_events.csv
     ```
   * **Case-duration**

     ```bash
     docker compose exec backend python scripts/train_improved_model.py
     ```
   * **Or via API** *(admin only)*

     ```bash
     curl -X POST \
       -H "Authorization: Bearer <ADMIN_TOKEN>" \
       http://localhost:8000/api/retrain/
     ```

8. **Browse the apps**

   * **Django API** → `http://localhost:8000/api/metrics/`
     *(login for protected endpoints)*
   * **Streamlit UI** → `http://localhost:8501`

---

## 🛠️ Local (no-Docker) Development

> **Prerequisites:** Python 3.10+, `pip`, PostgreSQL (optional; SQLite fallback)

1. **Clone & enter**

   ```bash
   git clone https://github.com/your-org/process-mining-prototype.git
   cd process-mining-prototype
   ```

2. **Create & activate a virtualenv**

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. **Install backend deps**

   ```bash
   pip install --upgrade pip
   pip install -r backend/requirements.txt
   ```

4. **Install Streamlit deps**

   ```bash
   pip install -r streamlit_app/requirements.txt
   ```

5. **Configure your `.env`** *(see above)*

6. **Run migrations & create superuser**

   ```bash
   cd backend
   python manage.py migrate
   python manage.py createsuperuser
   ```

7. **Load or generate event data**

   ```bash
   python manage.py load_events
   ```

8. **Train models**

   ```bash
   python scripts/train_reopen_classifier.py ../backend/data/event_logs/synthetic_events.csv
   python scripts/train_improved_model.py
   ```

9. **Start Django**

   ```bash
   python manage.py runserver
   ```

10. **Start Streamlit**

    ```bash
    cd ../streamlit_app
    streamlit run app.py
    ```

---

## 📂 Project Layout

```
├── backend
│   ├── api/               ← DRF views & serializers
│   ├── core/              ← Django settings, URLs, wsgi, utils
│   ├── data/              ← sample CSV event-logs
│   ├── events/            ← `Event` & `Case` models + management commands
│   ├── models/            ← persisted ML artifacts (.joblib)
│   ├── scripts/           ← training pipelines
│   ├── entrypoint.sh      ← Docker entrypoint (migrations + gunicorn)
│   ├── Dockerfile
│   ├── manage.py
│   └── requirements.txt
├── streamlit_app
│   ├── app.py
│   ├── Dockerfile
│   └── requirements.txt
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## ⚙️ Tips & Troubleshooting

* **Switch DB**: set `DATABASE_URL` to:

  * SQLite: `sqlite:///app/db.sqlite3`
  * Postgres: `postgresql://<user>:<pw>@db:5432/<db>`
* **Inspect volumes**:

  ```bash
  docker run --rm -v process-mining-prototype_db_data:/data busybox ls -R /data
  ```
* **Free up space**:

  ```bash
  docker system prune -af
  docker volume prune -f
  ```
* **View logs**:

  ```bash
  docker compose logs -f backend
  docker compose logs -f streamlit
  ```
* **Rebuild only one service**:

  ```bash
  docker compose build backend
  docker compose up -d backend
  ```

Happy process-mining! 🎉

```
```
