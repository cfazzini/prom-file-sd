FROM python:alpine
LABEL maintainer="Dmitry Kamovsky <kd@arenadata.io>"
WORKDIR /app
ADD ./requirements.txt .
RUN pip install -r requirements.txt
ADD ./app.py .
EXPOSE 19216
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:19216", "app:app"]
