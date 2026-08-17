"""
Amazon Bedrock clients.

* Claude (via the Anthropic SDK's ``AnthropicBedrock`` client, which signs
  requests with the ambient AWS credentials) for extraction and matching.
* Titan Text Embeddings v2 (via boto3 ``bedrock-runtime``) for chunk embeddings.

Clients are created lazily so importing this module never touches the network.
"""
import json
import logging
from functools import lru_cache
from typing import Any, Dict, List

from app.config import settings, aws_credential_kwargs, anthropic_bedrock_kwargs

log = logging.getLogger("carethread.bedrock")


@lru_cache(maxsize=1)
def claude_client():
    from anthropic import AnthropicBedrock
    return AnthropicBedrock(aws_region=settings.aws_region, **anthropic_bedrock_kwargs())


@lru_cache(maxsize=1)
def bedrock_runtime():
    import boto3
    return boto3.client("bedrock-runtime", region_name=settings.aws_region, **aws_credential_kwargs())


def embed_text_bedrock(text: str) -> List[float]:
    """Titan v2 embedding, L2-normalised so dot product == cosine similarity
    (the matching agent relies on that)."""
    body = json.dumps({
        "inputText": text[:8000],
        "dimensions": settings.embedding_dim,
        "normalize": True,
    })
    resp = bedrock_runtime().invoke_model(
        modelId=settings.bedrock_embed_model_id,
        body=body,
        contentType="application/json",
        accept="application/json",
    )
    return json.loads(resp["body"].read())["embedding"]


def structured_call(
    *,
    system: str,
    user: str,
    tool_name: str,
    tool_description: str,
    input_schema: Dict[str, Any],
    max_tokens: int = 2048,
) -> Dict[str, Any]:
    """Ask Claude for a schema-conforming JSON object by forcing a single tool
    call. Forced ``tool_choice`` guarantees the response is a ``tool_use``
    block whose ``input`` validates against ``input_schema``."""
    resp = claude_client().messages.create(
        model=settings.bedrock_model_id,
        max_tokens=max_tokens,
        system=system,
        tools=[{"name": tool_name, "description": tool_description, "input_schema": input_schema}],
        tool_choice={"type": "tool", "name": tool_name},
        messages=[{"role": "user", "content": user}],
    )
    if resp.stop_reason == "refusal":
        raise RuntimeError("Bedrock/Claude refused the request")
    for block in resp.content:
        if block.type == "tool_use" and block.name == tool_name:
            return block.input  # already parsed JSON
    raise RuntimeError(f"No tool_use block in response (stop_reason={resp.stop_reason})")
