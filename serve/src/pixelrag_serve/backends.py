import os
from typing import Any, Protocol, TypedDict, runtime_checkable

_META_FIELDS = ("article_id", "tile_index", "chunk_index", "y_offset", "tile_height")


class SearchHit(TypedDict):
    score: float
    vector_id: int | str
    article_id: int
    tile_index: int
    chunk_index: int
    y_offset: int
    tile_height: int


@runtime_checkable
class VectorBackend(Protocol):
    name: str
    dimension: int
    nlist: int
    nprobe: int

    @property
    def ntotal(self) -> int: ...

    def set_nprobe(self, n: int | None) -> None: ...

    def reset_nprobe(self) -> None: ...

    def raw_search(
        self, query_vectors: Any, k: int, min_tile_height: int | None = None
    ) -> list[list[SearchHit]]: ...

    def reconstruct(self, vids: list[int | str]) -> list[list[float] | None]: ...


class FaissBackend:
    name = "faiss"

    def __init__(self, index_dir: str, summary: dict):
        import faiss
        import numpy as np

        index_path = os.path.join(index_dir, "index.faiss")
        self.index = faiss.read_index(index_path)
        self._meta = np.load(os.path.join(index_dir, "metadata.npz"))
        self.dimension = summary.get("dimension", self.index.d)
        self.nlist = summary.get("nlist", 4096)
        self._default_nprobe = self.index.nprobe
        self._direct_map_built = False

    @property
    def ntotal(self) -> int:
        return self.index.ntotal

    @property
    def nprobe(self) -> int:
        return self.index.nprobe

    def set_nprobe(self, n):
        if n is not None:
            self.index.nprobe = n

    def reset_nprobe(self):
        self.index.nprobe = self._default_nprobe

    def raw_search(self, query_vectors, k, min_tile_height=None):
        # The API filters FAISS metadata after search.
        if k <= 0:
            return [[] for _ in query_vectors]
        distances, indices = self.index.search(query_vectors, k)
        article_ids = self._meta["article_ids"]
        tile_indices = self._meta["tile_indices"]
        chunk_indices = self._meta["chunk_indices"]
        y_offsets = self._meta["y_offsets"]
        tile_heights = self._meta["tile_heights"]
        out = []
        for query_index in range(indices.shape[0]):
            hits = []
            for result_index in range(indices.shape[1]):
                vector_id = int(indices[query_index, result_index])
                if vector_id == -1:
                    continue
                hits.append(
                    {
                        "score": float(distances[query_index, result_index]),
                        "vector_id": vector_id,
                        "article_id": int(article_ids[vector_id]),
                        "tile_index": int(tile_indices[vector_id]),
                        "chunk_index": int(chunk_indices[vector_id]),
                        "y_offset": int(y_offsets[vector_id]),
                        "tile_height": int(tile_heights[vector_id]),
                    }
                )
            out.append(hits)
        return out

    def reconstruct(self, vids):
        if not self._direct_map_built:
            self.index.make_direct_map()
            self._direct_map_built = True
        return [self.index.reconstruct(int(v)).tolist() for v in vids]


class QdrantBackend:
    name = "qdrant"
    nlist = 0
    nprobe = 0

    def __init__(
        self, summary, url=None, collection=None, api_key=None, client_config=None
    ):
        from qdrant_client import QdrantClient

        client_options = dict(client_config or {})
        if url:
            client_options["url"] = url
        if api_key:
            client_options["api_key"] = api_key
        if not any(
            key in client_options for key in ("url", "host", "location", "path")
        ):
            raise ValueError(
                "Qdrant requires --qdrant-url or an endpoint in "
                "--qdrant-client-config"
            )
        self.collection = collection or summary.get("collection", "pixelrag")
        self.client = QdrantClient(**client_options)
        config = self.client.get_collection(self.collection).config.params.vectors
        self.dimension = config.size

    @property
    def ntotal(self) -> int:
        return self.client.count(self.collection, exact=True).count

    def set_nprobe(self, n):
        pass

    def reset_nprobe(self):
        pass

    @staticmethod
    def _hit(point):
        payload = point.payload
        return {
            "score": float(point.score),
            "vector_id": point.id,
            **{field: int(payload[field]) for field in _META_FIELDS},
        }

    def raw_search(self, query_vectors, k, min_tile_height=None):
        from qdrant_client import models

        if k <= 0:
            return [[] for _ in query_vectors]

        query_filter = (
            models.Filter(
                must=[
                    models.FieldCondition(
                        key="tile_height",
                        range=models.Range(gte=min_tile_height),
                    )
                ]
            )
            if min_tile_height
            else None
        )
        requests = [
            models.QueryRequest(
                query=v.tolist(),
                limit=k,
                with_payload=True,
                filter=query_filter,
            )
            for v in query_vectors
        ]
        responses = self.client.query_batch_points(self.collection, requests=requests)
        return [
            [self._hit(point) for point in response.points]
            for response in responses
        ]

    def reconstruct(self, vids):
        points = self.client.retrieve(
            self.collection, ids=vids, with_vectors=True
        )
        vectors = {point.id: point.vector for point in points}
        return [vectors.get(vid) for vid in vids]


def make_backend(args, summary: dict) -> VectorBackend:
    backend = getattr(args, "backend", None) or summary.get("backend", "faiss")

    if backend == "ivf":
        backend = "faiss"
    if backend == "faiss":
        return FaissBackend(args.index_dir, summary)
    if backend == "qdrant":
        return QdrantBackend(
            summary,
            url=getattr(args, "qdrant_url", None),
            collection=getattr(args, "collection", None),
            api_key=getattr(args, "qdrant_api_key", None),
            client_config=getattr(args, "qdrant_client_config", None),
        )
    raise ValueError(f"unknown backend: {backend!r} (expected 'faiss' or 'qdrant')")
