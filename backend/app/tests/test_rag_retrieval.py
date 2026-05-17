from app import database
from app.schemas import ResumeSection
from app.services.rag_indexer import build_chunks, retrieve


def test_rag_retrieval_returns_original_source_chunks_only():
    database.init_db()
    run_id = "run_rag_test"
    sections = [ResumeSection(id="s1", section_name="Projects", text="Built a FastAPI RAG chatbot using FAISS.", page_number=1, source_quote="Built a FastAPI RAG chatbot using FAISS.")]
    chunks = build_chunks(run_id, sections, ["Need RAG and vector search experience."], 600, 100)
    assert all("Suggested improvement" not in chunk.text for chunk in chunks)
    results = retrieve(run_id, "RAG vector search", "both", 3)
    assert results
    assert {result.source_type.value for result in results}.issubset({"resume", "job_description"})

