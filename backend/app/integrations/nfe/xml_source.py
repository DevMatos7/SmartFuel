"""Abstração de origem de XML de NF-e — não presume o mecanismo do ambiente."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class NfeXmlCandidate:
    access_key: str | None
    content: bytes
    source_label: str


class NfeXmlSource(ABC):
    @abstractmethod
    def list_candidates(self, *, limit: int = 100) -> list[NfeXmlCandidate]:
        raise NotImplementedError

    @abstractmethod
    def load_by_access_key(self, access_key: str) -> NfeXmlCandidate | None:
        raise NotImplementedError


class DirectoryNfeXmlSource(NfeXmlSource):
    """Diretório montado no servidor (quando identificado no ambiente)."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def list_candidates(self, *, limit: int = 100) -> list[NfeXmlCandidate]:
        if not self.root.exists():
            return []
        out: list[NfeXmlCandidate] = []
        for path in sorted(self.root.glob("**/*.xml"))[:limit]:
            content = path.read_bytes()
            stem = path.stem
            access_key = stem if stem.isdigit() and len(stem) == 44 else None
            out.append(NfeXmlCandidate(access_key=access_key, content=content, source_label=str(path)))
        return out

    def load_by_access_key(self, access_key: str) -> NfeXmlCandidate | None:
        path = self.root / f"{access_key}.xml"
        if not path.exists():
            matches = list(self.root.glob(f"**/{access_key}.xml"))
            if not matches:
                return None
            path = matches[0]
        return NfeXmlCandidate(access_key=access_key, content=path.read_bytes(), source_label=str(path))


class UploadNfeXmlSource(NfeXmlSource):
    """Upload administrativo controlado (conteúdo já em memória)."""

    def __init__(self, items: list[NfeXmlCandidate] | None = None) -> None:
        self._items = list(items or [])

    def add(self, candidate: NfeXmlCandidate) -> None:
        self._items.append(candidate)

    def list_candidates(self, *, limit: int = 100) -> list[NfeXmlCandidate]:
        return self._items[:limit]

    def load_by_access_key(self, access_key: str) -> NfeXmlCandidate | None:
        for item in self._items:
            if item.access_key == access_key:
                return item
        return None


class UnconfiguredNfeXmlSource(NfeXmlSource):
    """Fonte ainda não identificada no ambiente — fail closed."""

    def list_candidates(self, *, limit: int = 100) -> list[NfeXmlCandidate]:
        return []

    def load_by_access_key(self, access_key: str) -> NfeXmlCandidate | None:
        return None
