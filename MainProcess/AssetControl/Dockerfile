FROM python:3.11-slim
WORKDIR /app/code
COPY ../../.. /app/code
COPY ../../../_settings /app/code/_settings
RUN mkdir -p /app/data /app/logs
RUN mkdir -p /home/ubuntu/fr_bot/code
RUN mkdir -p /home/ubuntu/fr_bot/logs/asset
RUN ln -s /app/code/_settings /home/ubuntu/fr_bot/code/_settings
RUN pip install --no-cache-dir -r /app/code/requirements.txt
CMD ["python", "MainProcess/AssetControl/Main.py"]
