#!/usr/bin/env bash
cd /app

python main.py & celery -A src.celery_worker.celery_app worker --loglevel=info --pool=threads