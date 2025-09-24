FROM python:3.11-slim

WORKDIR /app

ENV PYTHONPATH=/app

RUN pip install poetry==1.7.1

COPY pyproject.toml poetry.lock* /app/

# Ensure local path dependencies are available to Poetry during install
COPY ../third_party/ /app/third_party/

RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi

# Copy rest of the repo
COPY ../ /app/

CMD ["python", "-m", "src.jobs.queue_worker"]
