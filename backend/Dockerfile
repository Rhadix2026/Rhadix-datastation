FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN addgroup --system kik && adduser --system --ingroup kik kik
USER kik
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
