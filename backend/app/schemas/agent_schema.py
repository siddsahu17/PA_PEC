from pydantic import BaseModel
from typing import List

class VisionAgentOutput(BaseModel):
    objects: List[str]
    spatial_relationships: List[str]
    labels: List[str]
    overall_context: str
