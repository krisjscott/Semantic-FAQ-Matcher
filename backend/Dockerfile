FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FAQ_DEVICE=cpu

WORKDIR /app

COPY requirements.txt /app/backend/requirements.txt
RUN python -m pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
    && python -m pip install --no-cache-dir -r /app/backend/requirements.txt

COPY . /app/backend/

CMD ["sh", "-c", "exec python -m uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
