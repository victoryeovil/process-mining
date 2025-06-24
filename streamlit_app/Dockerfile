# streamlit_app/Dockerfile
FROM python:3.11-slim

# Set a working dir
WORKDIR /app

# Copy & install Python deps
COPY streamlit_app/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# Copy your Streamlit app
COPY streamlit_app/ .

# Expose Streamlit port
EXPOSE 8501

# Launch via the streamlit CLI
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501"]
