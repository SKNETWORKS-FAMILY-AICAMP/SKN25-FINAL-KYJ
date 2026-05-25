from __future__ import annotations

from foldmind_ai_core.bootstrap.container.application import ApplicationContainer

app = ApplicationContainer().fastapi_app()
