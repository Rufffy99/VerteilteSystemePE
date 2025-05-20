FROM python:3-alpine
WORKDIR /app
COPY . .
COPY ../shared ../shared
RUN pip install --no-cache-dir -r requirements.txt
CMD ["python", "dispatcher.py"]