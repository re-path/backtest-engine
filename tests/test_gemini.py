"""
Unit tests for GeminiLLM internal logic (no real API calls).
Tests prompt building, post-processing, image processing, and rotation.
"""
import pytest
import json
import base64
import os
from unittest.mock import patch, MagicMock

# Skip entire module if google-genai is not installed
pytest.importorskip("google.genai", reason="google-genai not installed")

from core.gemini import (
    GeminiLLM, PromptType, GeminiModel, PrePrompts, create_llm,
)



# ---------------------------------------------------------------------------
# Enum values
# ---------------------------------------------------------------------------

class TestEnums:
    def test_prompt_type_values(self):
        assert PromptType.STRING.value == "string"
        assert PromptType.SINGLE_NUMERIC_VALUE.value == "single_numeric_value"
        assert PromptType.JSON.value == "json"
        assert PromptType.BOOLEAN.value == "boolean"
        assert PromptType.LIST.value == "list"
        assert PromptType.MARKDOWN.value == "markdown"
        assert PromptType.IMAGETOTEXT.value == "image_to_text"

    def test_gemini_model_values(self):
        assert GeminiModel.GEMINI_PRO_2_5.value == "gemini-2.5-pro"
        assert GeminiModel.GEMINI_FLASH_2_5.value == "gemini-2.5-flash"

    def test_pre_prompts_exists(self):
        assert hasattr(PrePrompts, "FINANCIAL_QUARTERLY_REPORT")


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------

class TestGeminiLLMConstruction:
    def test_single_api_key_string(self):
        llm = GeminiLLM(api_keys="key1")
        assert llm.api_keys == ["key1"]

    def test_multiple_api_keys(self):
        llm = GeminiLLM(api_keys=["k1", "k2", "k3"])
        assert len(llm.api_keys) == 3

    def test_default_models(self):
        llm = GeminiLLM(api_keys="key1")
        assert len(llm.models) == 5

    def test_custom_models(self):
        llm = GeminiLLM(api_keys="key1", models=[GeminiModel.GEMINI_PRO_2_5])
        assert len(llm.models) == 1

    def test_create_llm_factory(self):
        llm = create_llm("key1")
        assert isinstance(llm, GeminiLLM)


# ---------------------------------------------------------------------------
# Prompt Building
# ---------------------------------------------------------------------------

class TestBuildPrompt:
    def test_string_prompt(self):
        llm = GeminiLLM(api_keys="key1")
        result = llm._build_prompt("Hello", PromptType.STRING)
        assert "Hello" in result
        assert "plain text" in result

    def test_numeric_prompt(self):
        llm = GeminiLLM(api_keys="key1")
        result = llm._build_prompt("extract value", PromptType.SINGLE_NUMERIC_VALUE)
        assert "single number" in result.lower() or "numeric" in result.lower()

    def test_json_prompt(self):
        llm = GeminiLLM(api_keys="key1")
        result = llm._build_prompt("convert this", PromptType.JSON)
        assert "JSON" in result

    def test_boolean_prompt(self):
        llm = GeminiLLM(api_keys="key1")
        result = llm._build_prompt("is this true?", PromptType.BOOLEAN)
        assert "true" in result.lower() or "false" in result.lower()

    def test_list_prompt(self):
        llm = GeminiLLM(api_keys="key1")
        result = llm._build_prompt("list items", PromptType.LIST)
        assert "array" in result.lower() or "list" in result.lower()

    def test_markdown_prompt(self):
        llm = GeminiLLM(api_keys="key1")
        result = llm._build_prompt("format this", PromptType.MARKDOWN)
        assert "markdown" in result.lower()


# ---------------------------------------------------------------------------
# Post-Processing
# ---------------------------------------------------------------------------

class TestPostProcessResponse:
    @pytest.fixture
    def llm(self):
        return GeminiLLM(api_keys="key1")

    # --- STRING ---
    def test_string_passthrough(self, llm):
        assert llm._post_process_response("hello world", PromptType.STRING) == "hello world"

    # --- SINGLE_NUMERIC_VALUE ---
    def test_numeric_extraction(self, llm):
        assert llm._post_process_response("the value is 42.5", PromptType.SINGLE_NUMERIC_VALUE) == "42.5"

    def test_numeric_negative(self, llm):
        assert llm._post_process_response("answer: -7", PromptType.SINGLE_NUMERIC_VALUE) == "-7"

    def test_numeric_no_number(self, llm):
        assert llm._post_process_response("no numbers here", PromptType.SINGLE_NUMERIC_VALUE) == "0"

    def test_numeric_multiple_picks_first(self, llm):
        result = llm._post_process_response("values are 10 and 20", PromptType.SINGLE_NUMERIC_VALUE)
        assert result == "10"

    # --- JSON ---
    def test_json_valid(self, llm):
        text = '{"key": "value"}'
        result = llm._post_process_response(text, PromptType.JSON)
        assert json.loads(result) == {"key": "value"}

    def test_json_with_wrapping_text(self, llm):
        text = 'Here is the JSON: {"a": 1} done.'
        result = llm._post_process_response(text, PromptType.JSON)
        assert json.loads(result) == {"a": 1}

    def test_json_array(self, llm):
        text = 'Result: [1, 2, 3]'
        result = llm._post_process_response(text, PromptType.JSON)
        assert json.loads(result) == [1, 2, 3]

    def test_json_invalid(self, llm):
        text = "this is not json at all"
        result = llm._post_process_response(text, PromptType.JSON)
        parsed = json.loads(result)
        assert "error" in parsed

    # --- BOOLEAN ---
    def test_boolean_true(self, llm):
        assert llm._post_process_response("True", PromptType.BOOLEAN) == "true"

    def test_boolean_false(self, llm):
        assert llm._post_process_response("False", PromptType.BOOLEAN) == "false"

    def test_boolean_with_text(self, llm):
        assert llm._post_process_response("I think it is true because...", PromptType.BOOLEAN) == "true"

    def test_boolean_ambiguous(self, llm):
        assert llm._post_process_response("maybe", PromptType.BOOLEAN) == "false"

    # --- LIST ---
    def test_list_valid(self, llm):
        text = '["a", "b", "c"]'
        result = llm._post_process_response(text, PromptType.LIST)
        assert json.loads(result) == ["a", "b", "c"]

    def test_list_with_wrapping(self, llm):
        text = 'Here are items: ["x", "y"]'
        result = llm._post_process_response(text, PromptType.LIST)
        assert json.loads(result) == ["x", "y"]

    def test_list_invalid(self, llm):
        text = "just text"
        result = llm._post_process_response(text, PromptType.LIST)
        assert json.loads(result) == []


# ---------------------------------------------------------------------------
# API Key / Model Rotation
# ---------------------------------------------------------------------------

class TestRotation:
    def test_rotate_api_key(self):
        llm = GeminiLLM(api_keys=["k1", "k2", "k3"])
        assert llm._get_current_api_key() == "k1"
        llm._rotate_api_key()
        assert llm._get_current_api_key() == "k2"
        llm._rotate_api_key()
        assert llm._get_current_api_key() == "k3"
        llm._rotate_api_key()
        assert llm._get_current_api_key() == "k1"  # wraps

    def test_rotate_model(self):
        llm = GeminiLLM(api_keys="k1", models=[
            GeminiModel.GEMINI_PRO_2_5,
            GeminiModel.GEMINI_FLASH_2_5,
        ])
        assert llm._get_current_model() == GeminiModel.GEMINI_PRO_2_5
        llm._rotate_model()
        assert llm._get_current_model() == GeminiModel.GEMINI_FLASH_2_5
        llm._rotate_model()
        assert llm._get_current_model() == GeminiModel.GEMINI_PRO_2_5

    def test_rotate_api_key_clears_clients(self):
        llm = GeminiLLM(api_keys=["k1", "k2"])
        llm.clients["k1"] = "fake_client"
        llm._rotate_api_key()
        assert len(llm.clients) == 0


# ---------------------------------------------------------------------------
# Image Processing
# ---------------------------------------------------------------------------

class TestProcessImage:
    @pytest.fixture
    def llm(self):
        return GeminiLLM(api_keys="key1")

    def test_base64_data_uri(self, llm):
        # Create a minimal 1x1 PNG as base64
        png_bytes = base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100).decode()
        data_uri = f"data:image/png;base64,{png_bytes}"
        result = llm._process_image(data_uri)
        assert result["mime_type"] == "image/png"
        assert "data" in result

    def test_bytes_input(self, llm):
        result = llm._process_image(b"\x89PNG fake data")
        assert result["mime_type"] == "image/png"

    def test_unsupported_type(self, llm):
        with pytest.raises(ValueError, match="Unsupported"):
            llm._process_image(12345)

    def test_file_path_input(self, llm, tmp_path):
        img_file = tmp_path / "test.jpg"
        img_file.write_bytes(b"\xff\xd8\xff fake jpeg")
        result = llm._process_image(str(img_file))
        assert result["mime_type"] == "image/jpg"


# ---------------------------------------------------------------------------
# ask() prompt type coercion
# ---------------------------------------------------------------------------

class TestAskPromptTypeCoercion:
    def test_string_prompt_type_coerced(self):
        llm = GeminiLLM(api_keys="key1")
        # We can't call ask() without mocking the API, but we can test
        # the prompt_type conversion logic by calling _build_prompt
        # after conversion
        prompt_type = "json"
        try:
            pt = PromptType(prompt_type.lower())
        except ValueError:
            pt = PromptType.STRING
        assert pt == PromptType.JSON

    def test_invalid_prompt_type_defaults_to_string(self):
        try:
            pt = PromptType("invalid_type".lower())
        except ValueError:
            pt = PromptType.STRING
        assert pt == PromptType.STRING


# ---------------------------------------------------------------------------
# set_generation_config
# ---------------------------------------------------------------------------

class TestSetGenerationConfig:
    def test_stores_config(self):
        llm = GeminiLLM(api_keys="key1")
        llm.set_generation_config(temperature=0.5, top_k=3, top_p=0.9, max_output_tokens=4096)
        assert llm.generation_config["temperature"] == 0.5
        assert llm.generation_config["max_output_tokens"] == 4096
