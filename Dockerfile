FROM python:3.11-slim

WORKDIR /app
COPY . .

ENV PYTHONUNBUFFERED=1
ENV PORT=8080
ENV HOST=0.0.0.0

EXPOSE 8080

CMD ["python3", "-m", "riskmemory.server", "--host", "0.0.0.0", "--no-browser"]
