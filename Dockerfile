# ================================
# 1) Base Image (Python 3.12)
# ================================
FROM python:3.12-slim

# ================================
# 2) Install system dependencies
# ================================
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# ================================
# 3) Set working directory
# ================================
WORKDIR /app

# ================================
# 4) Install Python dependencies
# ================================
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ================================
# 5) Copy all source files
# ================================
COPY . .

# ================================
# 6) Set environment
# ================================
ENV PYTHONUNBUFFERED=1
ENV PORT=10000

# ================================
# 7) Run server (gunicorn)
# ================================
CMD ["gunicorn", "--bind", "0.0.0.0:10000", "run:app"]
