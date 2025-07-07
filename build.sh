#!/usr/bin/env bash
set -e  # Exit immediately if a command exits with a non-zero status

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Collecting static files..."
python manage.py collectstatic --no-input

echo "Running migrations..."
python manage.py migrate --no-input

echo "Copying database if it exists..."
if [ -f db.sqlite3 ]; then
  mkdir -p data
  cp db.sqlite3 data/db.sqlite3
fi

echo "Build completed successfully!"
