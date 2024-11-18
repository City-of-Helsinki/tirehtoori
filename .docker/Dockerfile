# Used by Azure Devops to pull from internal registry
ARG BUILDER_REGISTRY=registry.access.redhat.com
# ==============================
FROM ${BUILDER_REGISTRY}/ubi9/python-311:latest AS appbase
# ==============================

USER root
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

COPY --chown=default:root requirements*.txt .

RUN dnf update -y && dnf install -y \
    nmap-ncat \
    gettext \
    && pip install -U pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir -r requirements-prod.txt \
    && dnf clean all

ENTRYPOINT ["/app/.docker/docker-entrypoint.sh"]
EXPOSE 8000/tcp

# ==============================
FROM appbase AS development
# ==============================

COPY --chown=default:root requirements-dev.txt .
RUN pip install --no-cache-dir -r requirements-dev.txt

ENV DEV_SERVER=True

COPY --chown=default:root . .

USER root
#USER default

# ==============================
FROM appbase AS staticbuilder
# ==============================

ENV STATIC_ROOT=/app/static
COPY --chown=default:root . .
RUN SECRET_KEY="only-used-for-collectstatic" ENABLE_ADMIN_APP="True"  \
    python manage.py collectstatic --noinput

# ==============================
FROM appbase AS production
# ==============================

COPY --from=staticbuilder --chown=default:root /app/static /app/static
COPY --chown=default:root . .

USER default
