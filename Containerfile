FROM python:3.12-slim

# Create a non-root user (rootless Podman maps this to your host UID)
RUN useradd --create-home --uid 1000 strata

WORKDIR /app

# Install uv for dependency management (matches local dev tooling)
RUN pip install --no-cache-dir uv

# Copy dependency manifests first for better layer caching
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Copy application code
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini ./

# Entrypoint: apply migrations, then start the app
COPY entrypoint.sh ./
RUN chmod +x entrypoint.sh

RUN mkdir -p /data && chown strata:strata /data
RUN chown -R strata:strata /app
USER strata

ENV DATABASE_URL=sqlite:////data/strata.db
EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]