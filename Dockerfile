FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY config/ config/
COPY docs/ docs/
COPY mongo/ mongo/
COPY results/ results/
COPY scripts/ scripts/
COPY v1/ v1/
COPY v2/ v2/
COPY README.md .

CMD ["python", "scripts/validate_counts.py", "--config", "config/db_config.docker.json"]
