# Security

## Reporting a vulnerability

Please report security issues privately via GitHub's **"Report a vulnerability"**
(Security → Advisories) on this repository rather than opening a public issue.

## Scope & expectations

`geo-eval-forge` is a research/benchmark tool, not a production service.

- **Credentials.** The values in `docker-compose.yml` and `.env.example`
  (`geoeval` / `geoserver`) are **insecure defaults for local development only**.
  Override every password via a `.env` file and never expose the PostGIS (5432)
  or GeoServer (8080) ports to untrusted networks.
- **No secrets in the repo.** Do not commit `.env`, service-account JSON, API
  keys, or tokens. These are excluded by `.gitignore`; the LLM adapters read
  credentials from the environment at runtime (e.g. `GOOGLE_APPLICATION_CREDENTIALS`).
- **Untrusted input.** The live runner executes the SQL/shell *solution* files in
  each task against the local stack. Only run task candidates you trust; treat a
  task directory like code you are about to execute.
- **Network.** Offline grading (`make run`, `make test`) makes no network calls.
  The dashboard's map loads tiles from OpenStreetMap; the optional LLM adapters
  call your configured provider (e.g. Vertex AI).
