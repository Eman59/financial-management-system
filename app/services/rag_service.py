import uuid
from typing import Optional
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
)
from langchain.text_splitter import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer, CrossEncoder

from app.config import get_settings
from app.models.document import Document

settings = get_settings()


class RAGService:
    def __init__(self):
        self._client: Optional[QdrantClient] = None
        self._embedding_model: Optional[SentenceTransformer] = None
        self._reranker: Optional[CrossEncoder] = None
        self._text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

    @property
    def client(self) -> QdrantClient:
        if self._client is None:
            try:
                client = QdrantClient(
                    host=settings.QDRANT_HOST, port=settings.QDRANT_PORT, timeout=2
                )
                # Test connection
                client.get_collections()
                self._client = client
            except Exception:
                # Fallback to in-memory for development/testing
                self._client = QdrantClient(":memory:")
            self._ensure_collection()
        return self._client

    @property
    def embedding_model(self) -> SentenceTransformer:
        if self._embedding_model is None:
            self._embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL)
        return self._embedding_model

    @property
    def reranker(self) -> CrossEncoder:
        if self._reranker is None:
            self._reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
        return self._reranker

    def _ensure_collection(self):
        """Create the Qdrant collection if it doesn't exist."""
        collections = self.client.get_collections().collections
        collection_names = [c.name for c in collections]

        if settings.QDRANT_COLLECTION not in collection_names:
            self.client.create_collection(
                collection_name=settings.QDRANT_COLLECTION,
                vectors_config=VectorParams(
                    size=384,  # all-MiniLM-L6-v2 output dimension
                    distance=Distance.COSINE,
                ),
            )

    def chunk_text(self, text: str) -> list[str]:
        """Split text into semantic chunks."""
        if not text or not text.strip():
            return []
        chunks = self._text_splitter.split_text(text)
        return [chunk for chunk in chunks if chunk.strip()]

    def generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of texts."""
        if not texts:
            return []
        embeddings = self.embedding_model.encode(texts, show_progress_bar=False)
        return embeddings.tolist()

    async def index_document(self, document: Document) -> int:
        """Index a document's content into the vector database."""
        if not document.content:
            return 0

        chunks = self.chunk_text(document.content)
        if not chunks:
            return 0

        embeddings = self.generate_embeddings(chunks)

        points = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            point_id = str(uuid.uuid4())
            points.append(
                PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload={
                        "document_id": document.id,
                        "title": document.title,
                        "company_name": document.company_name,
                        "document_type": document.document_type,
                        "chunk_text": chunk,
                        "chunk_index": i,
                    },
                )
            )

        self.client.upsert(
            collection_name=settings.QDRANT_COLLECTION,
            points=points,
        )

        return len(chunks)

    async def remove_document(self, document_id: str) -> bool:
        """Remove all embeddings for a document from the vector database."""
        self.client.delete(
            collection_name=settings.QDRANT_COLLECTION,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="document_id",
                        match=MatchValue(value=document_id),
                    )
                ]
            ),
        )
        return True

    async def search(
        self,
        query: str,
        top_k: int = 5,
        document_type: Optional[str] = None,
        company_name: Optional[str] = None,
    ) -> list[dict]:
        """Perform semantic search with optional reranking."""
        # Generate query embedding
        query_embedding = self.embedding_model.encode(query).tolist()

        # Build filter conditions
        filter_conditions = []
        if document_type:
            filter_conditions.append(
                FieldCondition(
                    key="document_type",
                    match=MatchValue(value=document_type),
                )
            )
        if company_name:
            filter_conditions.append(
                FieldCondition(
                    key="company_name",
                    match=MatchValue(value=company_name),
                )
            )

        search_filter = None
        if filter_conditions:
            search_filter = Filter(must=filter_conditions)

        # Retrieve top 20 results for reranking
        initial_results = self.client.search(
            collection_name=settings.QDRANT_COLLECTION,
            query_vector=query_embedding,
            limit=20,
            query_filter=search_filter,
        )

        if not initial_results:
            return []

        # Rerank results
        reranked = self._rerank_results(query, initial_results, top_k)
        return reranked

    def _rerank_results(
        self, query: str, results: list, top_k: int
    ) -> list[dict]:
        """Rerank search results using a cross-encoder model."""
        if not results:
            return []

        # Prepare pairs for reranking
        pairs = [(query, r.payload["chunk_text"]) for r in results]

        # Get reranking scores
        scores = self.reranker.predict(pairs)

        # Combine results with reranking scores
        scored_results = []
        for result, score in zip(results, scores):
            scored_results.append(
                {
                    "document_id": result.payload["document_id"],
                    "title": result.payload["title"],
                    "company_name": result.payload["company_name"],
                    "document_type": result.payload["document_type"],
                    "chunk_text": result.payload["chunk_text"],
                    "relevance_score": float(score),
                }
            )

        # Sort by reranking score and return top_k
        scored_results.sort(key=lambda x: x["relevance_score"], reverse=True)
        return scored_results[:top_k]

    async def get_document_context(self, document_id: str) -> dict:
        """Get context for a specific document including related chunks."""
        # Get all chunks for this document
        results = self.client.scroll(
            collection_name=settings.QDRANT_COLLECTION,
            scroll_filter=Filter(
                must=[
                    FieldCondition(
                        key="document_id",
                        match=MatchValue(value=document_id),
                    )
                ]
            ),
            limit=100,
        )

        chunks = []
        if results and results[0]:
            for point in results[0]:
                chunks.append(
                    {
                        "chunk_index": point.payload.get("chunk_index", 0),
                        "chunk_text": point.payload.get("chunk_text", ""),
                    }
                )

        # Find related documents by searching with the first chunk
        related_documents = []
        if chunks:
            first_chunk = chunks[0]["chunk_text"]
            query_embedding = self.embedding_model.encode(first_chunk).tolist()

            related_results = self.client.search(
                collection_name=settings.QDRANT_COLLECTION,
                query_vector=query_embedding,
                limit=5,
                query_filter=Filter(
                    must_not=[
                        FieldCondition(
                            key="document_id",
                            match=MatchValue(value=document_id),
                        )
                    ]
                ),
            )

            seen_docs = set()
            for r in related_results:
                doc_id = r.payload["document_id"]
                if doc_id not in seen_docs:
                    seen_docs.add(doc_id)
                    related_documents.append(
                        {
                            "document_id": doc_id,
                            "title": r.payload["title"],
                            "company_name": r.payload["company_name"],
                            "relevance_score": float(r.score),
                        }
                    )

        return {
            "chunks": sorted(chunks, key=lambda x: x["chunk_index"]),
            "related_documents": related_documents,
        }


# Singleton instance
rag_service = RAGService()
