"""Состояние текущего сеанса: кластер, цель (PROD/TEST), бэкенд. Credentials
в память сессии не попадают - они нужны только backend.connect() и не хранятся."""
from dataclasses import dataclass, field

from app_config import ClusterConfig


@dataclass
class Session:
    cluster: ClusterConfig
    target: str
    username: str
    backend: object
    host: str = field(default="")
    theme: str = field(default="light")

    def __post_init__(self):
        if not self.host:
            self.host = self.cluster.hosts.get(self.target) or next(iter(self.cluster.hosts.values()))
