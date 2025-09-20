FROM python:3.11-slim
WORKDIR /home/ubuntu/fr_bot/code
# Copy the entire repository (build context: repo root)
COPY . /home/ubuntu/fr_bot/code

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Ensure logs/data exist and legacy symlinks
RUN mkdir -p /home/ubuntu/fr_bot/data /home/ubuntu/fr_bot/logs /app \
    && ln -sfn /home/ubuntu/fr_bot/code /app/code \
    && ln -sfn /home/ubuntu/fr_bot/logs /app/logs

# Install dependencies from repo root
RUN pip install --no-cache-dir -r /home/ubuntu/fr_bot/code/requirements.txt

# Run AssetControl main
CMD ["python", "MainProcess/AssetControl/Main.py"]
