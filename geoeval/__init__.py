"""geo-eval-forge harness.

A reproducible GeoAI benchmark + eval harness. The package is organized as:

- ``models``      dataclasses (Task, Candidate, Verdict, Result)
- ``loader``      load + schema-validate tasks and candidates
- ``verifiers``   deterministic graders (numeric, vector_equiv, sql_result, ...)
- ``runner``      grade a candidate (offline recorded output, or live execution)
- ``score``       aggregate graded results into results.json (+ map GeoJSON)
- ``adapters``    pluggable LLM gateways (replay = offline, vertex = live)
- ``judge``       optional LLM-as-judge with measured human agreement
- ``cli``         the ``geoeval`` command
"""

__version__ = "0.1.0"
