import unittest

from app.config import settings
from app.models.schemas import Intent
from app.services.decision import run_guide_pipeline
from app.services.nlu import run_nlu


class NLUFallbackTests(unittest.TestCase):
    def setUp(self) -> None:
        self.old_key = settings.openai_api_key
        settings.openai_api_key = ""

    def tearDown(self) -> None:
        settings.openai_api_key = self.old_key

    def test_single_place_route_cn(self) -> None:
        result = run_nlu("图书馆怎么走？")
        self.assertEqual(result.intent, Intent.route)
        self.assertEqual(result.ordered_waypoints, ["library"])

    def test_single_place_route_en(self) -> None:
        result = run_nlu("Where is the library?")
        self.assertEqual(result.intent, Intent.route)
        self.assertEqual(result.ordered_waypoints, ["library"])

    def test_theme_tour_ai_robotics(self) -> None:
        result = run_nlu("我对 AI 和机器人比较感兴趣")
        self.assertEqual(result.intent, Intent.tour)
        self.assertEqual(result.ordered_waypoints, ["pmb", "nicc", "ieb"])

    def test_multi_place_tour(self) -> None:
        result = run_nlu("我想先去图书馆再去食堂")
        self.assertEqual(result.intent, Intent.tour)
        self.assertEqual(result.ordered_waypoints, ["library", "student_canteen"])

    def test_recommend_tour(self) -> None:
        result = run_nlu("第一次来，怎么逛比较好？")
        self.assertEqual(result.intent, Intent.recommend_tour)
        self.assertGreaterEqual(len(result.ordered_waypoints), 3)

    def test_clarification_for_ambiguous_request(self) -> None:
        result = run_nlu("我想去那个楼")
        self.assertEqual(result.intent, Intent.clarification)
        self.assertTrue(result.needs_clarification)

    def test_unknown_place_goes_to_clarification(self) -> None:
        result = run_nlu("我想去体育馆")
        self.assertEqual(result.intent, Intent.clarification)
        self.assertTrue(result.needs_clarification)

    def test_pipeline_returns_real_route(self) -> None:
        result = run_guide_pipeline("我想了解理工区域")
        self.assertEqual(result.intent, Intent.tour)
        self.assertGreater(len(result.places), 0)
        self.assertGreater(len(result.route_polyline), 0)
        self.assertIsNotNone(result.route_distance_px)


if __name__ == "__main__":
    unittest.main()
