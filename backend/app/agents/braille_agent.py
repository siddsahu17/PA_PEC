import logging
from app.services.braille_service import BrailleService

logger = logging.getLogger("assistant_backend.braille_agent")

class BrailleAgent:
    async def transcribe(self, text: str) -> str:
        """
        Transcribes the english text to a combination format:
        English line followed by the Braille translation.
        """
        logger.info("Braille Agent generating Braille output")
        
        paragraphs = text.split("\n\n")
        combined_output = []
        
        for p in paragraphs:
            eng_text = p.strip()
            if not eng_text:
                continue
            # Translate paragraph
            braille_trans = BrailleService.translate(eng_text)
            combined_output.append(f"{eng_text}\n{braille_trans}")
            
        return "\n\n".join(combined_output)
