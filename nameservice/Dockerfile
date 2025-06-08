FROM python:3-alpine


WORKDIR /app
COPY nameservice/ .
COPY shared/ shared/
ENV PYTHONPATH=/app
RUN pip install --no-cache-dir -r requirements.txt
CMD ["python", "nameservice.py"]