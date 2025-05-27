FROM python:3-alpine
WORKDIR /app
COPY worker/ .
COPY shared/ shared/
ENV PYTHONPATH=/app
RUN pip install --no-cache-dir --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt
ENTRYPOINT ["python", "worker.py"]