import pytest
from unittest.mock import AsyncMock, patch

from app.agents.vision_agent import VisionAgent
from app.agents.braille_agent import BrailleAgent

@pytest.mark.asyncio
async def test_vision_agent():
    agent = VisionAgent()
    mock_json = '{"objects": ["Heart"], "spatial_relationships": [], "labels": [], "overall_context": "diagram"}'
    
    with patch('app.services.openai_service.OpenAIService.analyze_image_with_vision', new_callable=AsyncMock) as mock_analyze:
        mock_analyze.return_value = mock_json
        result = await agent.analyze("dummy_path.jpg")
        
        assert "objects" in result
        assert result["objects"][0] == "Heart"

@pytest.mark.asyncio
async def test_braille_agent():
    agent = BrailleAgent()
    
    with patch('app.services.braille_service.BrailleService.translate') as mock_translate:
        mock_translate.return_value = "⠓⠑⠇⠇⠕"
        text = "hello"
        result = await agent.transcribe(text)
        
        assert "hello" in result
        assert "⠓⠑⠇⠇⠕" in result
