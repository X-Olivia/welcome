import math
import unittest

from app.models.schemas import MapPoint
from app.services.route_arm_direction import EIGHT_DIRECTION_KEYS, polyline_to_action_key


class TestPolylineToActionKey(unittest.TestCase):
    def test_empty_polyline(self) -> None:
        self.assertIsNone(polyline_to_action_key([]))
        self.assertIsNone(polyline_to_action_key([MapPoint(x=0, y=0)]))

    def test_north_up_decreasing_y(self) -> None:
        # 北：向上，dy 为负
        poly = [MapPoint(x=0, y=100), MapPoint(x=0, y=50)]
        self.assertEqual(polyline_to_action_key(poly, min_segment_px=1.0), "point_north")

    def test_east_increasing_x(self) -> None:
        poly = [MapPoint(x=0, y=0), MapPoint(x=50, y=0)]
        self.assertEqual(polyline_to_action_key(poly, min_segment_px=1.0), "point_east")

    def test_south_increasing_y(self) -> None:
        poly = [MapPoint(x=0, y=0), MapPoint(x=0, y=50)]
        self.assertEqual(polyline_to_action_key(poly, min_segment_px=1.0), "point_south")

    def test_west_decreasing_x(self) -> None:
        poly = [MapPoint(x=50, y=0), MapPoint(x=0, y=0)]
        self.assertEqual(polyline_to_action_key(poly, min_segment_px=1.0), "point_west")

    def test_short_segment_skipped(self) -> None:
        poly = [MapPoint(x=0, y=0), MapPoint(x=1, y=0), MapPoint(x=100, y=0)]
        # 第一段 < 3px，应跳过用第二段
        self.assertEqual(polyline_to_action_key(poly, min_segment_px=3.0), "point_east")

    def test_north_offset(self) -> None:
        poly = [MapPoint(x=0, y=100), MapPoint(x=0, y=50)]  # north
        # 旋转 +90° 后原「北」应落在「东」扇区
        key = polyline_to_action_key(poly, min_segment_px=1.0, north_offset_deg=90.0)
        self.assertEqual(key, "point_east")

    def test_eight_keys_distinct(self) -> None:
        self.assertEqual(len(EIGHT_DIRECTION_KEYS), 8)
        self.assertEqual(len(set(EIGHT_DIRECTION_KEYS)), 8)

    def test_northeast_quadrant(self) -> None:
        # 45° from north: equal dx and -dy
        d = 40
        poly = [MapPoint(x=0, y=0), MapPoint(x=d, y=-d)]
        key = polyline_to_action_key(poly, min_segment_px=1.0)
        self.assertEqual(key, "point_northeast")
        # sanity: atan2(dx,-dy) = atan2(d,d)=45°
        self.assertAlmostEqual(math.degrees(math.atan2(d, -(-d))), 45.0)


if __name__ == "__main__":
    unittest.main()
