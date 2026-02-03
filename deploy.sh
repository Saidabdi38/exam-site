#!/bin/bash
set -e

echo "🚀 Starting deployment..."

cd /home/xirfadyaal/exam-site

echo "📦 Activating virtualenv..."
source venv/bin/activate

echo "⬇️ Pulling latest code from GitHub..."
git pull origin main

echo "🧱 Making migrations..."
python3 manage.py makemigrations

echo "🗄 Applying migrations..."
python3 manage.py migrate

echo "🎨 Collecting static files..."
python3 manage.py collectstatic --noinput

echo "♻️ Restarting services..."
sudo systemctl restart gunicorn_xirfadyaal
# Optional: restart Nginx only if needed
# sudo systemctl restart nginx

echo "✅ Deployment finished successfully!"

