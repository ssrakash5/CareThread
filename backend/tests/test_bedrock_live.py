"""
Opt-in tests exercising real AWS Bedrock (Claude + Titan) calls. Excluded by
default (see pytest.ini); run explicitly with:

    pytest -m bedrock

Requires backend/.env to have CARETHREAD_AI_PROVIDER=bedrock and valid AWS
credentials (explicit keys, or the ambient AWS credential chain).
"""
import pytest

from app.config import settings

pytestmark = [
    pytest.mark.bedrock,
    pytest.mark.skipif(settings.ai_provider != "bedrock", reason="CARETHREAD_AI_PROVIDER is not 'bedrock'"),
]


def test_embed_text_bedrock_returns_vector():
    from app.ai.bedrock import embed_text_bedrock

    vec = embed_text_bedrock("6 mm solid pulmonary nodule in the right upper lobe")
    assert isinstance(vec, list)
    assert len(vec) == settings.embedding_dim
    assert all(isinstance(v, float) for v in vec)


def test_extract_document_bedrock_returns_findings():
    from app.ai.extraction import extract_document_bedrock

    result = extract_document_bedrock(
        "IMPRESSION:\n6 mm solid pulmonary nodule in the right upper lobe. "
        "Follow-up CT chest recommended in 6-12 months.",
        artifact_type="RADIOLOGY_REPORT",
    )
    assert result.findings
    assert result.findings[0].finding_type
