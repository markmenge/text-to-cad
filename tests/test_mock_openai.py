# Suggested filename: test_mock_openai.py

import json
import unittest
from pathlib import Path

from llm_client import LLMRequest, MockOpenAIClient

# pip install instructions:
# No third-party packages required.


ROOT = Path(__file__).resolve().parents[1]


class MockOpenAITests(unittest.TestCase):
    def setUp(self):
        self.client = MockOpenAIClient(ROOT / "mocks" / "mock_openai.json")

    def test_planner_uses_prompt_context(self):
        r = self.client.generate(LLMRequest("planner", "Generate a bishop chess piece.", {}))
        self.assertEqual(r.fixture_id, "plan_bishop")
        self.assertEqual(json.loads(r.text)["object_type"], "bishop")

    def test_f16_repair_selected_by_feedback(self):
        req1 = LLMRequest("generator", "Generate a F-16 model.", {
            "object_type":"f16", "iteration":1, "feedback":[], "strategies":["hull_loft"]
        })
        req2 = LLMRequest("generator", "Generate a F-16 model.", {
            "object_type":"f16", "iteration":2,
            "feedback":["connected components=3"], "strategies":["hull_loft"]
        })
        self.assertEqual(self.client.generate(req1).fixture_id, "gen_f16_bad")
        self.assertEqual(self.client.generate(req2).fixture_id, "gen_f16_repair")

    def test_frog_repair_selected_by_semantic_feedback(self):
        req = LLMRequest("generator", "Generate a tea cup with a frog in it.", {
            "object_type":"frog_teacup", "iteration":2,
            "feedback":["Wall is too thin: 0.8 mm"], "strategies":["shell"]
        })
        self.assertEqual(self.client.generate(req).fixture_id, "gen_frog_teacup_repair")


if __name__ == "__main__":
    unittest.main()

class PromptAssemblyTests(unittest.TestCase):
    def setUp(self):
        self.client = MockOpenAIClient(ROOT / "mocks" / "mock_openai.json", ROOT / "prompts")

    def test_common_and_stage_prompts_are_assembled(self):
        req = LLMRequest("planner", "Generate a bishop chess piece.", {})
        self.client.generate(req)
        assembled = self.client.last_assembled_prompt
        self.assertIn("# Text-to-CAD Common Context", assembled)
        self.assertIn("# Planner Stage", assembled)
        self.assertIn("Generate a bishop chess piece.", assembled)

    def test_each_role_uses_its_own_stage_file(self):
        for role, heading in (("planner", "# Planner Stage"), ("generator", "# Generator Stage"), ("critic", "# Critic Stage")):
            context = {"object_type":"cube", "iteration":1, "feedback":[], "strategies":["primitive_csg"]}
            self.client.generate(LLMRequest(role, "Generate a 2 cm by 2 cm by 2 cm cube.", context))
            self.assertIn(heading, self.client.last_assembled_prompt)
