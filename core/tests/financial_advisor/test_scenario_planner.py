from core.services.shared.auth_workflow_service import AuthWorkflowService
import json
from datetime import date
from django.contrib.auth import get_user_model
from django.test import TestCase
from core.models import Scenario, ScenarioEvent

User = get_user_model()


class ScenarioPlannerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="scenario_user",
            email="scenario@example.com",
            password="Password123!",
            is_active=True,
        )
        profile = AuthWorkflowService.get_profile(self.user)
        profile.email_verified = True
        profile.account_status = "active"
        profile.save()

    def test_scenario_model_crud(self):
        sc = Scenario.objects.create(
            name="Plan A",
            description="Buy home and marry",
            is_baseline_pinned=False,
        )
        self.assertEqual(sc.name, "Plan A")
        self.assertFalse(sc.is_baseline_pinned)

        ev = ScenarioEvent.objects.create(
            scenario=sc,
            event_type="house",
            event_date=date(2027, 1, 1),
            params={"purchase_price": 4200000, "down_payment": 1000000},
            order=1,
        )
        self.assertEqual(ev.scenario_id, sc.id)
        d = sc.to_dict()
        self.assertEqual(d["name"], "Plan A")
        self.assertEqual(len(d["events"]), 1)
        self.assertEqual(d["events"][0]["event_type"], "house")

    def test_scenario_service_payload_and_overrides(self):
        from core.services.financial_advisor.scenario_planner_service import ScenarioPlannerService
        svc = ScenarioPlannerService(today=date(2026, 8, 1))

        # Test empty scenario list comparison
        payload = svc.payload(scenario_ids=[])
        self.assertIn("baseline", payload)
        self.assertIn("scenarios", payload)
        self.assertIn("config", payload)
        self.assertEqual(len(payload["scenarios"]), 0)

        # Test with actual scenario
        sc = Scenario.objects.create(name="Apartment Purchase", description="House event")
        ScenarioEvent.objects.create(
            scenario=sc,
            event_type="house",
            event_date=date(2027, 1, 1),
            params={"down_payment": 500000, "monthly_installment": 15000, "purchase_price": 2000000},
        )

        payload2 = svc.payload(scenario_ids=[sc.id])
        self.assertEqual(len(payload2["scenarios"]), 1)
        sc_res = payload2["scenarios"][0]
        self.assertEqual(sc_res["id"], sc.id)
        self.assertIn("retirement_readiness", sc_res)
        self.assertIn("readiness_pct", sc_res["retirement_readiness"])
        self.assertIn("insights", sc_res)

    def test_event_definitions_endpoint(self):
        self.client.login(username="scenario_user", password="Password123!")
        response = self.client.get("/api/scenarios/event-definitions/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("event_schema", data)
        self.assertTrue(len(data["event_schema"]) >= 10)

    def test_scenario_views_crud_and_compare(self):
        self.client.login(username="scenario_user", password="Password123!")

        # List (empty initially)
        resp = self.client.get("/api/scenarios/")
        self.assertEqual(resp.status_code, 200)

        # Create scenario
        create_resp = self.client.post(
            "/api/scenarios/",
            json.dumps({"name": "Test Scenario", "description": "Desc"}),
            content_type="application/json",
        )
        self.assertEqual(create_resp.status_code, 201)
        sc_id = create_resp.json()["id"]

        # Add event to scenario
        ev_resp = self.client.post(
            f"/api/scenarios/{sc_id}/events/",
            json.dumps({
                "event_type": "marriage",
                "event_date": "2027-06-01",
                "params": {"one_time_cost": 300000, "new_monthly_expense": 3000},
            }),
            content_type="application/json",
        )
        self.assertEqual(ev_resp.status_code, 201)

        # Compare endpoint
        cmp_resp = self.client.get(f"/api/financial-advisor/scenario-planner/compare/?scenario_ids={sc_id}")
        self.assertEqual(cmp_resp.status_code, 200)
        cmp_data = cmp_resp.json()
        self.assertIn("baseline", cmp_data)
        self.assertEqual(len(cmp_data["scenarios"]), 1)
