from __future__ import annotations

from rent_pulse.config import RentPulseConfig


def trigger_dbt_cloud_job(config: RentPulseConfig | None = None) -> dict:
    active_config = config or RentPulseConfig.from_env()
    active_config.require("dbt_cloud_account_id", "dbt_cloud_job_id", "dbt_cloud_api_token")

    import requests

    url = (
        "https://cloud.getdbt.com/api/v2/accounts/"
        f"{active_config.dbt_cloud_account_id}/jobs/{active_config.dbt_cloud_job_id}/run/"
    )
    response = requests.post(
        url,
        headers={"Authorization": f"Token {active_config.dbt_cloud_api_token}"},
        json={"cause": "RentPulse Airflow orchestration"},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()
