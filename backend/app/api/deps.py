from app.core.pipeline import AssistantPipeline
from fastapi import Depends

def get_pipeline() -> AssistantPipeline:
    # In a real app we might want to dependency inject or pool instances.
    # We will instantiate a new pipeline per request for simplicity,
    # or return a singleton if agents are stateless.
    return AssistantPipeline()
