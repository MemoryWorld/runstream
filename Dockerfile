FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
COPY schemas ./schemas

RUN pip install --no-cache-dir .

ENV RUNSTREAM_DB=/data/runstream.db
EXPOSE 8000

CMD ["uvicorn", "runstream.api:app", "--host", "0.0.0.0", "--port", "8000"]
