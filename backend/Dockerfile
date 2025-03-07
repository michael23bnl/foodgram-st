FROM python:3.9-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD sh -c "python manage.py migrate && python manage.py loaddata /app/recipes/data/ingredients.json /app/recipes/data/users.json /app/recipes/data/recipes.json && python manage.py collectstatic --noinput && gunicorn --bind 0.0.0.0:8000 foodgram.wsgi:application"
