# Suggested filename: retrieval.py

import math
import re
from collections import Counter
from dataclasses import dataclass, asdict
from pathlib import Path

# pip install instructions:
# No third-party packages required.

TOKEN_RE = re.compile(r"[a-z0-9_+-]+")


def _tokens(text: str) -> list[str]:
    low = text.lower()
    expanded = low
    expansions = {
        "f-16": " aircraft fighter jet fuselage wings tail ",
        "f16": " aircraft fighter jet fuselage wings tail ",
        "bishop": " chess revolve rotational profile slot ",
        "tea cup": " cup vessel shell handle rotate_extrude ",
        "teacup": " cup vessel shell handle rotate_extrude ",
        "name tag": " plate tag text hole extrusion ",
        "key ring": " tag plate hole extrusion ",
    }
    for phrase, extra in expansions.items():
        if phrase in low:
            expanded += extra
    return TOKEN_RE.findall(expanded)


@dataclass
class RetrievedDocument:
    path: str
    score: float
    excerpt: str


class CorpusRetriever:
    """Small deterministic BM25-style retriever for offline CAD knowledge."""

    def __init__(self, roots: list[str | Path]):
        self.docs = []
        for root in roots:
            root = Path(root)
            if not root.exists():
                continue
            for path in sorted(root.rglob("*.md")):
                text = path.read_text(encoding="utf-8", errors="replace")
                toks = _tokens(path.stem.replace("_", " ") + " " + text)
                self.docs.append({"path": path, "text": text, "tokens": toks, "tf": Counter(toks)})
        self.avg_len = sum(len(d["tokens"]) for d in self.docs) / max(1, len(self.docs))
        self.df = Counter()
        for d in self.docs:
            self.df.update(set(d["tokens"]))

    def search(self, query: str, limit: int = 3) -> list[RetrievedDocument]:
        if not self.docs:
            return []
        q = Counter(_tokens(query))
        n = len(self.docs)
        scored = []
        for d in self.docs:
            score = 0.0
            dl = len(d["tokens"])
            for term, qf in q.items():
                tf = d["tf"].get(term, 0)
                if not tf:
                    continue
                df = self.df.get(term, 0)
                idf = math.log(1.0 + (n - df + 0.5) / (df + 0.5))
                denom = tf + 1.5 * (1 - 0.75 + 0.75 * dl / max(self.avg_len, 1))
                score += idf * (tf * 2.5 / denom) * (1 + math.log1p(qf))
            if score > 0:
                excerpt = " ".join(d["text"].strip().split())[:1400]
                scored.append(RetrievedDocument(str(d["path"]), round(score, 5), excerpt))
        scored.sort(key=lambda x: (-x.score, x.path))
        if scored:
            cutoff = scored[0].score * 0.50
            scored = [x for x in scored if x.score >= cutoff]
        return scored[:limit]

    @staticmethod
    def serializable(items: list[RetrievedDocument]) -> list[dict]:
        return [asdict(x) for x in items]
