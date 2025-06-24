Below is an updated **README.md** for the **process-mining-prototype** repo, with step-by-step instructions for both Docker-based and local (no-Docker) setups, environment variables, migrations, model training, and how to launch the Streamlit UI.

````markdown
# ⚙️ Process-Mining Prototype

A demo end-to-end process-mining application, with:

- **Django REST API** for metrics, process-map, conformance, throughput, predictions, and model retraining  
- **PostgreSQL** (or SQLite) persistence  
- **Streamlit** frontend for interactive dashboards and “upload & predict risk”  

---

## 🚀 Quickstart with Docker Compose

1. **Clone the repo**  
   ```bash
   git clone https://github.com/your-org/process-mining-prototype.git
   cd process-mining-prototype
````

2. **Create your `.env` file**
   Copy `​.env.example` to `.env` and edit as needed:

   ```ini
   # .env

   # — PostgreSQL (only if using Postgres; see SQLite alternative below) —
   POSTGRES_DB=pm_db
   POSTGRES_USER=pm_user
   POSTGRES_PASSWORD=pm_pass

   # DATABASE_URL may point at Postgres or SQLite
   # Use Postgres:      postgresql://pm_user:pm_pass@db:5432/pm_db
   # Or SQLite fallback:
   DATABASE_URL=sqlite:///app/db.sqlite3

   # Backend (Django) settings
   SECRET_KEY=replace-me-with-a-secure-one
   DEBUG=True

   # API URL for Streamlit frontend
   API_URL=http://backend:8000
   ```

3. **Build & run all services**

   ```bash
   docker compose up --build -d
   ```

4. **Check that containers are running**

   ```bash
   docker compose ps
   ```

5. **(First run) Create a Django superuser**

   ```bash
   docker compose exec backend python manage.py createsuperuser
   ```

6. **(If using Postgres) Load initial event data**

   ```bash
   # from project root
   docker compose exec backend python manage.py loaddata synthetic_events
   ```

   Or use your own management command:

   ```bash
   docker compose exec backend python manage.py load_events
   ```

7. **Train or retrain ML models**

   * **Reopen-risk**

     ```bash
     docker compose exec backend python scripts/train_reopen_classifier.py ./backend/data/event_logs/synthetic_events.csv
     ```
   * **Case-duration**

     ```bash
     docker compose exec backend python scripts/train_improved_model.py
     ```

   Or via the REST API (admin only):

   ```bash
   curl -X POST -H "Authorization: Bearer <your_admin_token>" \
     http://localhost:8000/api/retrain/
   ```

8. **Visit the apps**

   * **Django API** → [http://localhost:8000/api/metrics/](http://localhost:8000/api/metrics/)  (you’ll need to log in for protected endpoints)
   * **Streamlit UI** → [http://localhost:8501](http://localhost:8501)

---

## 🛠️ Local (no-Docker) Development

> **Prerequisites:** Python 3.10+, `pip`, PostgreSQL (or skip for SQLite),

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

5. **Configure your `.env`** (see above).

6. **Run Django migrations**

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

9. **Start the Django server**

   ```bash
   python manage.py runserver
   ```

10. **Run Streamlit** (in repo root)

    ```bash
    cd ../streamlit_app
    streamlit run app.py
    ```

---

## 📂 Project Layout

```
├── backend
│   ├── api/               ← Django REST views & serializers
│   ├── core/              ← Django project settings, URLs, wsgi, utils
│   ├── data/              ← example CSV event-logs
│   ├── events/            ← `Event` & `Case` models, management cmds
│   ├── models/            ← persisted ML artifacts (.joblib)
│   ├── scripts/           ← training pipelines for ML models
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
└── README.md  ← you are here
```

---

## ⚙️ Tips & Troubleshooting

* **Switching DB**: set `DATABASE_URL` to `sqlite:///app/db.sqlite3` for SQLite, or to a full `postgresql://…` URI for Postgres.
* **Inspecting volumes**:

  ```bash
  docker run --rm -v process-mining-prototype_db_data:/data busybox ls -R /data
  ```
* **Free up space**:

  ```bash
  docker system prune -af
  docker volume prune -f
  ```
* **Logs**:

  ```bash
  docker compose logs -f backend
  docker compose logs -f streamlit
  ```
* **Rebuild only one service**:

  ```bash
  docker compose build backend
  docker compose up -d backend
  ```

---

Happy process-mining! 🎉
