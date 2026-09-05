# The marketplace service.
#
# Two stages, for one specific reason: `chain.py` loads the ListingContract ABI
# from `contracts/out/artifacts.json`, and that file is gitignored because it is
# a build product. A single-stage Python image would deploy cleanly and then
# fail on the first chain read with "contract artifacts not found", which is the
# worst kind of deployment bug: green build, broken service.
#
# So the contracts are compiled here rather than assumed. The Node stage exists
# only to produce that one JSON file; nothing else from it reaches the runtime
# image.

# --- stage 1: compile the contracts ---------------------------------------
FROM node:22-slim AS contracts

WORKDIR /build/contracts
COPY contracts/package.json contracts/package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY contracts/ ./
RUN npm run build && test -s out/artifacts.json


# --- stage 2: the service -------------------------------------------------
FROM python:3.11-slim

# Keeps the image from carrying a pip cache and stops Python buffering logs,
# which otherwise makes a crash loop look silent in Railway's log view.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependencies first, so a change to service code does not reinstall the world.
COPY packages/succession/pyproject.toml packages/succession/README.md ./packages/succession/
COPY packages/succession/src ./packages/succession/src
RUN pip install --no-cache-dir -e "./packages/succession[service,chain]"

COPY service ./service
COPY --from=contracts /build/contracts/out/artifacts.json ./contracts/out/artifacts.json

# The deployment record is baked in rather than fetched: it is the only thing
# that puts the service in on-chain mode, and a service that started in "no
# contract" mode because a file had not synced yet would report an empty
# marketplace as though nothing had ever been listed.
COPY deployments ./deployments

EXPOSE 8000

# Railway assigns $PORT. Single worker on purpose: envelopes and content keys
# live in process memory by design, so a second worker would serve 409s for a
# listing it cannot see. See service/README.md.
CMD ["sh", "-c", "uvicorn service.app:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
