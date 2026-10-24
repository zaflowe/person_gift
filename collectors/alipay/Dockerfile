FROM mcr.microsoft.com/playwright/python:v1.63.0-noble
USER root
RUN apt-get update && apt-get install -y --no-install-recommends libzbar0 fonts-noto-cjk xauth \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir playwright==1.63.0 Pillow==12.0.0 pyzbar==0.1.9
WORKDIR /app
COPY agent.py ledger.py schedule.py /app/
USER pwuser
ENV PYTHONUNBUFFERED=1 COLLECTOR_DATA=/data
CMD ["python", "/app/agent.py"]
