"""
FAISS-backed vector backend adapter.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np

from .index_manager import FAISSIndexManager


class FAISSVectorBackend:
    def __init__(self, index_dir: Path, model_version: str):
        self.manager = FAISSIndexManager(index_dir=index_dir, model_version=model_version)

    def exists(self) -> bool:
        return self.manager.exists()

    def load(self) -> bool:
        return self.manager.load()

    def search_jobs(self, query_vector: np.ndarray, k: int = 10) -> list[tuple[str, float]]:
        return self.manager.search_jobs(query_vector, k=k)

    def search_jobs_filtered(
        self,
        query_vector: np.ndarray,
        candidate_uuids: list[str],
        k: int = 10,
    ) -> list[tuple[str, float]]:
        return self.manager.search_jobs_filtered(query_vector, candidate_uuids, k=k)

    def total_jobs(self) -> int:
        index = self.manager.indexes.get("jobs")
        return int(index.ntotal) if index is not None else 0

    def has_skill_index(self) -> bool:
        return "skills" in self.manager.indexes and self.manager.indexes["skills"] is not None

    def get_skill_embedding(self, skill: str) -> Optional[np.ndarray]:
        if not self.has_skill_index():
            return None
        skill_idx = self.manager.skill_to_idx.get(skill)
        if skill_idx is None:
            return None
        return self.manager.indexes["skills"].reconstruct(skill_idx)

    def search_skills(self, query_vector: np.ndarray, k: int = 10) -> list[tuple[str, float]]:
        return self.manager.search_skills(query_vector, k=k)

    def has_company_index(self) -> bool:
        return self.manager.has_company_index()

    def get_company_centroids(self, company_name: str) -> Optional[np.ndarray]:
        return self.manager.get_company_centroids(company_name)

    def search_companies(self, query_vector: np.ndarray, k: int = 10) -> list[tuple[str, float]]:
        return self.manager.search_companies(query_vector, k=k)

    def get_stats(self) -> dict:
        return self.manager.get_stats()
