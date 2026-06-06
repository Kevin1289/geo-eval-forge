"""Google Vertex AI adapter (the default live gateway).

Heavy SDK imports are deferred to construction so the package imports fine without
``google-cloud-aiplatform`` installed. Requires ``GOOGLE_CLOUD_PROJECT`` and
application-default / service-account credentials in the environment.
"""
from __future__ import annotations

import os


class VertexClient:
    name = "vertex"

    def __init__(self, model: str | None = None, location: str | None = None):
        try:
            import vertexai
            from vertexai.generative_models import GenerativeModel
        except Exception as exc:  # pragma: no cover - import guard
            raise RuntimeError(
                "Vertex adapter requires `pip install geoeval[vertex]` "
                "(google-cloud-aiplatform)."
            ) from exc

        project = os.environ.get("GOOGLE_CLOUD_PROJECT")
        if not project:
            raise RuntimeError("GOOGLE_CLOUD_PROJECT is not set; cannot use the Vertex adapter.")
        location = location or os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
        vertexai.init(project=project, location=location)
        self.model_name = model or os.environ.get("GEOEVAL_VERTEX_MODEL", "gemini-2.5-pro")
        self._model = GenerativeModel(self.model_name)

    def complete(self, prompt: str, *, system: str | None = None, key: str | None = None) -> str:
        text = f"{system}\n\n{prompt}" if system else prompt
        resp = self._model.generate_content(text)
        return resp.text
