"""Optional Google Cloud adapters.

These modules never produce the multi-signal alert. They ingest lagged
geospatial layers, structure dated evidence, host the investigator UI, and
optionally compare a Vertex baseline. Numeric discovery stays in anomaly /
graph / hypotheses / VoI.
"""

from jaadu.google.status import google_status

__all__ = ["google_status"]
