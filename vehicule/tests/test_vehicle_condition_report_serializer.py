from django.test import SimpleTestCase
from rest_framework import serializers
from vehicule.serializers import VehicleConditionReportSerializer


class VehicleConditionReportSerializerTest(SimpleTestCase):
    def test_validate_points_normalizes_missing_level(self):
        serializer = VehicleConditionReportSerializer()

        points = [
            {
                "id": "point-1",
                "view": "left",
                "x": 25,
                "y": 75,
                "description": "Rayure portière",
            }
        ]

        normalized = serializer.validate_points(points)

        self.assertEqual(normalized[0]["level"], "léger")
        self.assertEqual(normalized[0]["view"], "left")
        self.assertEqual(normalized[0]["x"], 25.0)
        self.assertEqual(normalized[0]["y"], 75.0)

    def test_validate_points_rejects_invalid_level(self):
        serializer = VehicleConditionReportSerializer()

        points = [
            {
                "id": "point-1",
                "view": "left",
                "x": 25,
                "y": 75,
                "level": "critique",
                "description": "Rayure portière",
            }
        ]

        with self.assertRaisesMessage(serializers.ValidationError, "niveau invalide"):
            serializer.validate_points(points)
