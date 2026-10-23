import json
import unittest
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient
from openai import OpenAI

from wordlearn.api import app
from wordlearn.generator import build_client_and_model


class GenerationTests(unittest.TestCase):
    def test_cet_rejects_tfng_before_model_calls(self):
        with patch("wordlearn.api.generate_passage") as generate:
            for exam in ("CET4", "CET6"):
                response = TestClient(app).post("/generate", json={"provider": "ollama", "exam": exam, "question_type": "tfng"})
                self.assertEqual(response.status_code, 400)
            generate.assert_not_called()

    def test_ielts_keeps_tfng(self):
        from wordlearn.question_generator import validate_exam_question_type
        self.assertEqual(validate_exam_question_type("IELTS", "tfng"), "tfng")

    def test_client_has_bounded_timeout_and_no_network_retries(self):
        client, _, _ = build_client_and_model(None, {"provider": "deepseek", "api_key": "test"})
        try:
            self.assertEqual(client.timeout.read, 60)
            self.assertEqual(client.max_retries, 0)
        finally:
            client.close()

    def run_request(self, handler):
        def build(*args):
            return OpenAI(api_key="test", max_retries=0, http_client=httpx.Client(transport=httpx.MockTransport(handler))), "deepseek-flash", 0.7
        with patch("wordlearn.generator.build_client_and_model", side_effect=build), patch("wordlearn.question_generator.build_client_and_model", side_effect=build), patch("wordlearn.api.load_words", return_value=["nature"]):
            return TestClient(app).post("/generate", json={"provider": "deepseek", "api_key": "test", "exam": "CET6", "model": "deepseek-flash"})

    def test_generation_uses_fast_json_mode_for_both_calls(self):
        calls = []
        def handler(request):
            body = json.loads(request.content)
            calls.append(body)
            self.assertEqual(body["thinking"], {"type": "disabled"})
            self.assertEqual(body["response_format"], {"type": "json_object"})
            payload = {"title": "Nature", "paragraphs": ["Nature is important. " * 25] * 5} if len(calls) == 1 else {"careful_reading": [{"question": "Why?", "options": {"A": "a", "B": "b", "C": "c", "D": "d"}, "answer": "A"}]}
            return httpx.Response(200, json={"id": "test", "object": "chat.completion", "created": 0, "model": "deepseek-flash", "choices": [{"index": 0, "message": {"role": "assistant", "content": json.dumps(payload)}, "finish_reason": "stop"}]})
        response = self.run_request(handler)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(len(calls), 2)
        self.assertEqual(response.json()["source"], "model")

    def test_timeout_is_reported_without_retrying_or_exposing_key(self):
        calls = []
        def handler(request):
            calls.append(request)
            raise httpx.ReadTimeout("test-secret", request=request)
        response = self.run_request(handler)
        self.assertEqual(response.status_code, 504)
        self.assertIn("生成文章", response.json()["detail"])
        self.assertNotIn("test-secret", response.text)
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
