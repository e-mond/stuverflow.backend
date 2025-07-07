#!/usr/bin/env bash
set -e

echo "Installing dependencies..."
pip install -r requirements.txt
pip install gunicorn==23.0.0  # Explicitly ensure Gunicorn is installed

echo "Collecting static files..."
python manage.py collectstatic --no-input

echo "Running migrations..."
python manage.py migrate --noinput

echo "Copying database if it exists..."
if [ -f db.sqlite3 ]; then
  mkdir -p /data
  cp db.sqlite3 /data/db.sqlite3
fi

echo "Verifying Gunicorn..."
which gunicorn || echo "Warning: Gunicorn not found in PATH"

echo "Build completed successfully!"