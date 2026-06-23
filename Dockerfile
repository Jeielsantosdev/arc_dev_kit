FROM python:3.11-slim

WORKDIR /app

# Install system deps needed by web3.py (secp256k1)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY arc_devkit/ ./arc_devkit/

RUN pip install --no-cache-dir -e "." \
    && pip install --no-cache-dir uvicorn[standard]

# Non-root user for security
RUN useradd -m appuser
USER appuser

EXPOSE 8000

CMD ["uvicorn", "arc_devkit.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
