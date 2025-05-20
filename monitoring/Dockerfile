FROM alpine:latest
WORKDIR /app
COPY . .
COPY ../shared ../shared
RUN pip install --no-cache-dir -r requirements.txt
CMD ["python", "monitor.py"]