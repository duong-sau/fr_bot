FROM python:3.11-slim
WORKDIR /home/ubuntu/fr_bot/code
# Copy entire repo (build context is repo root)
COPY . /home/ubuntu/fr_bot/code

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Ensure dirs exist and legacy symlinks
RUN mkdir -p /home/ubuntu/fr_bot/data /home/ubuntu/fr_bot/logs /app \
    && ln -sfn /home/ubuntu/fr_bot/code /app/code \
    && ln -sfn /home/ubuntu/fr_bot/logs /app/logs

# Install dependencies from repo root
RUN pip install --no-cache-dir -r /home/ubuntu/fr_bot/code/requirements.txt

# Start Discord notifier (default reads discord_simple_log_path; override via LOG_FILE env)
CMD ["python", "-u", "Notification/Discord.py"]
