# Worker image: GDAL CLI (ogr2ogr) + Python + the geoeval harness.
# Base image ships GDAL and ogr2ogr; we add psql and the Python deps.
FROM ghcr.io/osgeo/gdal:ubuntu-small-latest

RUN apt-get update \
 && apt-get install -y --no-install-recommends postgresql-client python3-pip \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies first for better layer caching.
COPY pyproject.toml README.md ./
COPY geoeval ./geoeval
RUN pip install --no-cache-dir --break-system-packages -e ".[live,dev]"

# The rest of the repo is bind-mounted at runtime (see docker-compose.yml),
# but copy it so the image is usable standalone (e.g. in CI without a mount).
COPY . .

CMD ["geoeval", "--help"]
