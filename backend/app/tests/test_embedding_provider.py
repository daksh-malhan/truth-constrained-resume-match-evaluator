from app.services.embedding_provider import embed_texts


def test_embed_texts_returns_one_normalized_vector_per_input(monkeypatch):
    monkeypatch.setenv("EMBEDDING_PROVIDER", "mock")
    vectors = embed_texts(["Python REST APIs", "Docker containers"])
    assert len(vectors) == 2
    assert len(vectors[0]) == len(vectors[1])
    assert all(abs(sum(value * value for value in vector) - 1.0) < 0.0001 for vector in vectors)
