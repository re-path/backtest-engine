from google import genai
from google.genai import types
import json
import time
import random
import io
import base64
from typing import Dict, List, Any, Optional, Union
from enum import Enum
from PIL import Image


class PrePrompts(Enum):
    FINANCIAL_QUARTERLY_REPORT = """
    from the given image or text (only two languages are there english and nepali so keep that in mind), you only extract important financial information, and output in english in the following way:

    REVENUE_INCREASED:2%,SHARE_PRICE:2548,SOME_OTHER_METRIC:xxx,SOME_TYPE_OF_SENTIMENT:xx,SOME_TYPE_OF_CONTEXTUAL_DETAIL:xxx
    (I am not saying these EXACT metrics should be there, but don't leave anything that is in the image or text, ALL should be included, no exceptions)
    Also the texts should be ENGLISH text, and number should be english numbers.

    In this way write in short but don't leave any kind of detail that would help financially to make trading decisions, keep small to small information, there but in the concise format I provided you. It should be very very concise but should include all the detail. For contextual things the value after : should be of max 5 words. You do not say anything else except in the format above
    """


class PromptType(Enum):
    STRING = "string"
    SINGLE_NUMERIC_VALUE = "single_numeric_value"
    JSON = "json"
    BOOLEAN = "boolean"
    LIST = "list"
    MARKDOWN = "markdown"
    IMAGETOTEXT = "image_to_text"


class GeminiModel(Enum):
    GEMINI_PRO_2_5 = "gemini-2.5-pro"
    GEMINI_FLASH_2_5 = "gemini-2.5-flash"
    GEMINI_FLASH_EXP_2_0 = "gemini-2.0-flash-exp"
    GEMINI_PRO_1_5 = "gemini-1.5-pro"
    GEMINI_FLASH_1_5 = "gemini-1.5-flash"


class GeminiLLM:
    def __init__(
        self,
        api_keys: Union[str, List[str]],
        models: Optional[List[GeminiModel]] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ) -> None:
        self.api_keys: List[str] = [api_keys] if isinstance(api_keys, str) else api_keys
        self.models: List[GeminiModel] = models or [
            GeminiModel.GEMINI_PRO_2_5,
            GeminiModel.GEMINI_FLASH_2_5,
            GeminiModel.GEMINI_FLASH_EXP_2_0,
            GeminiModel.GEMINI_PRO_1_5,
            GeminiModel.GEMINI_FLASH_1_5,
        ]
        self.max_retries: int = max_retries
        self.retry_delay: float = retry_delay
        self.current_api_key_index: int = 0
        self.current_model_index: int = 0
        self.clients: Dict[str, Any] = {}
        self.prompt_configs: Dict[PromptType, Dict[str, str]] = {
            PromptType.STRING: {
                "system_prompt": "",
                "format_instruction": "Provide your response as plain text.",
            },
            PromptType.SINGLE_NUMERIC_VALUE: {
                "system_prompt": "You are a data extraction assistant. Extract only the single most relevant numeric value. Only a single value, and that should not have any commas and all, just a single value ALWAYS float that can be easily parsed",
                "format_instruction": "Return only a single number without any text, currency symbols, or explanations. If no number is found, return 0.",
            },
            PromptType.JSON: {
                "system_prompt": "You are a JSON formatter assistant. Convert information into valid JSON format.",
                "format_instruction": "Return only valid JSON without any markdown formatting or explanations. Use double quotes for strings.",
            },
            PromptType.BOOLEAN: {
                "system_prompt": "You are a boolean evaluator. Determine if the statement or question has a true/false answer.",
                "format_instruction": "Return only 'true' or 'false' in lowercase without any explanations.",
            },
            PromptType.LIST: {
                "system_prompt": "You are a list generator. Convert information into a structured list format.",
                "format_instruction": "Return items as a JSON array format. Each item should be a string.",
            },
            PromptType.MARKDOWN: {
                "system_prompt": "You are a markdown formatter. Structure your response using proper markdown syntax.",
                "format_instruction": "Use proper markdown formatting with headers, bullet points, and emphasis where appropriate.",
            },
            PromptType.IMAGETOTEXT: {
                "system_prompt": "You are a precise Optical Character Recognition (OCR) engine. Your sole function is to extract any and all text from the provided image, verbatim. Preserve all original line breaks and spacing as best as possible. Do not interpret, correct, or reformat the text.",
                "format_instruction": "Output only the raw text transcribed from the image. Do not add any formatting, markdown, or conversational text. Your entire response must be the text content of the image and nothing more. Also see for capital small letters as well, the images can be text in a noisy environment, filter it properly and write the letter with appropriate cases (lower case and upper case), AS IT IS.",
            },
        }

    def _get_current_api_key(self) -> str:
        return self.api_keys[self.current_api_key_index]

    def _get_current_model(self) -> GeminiModel:
        return self.models[self.current_model_index]

    def _rotate_api_key(self) -> None:
        self.current_api_key_index = (self.current_api_key_index + 1) % len(
            self.api_keys
        )
        self.clients.clear()

    def _rotate_model(self) -> None:
        self.current_model_index = (self.current_model_index + 1) % len(self.models)

    def _get_client(self, api_key: str) -> Any:
        if api_key not in self.clients:
            self.clients[api_key] = genai.Client(api_key=api_key)
        return self.clients[api_key]

    def _build_prompt(self, user_prompt: str, prompt_type: PromptType) -> str:
        config: Dict[str, str] = self.prompt_configs[prompt_type]
        system_prompt: str = config["system_prompt"]
        format_instruction: str = config["format_instruction"]
        return f"{system_prompt}\n\n{format_instruction}\n\nUser Query: {user_prompt}"

    def _make_request(
        self,
        prompt: str,
        model: GeminiModel,
        client: Any,
        image: Optional[Union[str, bytes, Image.Image]] = None,
    ) -> str:
        if image:
            image_data = self._process_image(image)
            contents = [types.Part.from_bytes(**image_data), prompt]
        else:
            contents = prompt

        response: Any = client.models.generate_content(
            model=model.value,
            contents=contents,
            config=types.GenerateContentConfig(
                temperature=0.1,
                top_k=1,
                top_p=0.8,
                max_output_tokens=2048,
                safety_settings=[
                    types.SafetySetting(
                        category=types.HarmCategory.HARM_CATEGORY_CIVIC_INTEGRITY,
                        threshold=types.HarmBlockThreshold.BLOCK_NONE,
                    ),
                    types.SafetySetting(
                        category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                        threshold=types.HarmBlockThreshold.BLOCK_NONE,
                    ),
                    types.SafetySetting(
                        category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                        threshold=types.HarmBlockThreshold.BLOCK_NONE,
                    ),
                    types.SafetySetting(
                        category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                        threshold=types.HarmBlockThreshold.BLOCK_NONE,
                    ),
                ],
            ),
        )
        if not response.text:
            raise ValueError("Empty response from model")
        return response.text.strip()

    def _process_image(self, image: Union[str, bytes, Image.Image]) -> Dict[str, Any]:
        if isinstance(image, str):
            if image.startswith("data:image"):
                image_data = image.split(",")[1]
                image_bytes = base64.b64decode(image_data)
                mime_type = image.split(";")[0].split(":")[1]
            else:
                with open(image, "rb") as f:
                    image_bytes = f.read()
                mime_type = f"image/{image.split('.')[-1].lower()}"
        elif isinstance(image, bytes):
            image_bytes = image
            mime_type = "image/png"
        elif isinstance(image, Image.Image):
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG")
            image_bytes = buffer.getvalue()
            mime_type = "image/jpeg"
        else:
            raise ValueError("Unsupported image type")

        return {
            "mime_type": mime_type,
            "data": base64.b64encode(image_bytes).decode("utf-8"),
        }

    def _post_process_response(self, text: str, prompt_type: PromptType) -> str:
        if prompt_type == PromptType.SINGLE_NUMERIC_VALUE:
            import re

            numbers: List[str] = re.findall(r"-?\d+\.?\d*", text)
            return numbers[0] if numbers else "0"
        elif prompt_type == PromptType.JSON:
            try:
                json.loads(text)
                return text
            except json.JSONDecodeError:
                start_idx: int = text.find("{")
                end_idx: int = text.rfind("}")
                if start_idx != -1 and end_idx != -1:
                    json_text: str = text[start_idx : end_idx + 1]
                    try:
                        json.loads(json_text)
                        return json_text
                    except json.JSONDecodeError:
                        pass
                start_idx = text.find("[")
                end_idx = text.rfind("]")
                if start_idx != -1 and end_idx != -1:
                    json_text = text[start_idx : end_idx + 1]
                    try:
                        json.loads(json_text)
                        return json_text
                    except json.JSONDecodeError:
                        pass
                return '{"error": "Invalid JSON response"}'
        elif prompt_type == PromptType.BOOLEAN:
            text_lower: str = text.lower().strip()
            if "true" in text_lower:
                return "true"
            elif "false" in text_lower:
                return "false"
            else:
                return "false"
        elif prompt_type == PromptType.LIST:
            try:
                json.loads(text)
                return text
            except json.JSONDecodeError:
                start_idx: int = text.find("[")
                end_idx: int = text.rfind("]")
                if start_idx != -1 and end_idx != -1:
                    list_text: str = text[start_idx : end_idx + 1]
                    try:
                        json.loads(list_text)
                        return list_text
                    except json.JSONDecodeError:
                        pass
                return "[]"
        return text

    def ask(
        self,
        user_prompt: str,
        prompt_type: Union[PromptType, str] = PromptType.STRING,
        preferred_model: Optional[GeminiModel] = None,
        image: Optional[Union[str, bytes, Image.Image]] = None,
    ) -> str:
        if isinstance(prompt_type, str):
            try:
                prompt_type = PromptType(prompt_type.lower())
            except ValueError:
                prompt_type = PromptType.STRING

        formatted_prompt: str = self._build_prompt(user_prompt, prompt_type)

        if preferred_model and preferred_model in self.models:
            try:
                return self._try_single_model(
                    formatted_prompt, preferred_model, prompt_type, image
                )
            except Exception:
                pass

        return self._try_all_models(formatted_prompt, prompt_type, image)

    def _try_single_model(
        self,
        formatted_prompt: str,
        model: GeminiModel,
        prompt_type: PromptType,
        image: Optional[Union[str, bytes, Image.Image]] = None,
    ) -> str:
        api_key_attempts: int = 0
        last_exception: Optional[Exception] = None

        while api_key_attempts < len(self.api_keys):
            current_api_key: str = self._get_current_api_key()
            client: Any = self._get_client(current_api_key)

            for retry in range(self.max_retries):
                try:
                    response_text: str = self._make_request(
                        formatted_prompt, model, client, image
                    )
                    final_response: str = self._post_process_response(
                        response_text, prompt_type
                    )
                    return final_response
                except Exception as e:
                    last_exception = e
                    if retry < self.max_retries - 1:
                        sleep_time: float = self.retry_delay * (
                            2**retry
                        ) + random.uniform(0, 1)
                        time.sleep(sleep_time)
                    continue

            self._rotate_api_key()
            api_key_attempts += 1

        raise Exception(
            f"Single model {model.name} failed with all API keys. Last error: {last_exception}"
        )

    def _try_all_models(
        self,
        formatted_prompt: str,
        prompt_type: PromptType,
        image: Optional[Union[str, bytes, Image.Image]] = None,
    ) -> str:
        api_key_attempts: int = 0
        model_attempts: int = 0
        last_exception: Optional[Exception] = None

        while api_key_attempts < len(self.api_keys):
            current_api_key: str = self._get_current_api_key()
            client: Any = self._get_client(current_api_key)
            model_attempts = 0

            while model_attempts < len(self.models):
                current_model: GeminiModel = self._get_current_model()

                for retry in range(self.max_retries):
                    try:
                        response_text: str = self._make_request(
                            formatted_prompt, current_model, client, image
                        )
                        final_response: str = self._post_process_response(
                            response_text, prompt_type
                        )
                        return final_response
                    except Exception as e:
                        last_exception = e
                        if retry < self.max_retries - 1:
                            sleep_time: float = self.retry_delay * (
                                2**retry
                            ) + random.uniform(0, 1)
                            time.sleep(sleep_time)
                        continue

                self._rotate_model()
                model_attempts += 1

            self._rotate_api_key()
            api_key_attempts += 1

        raise Exception(f"All API keys and models failed. Last error: {last_exception}")

    def ask_batch(
        self,
        prompts: List[str],
        prompt_type: Union[PromptType, str] = PromptType.STRING,
        preferred_model: Optional[GeminiModel] = None,
    ) -> List[str]:
        results: List[str] = []
        for prompt in prompts:
            try:
                result: str = self.ask(prompt, prompt_type, preferred_model)
                results.append(result)
            except Exception as e:
                results.append(f"Error: {str(e)}")
        return results

    def add_custom_prompt_type(
        self, prompt_type_name: str, system_prompt: str, format_instruction: str
    ) -> None:
        custom_type: PromptType = PromptType(prompt_type_name.lower())
        self.prompt_configs[custom_type] = {
            "system_prompt": system_prompt,
            "format_instruction": format_instruction,
        }

    def get_available_models(self, api_key: Optional[str] = None) -> List[str]:
        try:
            client: Any = self._get_client(api_key or self._get_current_api_key())
            models: Any = client.models.list()
            return [model.name for model in models]
        except Exception:
            return [model.value for model in self.models]

    def set_generation_config(
        self,
        temperature: float = 0.2,
        top_k: int = 1,
        top_p: float = 0.85,
        max_output_tokens: int = 2048,
    ) -> None:
        self.generation_config: Dict[str, Any] = {
            "temperature": temperature,
            "top_k": top_k,
            "top_p": top_p,
            "max_output_tokens": max_output_tokens,
        }

    def create_chat_session(
        self, api_key: Optional[str] = None, model: Optional[GeminiModel] = None
    ) -> Any:
        client: Any = self._get_client(api_key or self._get_current_api_key())
        model_name: str = (model or self._get_current_model()).value
        return client.chats.create(model=model_name)


def create_llm(
    api_keys: Union[str, List[str]], models: Optional[List[GeminiModel]] = None
) -> GeminiLLM:
    return GeminiLLM(api_keys=api_keys, models=models)
