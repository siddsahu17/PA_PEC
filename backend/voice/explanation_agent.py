import logging
import os

from openai import OpenAI

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Per-language system prompts that enforce native output with cultural nuance
# ---------------------------------------------------------------------------

_PROMPTS: dict[str, str] = {
    "en-IN": (
        "You are an expert science educator creating vivid, sensory-rich audio descriptions "
        "of scientific diagrams for blind and visually impaired students aged 10–14 from India.\n\n"
        "Your goal is to help the student build a complete mental image through sound alone.\n\n"
        "RULES:\n"
        "• Start with a single sentence that gives the big picture — what is this thing and what does it do?\n"
        "• Describe structure using familiar objects: 'shaped like a coiled garden hose', "
        "'feels like smooth velvet', 'as wide as your thumb'.\n"
        "• Use positional language clearly: 'at the very top', 'directly below that', "
        "'running alongside on the left', 'tucked behind'.\n"
        "• Include movement, texture, or temperature where relevant: 'waves rhythmically', "
        "'smooth and slightly warm', 'expands like a balloon'.\n"
        "• Build the description in layers — overview first, then major parts, then fine details.\n"
        "• Use analogies from everyday Indian life: a water pot, a neem twig, a sari, a roti.\n"
        "• Keep sentences short and rhythmic — this is spoken aloud, not read.\n"
        "• End with ONE memorable summary sentence the student can hold in their mind.\n"
        "• NEVER use visual-only language like 'as you can see' or 'look at'.\n"
        "• Respond ONLY in clear, simple Indian English."
    ),

    "hi-IN": (
        "आप एक विशेषज्ञ विज्ञान शिक्षक हैं। आप दृष्टिहीन विद्यार्थियों (कक्षा 5–8) के लिए "
        "वैज्ञानिक आरेखों का जीवंत, इंद्रियग्राहक वर्णन करते हैं जो केवल कानों से सुनकर "
        "मानसिक चित्र बना सकें।\n\n"
        "नियम:\n"
        "• पहले एक वाक्य में पूरी बात बताएं — यह क्या है और क्या करता है।\n"
        "• आकार को परिचित वस्तुओं से समझाएं: 'मुड़ी हुई नली जैसा', 'रोटी जैसा गोल', "
        "'तुलसी की पत्ती जैसा सपाट'।\n"
        "• स्थान स्पष्ट करें: 'सबसे ऊपर', 'उसके ठीक नीचे', 'बाईं ओर', 'पीछे की तरफ'।\n"
        "• हलचल, बनावट और तापमान बताएं: 'लहरों की तरह सिकुड़ता है', 'मुलायम और चिकना', "
        "'गुब्बारे जैसा फैलता है'।\n"
        "• भारतीय जीवन के उदाहरण दें: घड़ा, नीम की टहनी, रोटी बेलना, सूती कपड़ा।\n"
        "• वाक्य छोटे और लयबद्ध रखें — यह बोला जाएगा, पढ़ा नहीं।\n"
        "• अंत में एक ऐसा वाक्य दें जो विद्यार्थी हमेशा याद रखे।\n"
        "• 'देखो' या 'जैसा दिखता है' जैसे शब्द न लिखें।\n"
        "• केवल सरल, स्पष्ट हिंदी में उत्तर दें।"
    ),

    "mr-IN": (
        "तुम्ही एक तज्ञ विज्ञान शिक्षक आहात. तुम्ही दृष्टिहीन विद्यार्थ्यांसाठी (इयत्ता 5–8) "
        "वैज्ञानिक आकृत्यांचे जिवंत, इंद्रियग्राहक वर्णन करता — जे फक्त कानांनी ऐकून "
        "मनात चित्र उभे करता येईल.\n\n"
        "नियम:\n"
        "• प्रथम एका वाक्यात संपूर्ण गोष्ट सांगा — हे काय आहे आणि काय करते.\n"
        "• आकार परिचित वस्तूंनी समजावा: 'वाकलेल्या नळीसारखे', 'भाकरीसारखे गोल', "
        "'तुळशीच्या पानासारखे सपाट'.\n"
        "• स्थान स्पष्ट करा: 'अगदी वर', 'त्याच्या खाली', 'डाव्या बाजूला', 'मागे'.\n"
        "• हालचाल, पोत आणि तापमान सांगा: 'लाटांसारखे आकुंचन पावते', 'मऊ आणि गुळगुळीत', "
        "'फुग्यासारखे फुगते'.\n"
        "• महाराष्ट्रातील दैनंदिन जीवनातील उदाहरणे द्या: माठ, कडुनिंबाची फांदी, "
        "'भाकरी लाटणे', सुती कापड.\n"
        "• वाक्ये छोटी आणि लयबद्ध ठेवा — हे बोलले जाईल, वाचले जाणार नाही.\n"
        "• शेवटी एक संस्मरणीय वाक्य द्या जे विद्यार्थी कायम लक्षात ठेवेल.\n"
        "• 'बघा' किंवा 'दिसते' असे शब्द वापरू नका.\n"
        "• केवळ सरळ, स्पष्ट मराठीत उत्तर द्या."
    ),
}

_FALLBACK_ERRORS = {
    "hi-IN": "क्षमा करें, विवरण उत्पन्न करने में त्रुटि हुई। कृपया पुनः प्रयास करें।",
    "mr-IN": "क्षमस्व, वर्णन तयार करताना त्रुटी आली. कृपया पुन्हा प्रयत्न करा.",
    "en-IN": "Sorry, I could not generate the description. Please try again.",
}


class ExplanationAgent:
    """
    Converts a factual diagram JSON dict (from DiagramRAGAgent) into a vivid,
    language-native mental visualization script for blind students.
    Supports English (en-IN), Hindi (hi-IN), and Marathi (mr-IN).
    """

    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def generate(self, diagram_data: dict, language_code: str = "en-IN") -> str:
        """
        Generate a sensory-rich spoken description of the diagram.

        Args:
            diagram_data: Factual JSON dict from DiagramRAGAgent.retrieve().
            language_code: Target language — 'en-IN', 'hi-IN', or 'mr-IN'.

        Returns:
            A vivid description string ready to be spoken aloud via TTS.
        """
        system_prompt = _PROMPTS.get(language_code, _PROMPTS["en-IN"])
        user_message = (
            "Create a vivid spoken description of the following scientific diagram "
            "for a blind student. Use the factual data below — do NOT add facts that "
            "are not present in the data.\n\n"
            f"{self._format_diagram(diagram_data)}"
        )

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                max_tokens=900,
                temperature=0.65,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error("ExplanationAgent failed for language %s: %s", language_code, e)
            return _FALLBACK_ERRORS.get(language_code, _FALLBACK_ERRORS["en-IN"])

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _format_diagram(self, data: dict) -> str:
        lines: list[str] = [
            f"TOPIC: {data.get('topic', 'Unknown')}",
            f"CLASS: {data.get('class', '')}  |  CHAPTER: {data.get('chapter', '')}",
        ]

        overview = data.get("overview")
        if overview:
            lines += ["", f"OVERVIEW:\n{overview}"]

        components: list[dict] = data.get("components", [])
        if components:
            lines.append("\nCOMPONENTS:")
            for c in components:
                lines.append(
                    f"  [{c.get('name', '')}]\n"
                    f"    Function  : {c.get('function', '')}\n"
                    f"    Location  : {c.get('location', '')}\n"
                    f"    Sensory   : {c.get('sensory_detail', '')}"
                )

        process: list[dict] = data.get("process_flow", [])
        if process:
            lines.append("\nPROCESS FLOW (in order):")
            for step in process:
                lines.append(f"  Step {step.get('step', '')}: {step.get('description', '')}")

        facts: list[str] = data.get("key_facts", [])
        if facts:
            lines.append("\nKEY FACTS:")
            for fact in facts:
                lines.append(f"  • {fact}")

        return "\n".join(lines)
