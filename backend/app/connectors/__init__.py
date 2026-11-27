from app.connectors.arbeitnow import ArbeitnowConnector
from app.connectors.base import BaseConnector, SourceUnavailable
from app.connectors.trudvsem import TrudvsemConnector

REGISTRY: dict[str, type[BaseConnector]] = {
    ArbeitnowConnector.name: ArbeitnowConnector,
    TrudvsemConnector.name: TrudvsemConnector,
}

__all__ = ["REGISTRY", "BaseConnector", "SourceUnavailable", "ArbeitnowConnector", "TrudvsemConnector"]
