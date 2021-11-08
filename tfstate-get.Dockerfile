FROM python:3.10-slim-bullseye  as builder
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc
COPY requirements.txt *.py /app/
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt

# final stage
FROM python:3.10-slim-bullseye
WORKDIR /app

ENV GOOGLE_APPLICATION_CREDENTIALS="/app/firebase.json"

RUN addgroup --gid 1001 --system app && \
    adduser --shell /bin/false --disabled-password --uid 1001 --system --group app
# USER app
COPY --from=builder /app/wheels /wheels
COPY --from=builder /app/ /app/
RUN pip install --no-cache /wheels/*
CMD ["gunicorn", "main:app", "-b", "0.0.0.0:8000", "--workers", "1", "--threads","20"]