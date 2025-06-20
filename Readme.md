```markdown
# Process-Mining Prototype

A lightweight end-to-end demo of process-mining and ML-driven case-duration prediction, built with:

- **Django** + **PostgreSQL** (backend & REST API)  
- **PM4Py** for process discovery & analysis  
- **Streamlit** (frontend) driving off the REST API  
- **scikit-learn** & **XGBoost** for ML  
- **Optuna** for hyperparameter tuning  

---

## 📁 Repository Structure

```

process-mining-prototype/
├── .gitignore
├── data/
│   └── event\_logs/
│       └── synthetic\_events.csv  ← generated log
├── scripts/
│   ├── generate\_synthetic\_logs.py
│   ├── train\_model.py
│   └── train\_improved\_model.py
├── backend/
│   ├── manage.py
│   ├── requirements.txt
│   ├── core/                     ← Django project
│   │   ├── settings.py
│   │   └── urls.py
│   ├── events/                   ← events app
│   │   ├── models.py
│   │   └── management/commands/load\_events.py
│   ├── api/                      ← REST API app
│   │   ├── serializers.py
│   │   ├── views.py
│   │   └── urls.py
│   └── models/                   ← serialized ML artifacts
│       ├── case\_duration\_rf.joblib
│       └── case\_duration\_xgb.joblib
└── streamlit\_app/
├── app.py
├── requirements.txt
└── Dockerfile (optional)

````

---

## 🛠 Prerequisites

- **Python 3.10+**  
- **PostgreSQL 15+**  
- **pip** (or use `venv`/`poetry`)  
- **Graphviz** (for PM4Py visualizations)  
- **Node.js** only if you later add a JS frontend  

---

## ⚙️ Backend Setup

1. **Create & activate** a virtual environment:
   ```bash
   cd backend
   python3 -m venv .env
   source .env/bin/activate
````

2. **Install dependencies**:

   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

3. **Configure database** (in `backend/core/settings.py`):

   ```python
   DATABASES = {
     'default': {
       'ENGINE':   'django.db.backends.postgresql',
       'NAME':     'pm_db',
       'USER':     'pm_user',
       'PASSWORD': 'pm_pass',
       'HOST':     'localhost',
       'PORT':     '5432',
     }
   }
   ```

4. **Apply migrations**:

   ```bash
   python manage.py migrate
   ```

5. **Load or generate event logs**:

   * **Generate** synthetic data:

     ```bash
     chmod +x ../scripts/generate_synthetic_logs.py
     ../scripts/generate_synthetic_logs.py
     ```
   * **Load** into Postgres:

     ```bash
     python manage.py load_events ../data/event_logs/synthetic_events.csv
     ```

6. **Train ML models**:

   * **RandomForest**:

     ```bash
     chmod +x ../scripts/train_model.py
     ../scripts/train_model.py
     ```
   * **XGBoost + Optuna**:

     ```bash
     pip install optuna xgboost
     chmod +x ../scripts/train_improved_model.py
     ../scripts/train_improved_model.py
     ```

7. **Run the server**:

   ```bash
   python manage.py runserver 8000
   ```

---

## 🚀 REST API

| Endpoint                               | Description                                      |
| -------------------------------------- | ------------------------------------------------ |
| `GET /api/metrics/`                    | Returns cycle-time metrics & bottleneck list     |
| `GET /api/process-map/`                | Returns an α-miner Petri net as PNG              |
| `GET /api/predict-duration/<case_id>/` | Predicts case duration (hours) via trained model |

Test with:

```bash
curl http://localhost:8000/api/metrics/
curl http://localhost:8000/api/process-map/ --output net.png
curl http://localhost:8000/api/predict-duration/CASE_0001/
```

---

## 📊 Streamlit Dashboard

1. **Switch to the Streamlit env** (you can reuse the backend venv or create a new one):

   ```bash
   cd streamlit_app
   python3 -m venv .env
   source .env/bin/activate
   pip install -r requirements.txt requests
   ```

2. **Configure** the API base URL in `.env` (at project root or in `streamlit_app/`):

   ```dotenv
   API_URL=http://localhost:8000
   ```

3. **Run** the dashboard:

   ```bash
   streamlit run app.py --server.address=0.0.0.0 --server.port=8501
   ```

4. **Features**:

   * **Top-line metrics** & **bottleneck chart** via `/api/metrics/`
   * **Process-map viewer** via `/api/process-map/`
   * **Case-duration predictor** via `/api/predict-duration/…/`

---

## ✅ What’s Done

* Data ingestion & storage (Django models + management command)
* Synthetic-log generator & loader (\~25 k events)
* PM4Py utility & shell verification (500 traces)
* REST API for metrics, process-map, predictions
* Streamlit dashboard driving off the API
* Enhanced analytics: multi-miner selection, bottlenecks, throughput charts
* ML pipelines: RandomForest & XGBoost with Optuna tuning

---

## 🔜 Next Steps

* **Dockerization** of backend + frontend + Postgres
* **Authentication** (DRF or JWT) for the API & dashboard
* **Conformance checking** & additional performance metrics
* **Automated retraining** endpoint & CI/CD pipeline
* **Unit/integration tests** and GitHub Actions setup

---

Feel free to open issues or PRs—happy process-mining!
