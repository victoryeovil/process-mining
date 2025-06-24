FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    POETRY_VIRTUALENVS_CREATE=false

WORKDIR /app

# Install system deps (now including graphviz)
RUN apt-get update && \
    apt-get install -y build-essential libpq-dev graphviz && \
    rm -rf /var/lib/apt/lists/*

# Copy & install Python deps
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy code
COPY backend/ .

ENTRYPOINT ["./entrypoint.sh"]
CMD ["gunicorn", "core.wsgi:application", "--bind", "0.0.0.0:8000"]
