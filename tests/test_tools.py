from infrastructure.retrieval.embedding_client import HashEmbeddingFunction
from infrastructure.tools.risk_matcher import match_risks
from infrastructure.tools.structure_checker import check_structure


def test_risk_matcher():
    hits = match_risks(
        "\u8fd9\u6b3e\u4ea7\u54c17\u5929\u89c1\u6548\uff0c"
        "\u7edd\u5bf9\u5b89\u5168\uff0c\u65e0\u526f\u4f5c\u7528\u3002"
    )
    assert len(hits) >= 2


def test_structure_checker():
    result = check_structure(
        "\u8fd9\u662f\u4e00\u6bb5\u6bd4\u8f83\u5b8c\u6574\u7684\u4f53\u9a8c\u5206\u4eab\u3002"
        "\u6211\u4f1a\u8bf4\u660e\u4f7f\u7528\u573a\u666f\u548c\u9002\u7528\u4eba\u7fa4\u3002",
        "xiaohongshu",
    )
    assert "score" in result


def test_hash_embedding_accepts_chroma_query_keyword():
    embedding = HashEmbeddingFunction(dimensions=8)

    direct = embedding.embed_query("\u7edd\u5bf9\u5b89\u5168")
    keyword = embedding.embed_query(input="\u7edd\u5bf9\u5b89\u5168")

    assert keyword == [direct]
    assert len(direct) == 8
    assert len(keyword[0]) == 8
