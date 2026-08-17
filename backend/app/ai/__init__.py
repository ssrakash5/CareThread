"""AWS-backed AI + storage integrations (Amazon Bedrock, S3).

Each module exposes a function with the same signature as its local
stand-in so callers dispatch on ``settings.ai_provider`` and never care
which backend served the request.
"""
