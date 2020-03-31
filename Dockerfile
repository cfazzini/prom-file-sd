FROM python:alpine
LABEL maintainer="Dmitry Kamovsky <kd@arenadata.io>"
WORKDIR /app
ADD ./requirements.txt .
RUN apk add --no-cache git
    pip install -r requirements.txt && \
    pip install -e git+https://github.com/schapman1974/tinymongo.git#egg=tinymongo
ADD ./app.py .
EXPOSE 19216
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:19216", "app:app"]
