# ==============================
FROM python:3.11 AS appbase
# ==============================

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

RUN useradd -Ums /bin/bash -d /appuser appuser

COPY --chown=appuser:appuser requirements.txt .

RUN  apt-get update && apt-get install -y \
    gettext \
    && pip install -U pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt

ENTRYPOINT ["/app/.docker/docker-entrypoint.sh"]

# ==============================
FROM appbase AS development
# ==============================

COPY --chown=appuser:appuser requirements-dev.txt .
RUN pip install --no-cache-dir -r requirements-dev.txt

ENV DEV_SERVER=True

COPY --chown=appuser:appuser . .

USER appuser
EXPOSE 8000/tcp

# ==============================
FROM appbase AS staticbuilder
# ==============================

ENV VAR_ROOT=/app
COPY . /app
RUN SECRET_KEY="only-used-for-collectstatic"  \
    python manage.py collectstatic --noinput

# ==============================
FROM appbase AS production
# ==============================

COPY --from=staticbuilder /app/static /app/static
COPY . .

USER default
EXPOSE 8000/tcp
