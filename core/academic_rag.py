"""
Academic Research Engine (RAG)
Monitors a folder, reads PDFs/texts, and indexes them into ChromaDB for research.
"""

import os
import glob
import fitz  # PyMuPDF
import hashlib
from typing import List
from sentence_transformers import SentenceTransformer

# Try to import chromadb, fallback if not available
try:
    import chromadb
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False

class AcademicResearchEngine:
    def __init__(self):
        self.data_dir = os.path.abspath("data/research_papers")
        os.makedirs(self.data_dir, exist_ok=True)
        self.embed_model = SentenceTransformer("all-MiniLM-L6-v2")
        self.chroma = None
        self.collection = None
        
        if CHROMA_AVAILABLE:
            # Must match KnowledgeStore's settings for the SAME path, else
            # chromadb raises "instance already exists ... with different settings".
            from chromadb.config import Settings as ChromaSettings
            self.chroma = chromadb.PersistentClient(
                path="data/chroma_research",
                settings=ChromaSettings(anonymized_telemetry=False),
            )
            self.collection = self.chroma.get_or_create_collection("academic_papers")
            
    def _get_hash(self, text: str) -> str:
        return hashlib.md5(text.encode()).hexdigest()

    def _chunk_text(self, text: str, chunk_size=1000, overlap=200) -> List[str]:
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunks.append(text[start:end])
            start += chunk_size - overlap
        return chunks

    def ingest_directory(self) -> str:
        """Scan data/research_papers and ingest all new PDFs and TXT files"""
        if not CHROMA_AVAILABLE:
            return "ChromaDB not installed."
            
        files = glob.glob(os.path.join(self.data_dir, "**/*.*"), recursive=True)
        ingested_count = 0
        
        for file in files:
            if file.endswith(".pdf"):
                text = self._read_pdf(file)
            elif file.endswith(".txt") or file.endswith(".md"):
                with open(file, "r", encoding="utf-8") as f:
                    text = f.read()
            else:
                continue
                
            filename = os.path.basename(file)
            
            # Simple check if already ingested (we'll just use the filename as an ID prefix)
            existing = self.collection.get(where={"source": filename})
            if existing and existing["ids"]:
                continue # Already ingested
                
            chunks = self._chunk_text(text)
            
            ids = []
            docs = []
            metadatas = []
            embeddings = []
            
            for i, chunk in enumerate(chunks):
                chunk_id = f"{filename}_chunk_{i}"
                ids.append(chunk_id)
                docs.append(chunk)
                metadatas.append({"source": filename, "chunk": i})
                embeddings.append(self.embed_model.encode(chunk).tolist())
                
            if ids:
                self.collection.add(
                    ids=ids,
                    documents=docs,
                    embeddings=embeddings,
                    metadatas=metadatas
                )
                ingested_count += 1
                
        return f"Successfully scanned directory. Ingested {ingested_count} new documents."

    def _read_pdf(self, path: str) -> str:
        try:
            doc = fitz.open(path)
            text = ""
            for page in doc:
                text += page.get_text() + "\n\n"
            return text
        except Exception as e:
            print(f"Error reading PDF {path}: {e}")
            return ""

    def query_research(self, query: str, n_results: int = 3) -> str:
        """Query the research database"""
        if not CHROMA_AVAILABLE:
            return "ChromaDB not installed."
            
        if self.collection.count() == 0:
            return "Research database is empty. Please place PDFs in data/research_papers and run ingest."
            
        query_embedding = self.embed_model.encode(query).tolist()
        
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )
        
        if not results["documents"][0]:
            return "No relevant research found."
            
        output = f"Research Results for '{query}':\n\n"
        for i, doc in enumerate(results["documents"][0]):
            source = results["metadatas"][0][i]["source"]
            output += f"--- Source: {source} ---\n{doc}...\n\n"
            
        return output