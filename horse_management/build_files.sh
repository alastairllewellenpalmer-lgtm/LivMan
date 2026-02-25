#!/bin/bash
pip install -r requirements.txt
npm install
npx tailwindcss -i static/css/input.css -o static/css/styles.css --minify
python manage.py collectstatic --noinput
