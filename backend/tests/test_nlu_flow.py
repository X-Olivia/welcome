import unittest
from unittest.mock import patch

from app.models.schemas import Intent
from app.services import nlu
from app.services.nlu import _LLMGuideParse


class NLUFallbackTests(unittest.TestCase):
    def test_single_place_route_cn(self) -> None:
        result = nlu._fallback_nlu("图书馆怎么走？")
        self.assertEqual(result.intent, Intent.route)
        self.assertEqual(result.ordered_waypoints, ["library"])

    def test_single_place_route_en(self) -> None:
        result = nlu._fallback_nlu("Where is PMB?")
        self.assertEqual(result.intent, Intent.route)
        self.assertEqual(result.ordered_waypoints, ["pmb"])

    def test_theme_tour(self) -> None:
        result = nlu._fallback_nlu("我想了解理工区域")
        self.assertEqual(result.intent, Intent.tour)
        self.assertEqual(result.ordered_waypoints, ["pmb", "yang_fujia", "ieb"])

    def test_multi_place_order_preserved(self) -> None:
        result = nlu._fallback_nlu("我想先去图书馆，再去 PMB")
        self.assertEqual(result.intent, Intent.tour)
        self.assertEqual(result.ordered_waypoints, ["library", "pmb"])

    def test_recommend_tour(self) -> None:
        result = nlu._fallback_nlu("第一次来，帮我推荐一下路线")
        self.assertEqual(result.intent, Intent.recommend_tour)
        self.assertGreaterEqual(len(result.ordered_waypoints), 2)

    def test_clarification(self) -> None:
        result = nlu._fallback_nlu("带我去那个楼")
        self.assertEqual(result.intent, Intent.clarification)
        self.assertTrue(result.needs_clarification)

    def test_unknown_place_needs_clarification(self) -> None:
        raw = _LLMGuideParse(
            intent="route",
            places=["moon building"],
            ordered_waypoints=["moon building"],
            themes=[],
            reply_text="",
            confidence=0.8,
            needs_clarification=False,
            clarification_question=None,
        )
        result = nlu._normalize_llm_output(raw, "我想去 moon building")
        self.assertEqual(result.intent, Intent.clarification)
        self.assertTrue(result.needs_clarification)

    def test_llm_multi_stop_tour_normalization(self) -> None:
        raw = _LLMGuideParse(
            intent="tour",
            places=["PMB", "YANG Fujia Building", "IEB"],
            ordered_waypoints=["PMB", "YANG Fujia Building", "IEB"],
            themes=["engineering"],
            reply_text="我为你安排一条理工导览路线。",
            confidence=0.93,
            needs_clarification=False,
            clarification_question=None,
        )
        result = nlu._normalize_llm_output(raw, "我想看看工科相关的地方")
        self.assertEqual(result.intent, Intent.tour)
        self.assertEqual(result.ordered_waypoints, ["pmb", "yang_fujia", "ieb"])


class NLUEntryTests(unittest.TestCase):
    @patch("app.services.nlu._run_llm_parse")
    @patch("app.services.nlu.settings")
    def test_run_nlu_prefers_llm_when_key_exists(self, mock_settings, mock_llm) -> None:
        mock_settings.openai_api_key = "test-key"
        mock_settings.openai_model = "gpt-4.1-mini"
        mock_llm.return_value = _LLMGuideParse(
            intent="route",
            places=["Library"],
            ordered_waypoints=["Library"],
            themes=[],
            reply_text="我已经找到图书馆。",
            confidence=0.95,
            needs_clarification=False,
            clarification_question=None,
        )

        result = nlu.run_nlu("图书馆怎么走")
        self.assertEqual(result.intent, Intent.route)
        self.assertEqual(result.ordered_waypoints, ["library"])


if __name__ == "__main__":
    unittest.main()
