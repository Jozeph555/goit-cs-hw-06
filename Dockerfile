FROM python:3.9

WORKDIR /app

COPY src/ /app/src/
COPY requirements.txt /app/
COPY static/ /app/static/
COPY templates/ /app/templates/

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 3000 5000

CMD ["python", "src/main.py"]