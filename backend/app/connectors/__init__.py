from app.connectors.arbeitnow import ArbeitnowConnector
from app.connectors.base import BaseConnector, SourceUnavailable

REGISTRY: dict[str, type[BaseConnector]] = {ArbeitnowConnector.name: ArbeitnowConnector}

__all__ = ["REGISTRY", "BaseConnector", "SourceUnavailable", "ArbeitnowConnector"]
