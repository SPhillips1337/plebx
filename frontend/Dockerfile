FROM python:3.11-slim
WORKDIR /app
COPY . /app
EXPOSE 3000
# Simple static server for the minimal frontend
CMD ["python", "-m", "http.server", "3000"]
