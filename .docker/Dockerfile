# ==============================
FROM registry.access.redhat.com/ubi9/python-312 AS appbase
# ==============================

# Branch or tag used to pull python-uwsgi-common.
ARG UWSGI_COMMON_REF="main"

# Install uv, see https://docs.astral.sh/uv/guides/integration/docker/#installing-uv
COPY --from=ghcr.io/astral-sh/uv:0.12.10@sha256:2bb3ebca0a796a155094a27773d290c4b074572e6107f171d88d086682fd2500 /uv /uvx /usr/local/bin/

USER root
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

ENV UV_PROJECT_ENVIRONMENT=/opt/app-root \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_CACHE=1 \
    UV_PYTHON_DOWNLOADS=never

# Make the virtualenv binaries available on PATH
ENV PATH="/opt/app-root/bin:$PATH"

COPY pyproject.toml uv.lock ./

RUN dnf update -y \
    && dnf install -y \
    nmap-ncat \
    gettext \
    && uv sync --locked --no-dev --group prod --no-install-project \
    && dnf clean all

# Build and copy specific python-uwsgi-common files.
ADD https://github.com/City-of-Helsinki/python-uwsgi-common/archive/"${UWSGI_COMMON_REF}".tar.gz /usr/src/
RUN mkdir -p /usr/src/python-uwsgi-common \
    && tar --strip-components=1 -xzf /usr/src/"${UWSGI_COMMON_REF}".tar.gz -C /usr/src/python-uwsgi-common \
    && mkdir /etc/uwsgi \
    && cp /usr/src/python-uwsgi-common/uwsgi-base.ini /etc/uwsgi/ \
    && uwsgi --build-plugin /usr/src/python-uwsgi-common \
    && rm -rf /usr/src/"${UWSGI_COMMON_REF}".tar.gz \
    && rm -rf /usr/src/python-uwsgi-common \
    && uwsgi --build-plugin https://github.com/City-of-Helsinki/uwsgi-sentry \
    && mkdir -p /usr/local/lib/uwsgi/plugins \
    && mv sentry_plugin.so /usr/local/lib/uwsgi/plugins

ENTRYPOINT ["/app/.docker/docker-entrypoint.sh"]

# ==============================
FROM appbase AS development
# ==============================

RUN uv sync --locked --group dev --group conf-parser --group prod --no-install-project

ENV DEV_SERVER=True

RUN groupadd -g 1000 appuser \
    && useradd -u 1000 -g appuser -ms /bin/bash appuser \
    && chown -R appuser:root /app

COPY --chown=appuser:root . .

USER appuser
EXPOSE 8000/tcp

# ==============================
FROM appbase AS staticbuilder
# ==============================

ENV STATIC_ROOT="/app/static"
COPY . .

RUN mkdir -p tirehtoori/static \
    && SECRET_KEY="only-used-for-collectstatic" ENABLE_ADMIN_APP="True" \
    python manage.py collectstatic --noinput

# ==============================
FROM appbase AS production
# ==============================

COPY --from=staticbuilder /app/static /app/static
COPY . .

USER default
EXPOSE 8000/tcp
