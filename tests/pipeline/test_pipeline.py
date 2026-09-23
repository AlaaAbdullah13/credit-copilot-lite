from src.application.pipeline import run_assessment


def test_pipeline_with_fake_llm():
    application = {
        "id": "app-1",
        "requested_amount": 100000,
        "annual_rate": 12.5,
        "tenure_months": 36,
        "monthly_income": 15000,
    }
    policy = {"edition": "v1"}
    memo = run_assessment(application, policy)
    assert memo.application_id == "app-1"
    assert "emi" in memo.calculations
