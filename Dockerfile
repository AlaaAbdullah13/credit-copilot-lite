FROM python:3.13-slim

WORKDIR /app

# Install system dependencies

RUN apt-get update && apt-get install -y --no-install-recommends \
build-essential \
poppler-utils \
&& rm -rf /var/lib/apt/lists/*

# Copy dependency files first for layer caching

COPY requirements.txt requirements-dev.txt* ./

# Install dependencies

RUN pip install --no-cache-dir -r requirements.txt

# Copy project source

COPY src/ ./src/
COPY prompts/ ./prompts/
COPY data/ ./data/
COPY alembic/ ./alembic/
COPY alembic.ini ./alembic.ini
COPY .env.example ./.env.example

# Create directories for runtime data

RUN mkdir -p data/chroma_db

# Expose port

EXPOSE 8000

# Start the FastAPI app

CMD ["uvicorn", "src.application.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
