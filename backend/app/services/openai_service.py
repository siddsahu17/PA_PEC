from openai import AsyncOpenAI
import base64
from app.config.settings import settings

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

def encode_image_base64(image_path: str) -> str:
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

class OpenAIService:
    @staticmethod
    async def analyze_image_with_vision(image_path: str, system_prompt: str) -> str:
        base64_image = encode_image_base64(image_path)
        
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Please analyze this image and return the structured JSON only."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            response_format={ "type": "json_object" }
        )
        return response.choices[0].message.content

    @staticmethod
    async def generate_completion(system_prompt: str, user_prompt: str) -> str:
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )
        return response.choices[0].message.content
