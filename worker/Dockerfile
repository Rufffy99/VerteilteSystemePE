FROM python:3-alpine
WORKDIR /app
COPY worker/ .
COPY shared/ shared/
ENV PYTHONPATH=/app
RUN pip install --no-cache-dir -r requirements.txt
ENTRYPOINT ["python", "worker.py"]