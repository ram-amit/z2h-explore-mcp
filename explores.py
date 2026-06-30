"""Z2H campaign-explore registry (from mf-campaign-explore v155 bundle)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExploreRef:
    explore_name: str
    label: str
    lkml_path: str
    model_path: str
    date_column: str = "CREATED_AT"
    schema_views: tuple[str, ...] = ("cm",)


EXPLORES: dict[str, ExploreRef] = {
    "campaign_monitoring": ExploreRef(
        explore_name="campaign_monitoring",
        label="Campaign Monitoring",
        lkml_path="marketing/views/campaign_monitoring_snowflake.view.lkml",
        model_path="marketing/models/marketing_sf.model.lkml",
        date_column="CREATED_AT",
        schema_views=("cm", "leads", "acct"),
    ),
    "advanced_analytics": ExploreRef(
        explore_name="advanced_analytics",
        label="Advanced Analytics",
        lkml_path="marketing/views/advanced_analytics_snowflake.view.lkml",
        model_path="marketing/models/marketing.model.lkml",
        date_column="DAY",
        schema_views=(),
    ),
    "linkedin_habu": ExploreRef(
        explore_name="linkedin_habu",
        label="LinkedIn Habu",
        lkml_path="marketing/views/Linkedin_Habu.view.lkml",
        model_path="marketing/models/marketing_sf.model.lkml",
        date_column="DAY",
        schema_views=(),
    ),
}

# Parameters not fully represented in the bundled CM schema chunk.
EXPLORE_PARAMETERS: dict[str, list[dict]] = {
    "campaign_monitoring": [
        {"name": "ATTRIBUTION_MODEL", "label": "attribution_model", "default": "BigBrainTouchV8"},
        {"name": "DATE_GRANULARITY", "label": "date_granularity", "default": "Day"},
        {"name": "DYNAMIC_DIMENSION_TYPE", "label": "dynamic_dimension_type", "default": "Source"},
        {"name": "LEAD_LOCK", "label": "lead_lock", "default": "1 Day"},
        {"name": "PAID_LOCK", "label": "paid_lock", "default": "60 Days"},
        {"name": "SIGNUP_LOCK", "label": "signup_lock", "default": "Unlocked"},
        {"name": "PRODUCT_INSTALLATION_LOCK", "label": "product_installation_lock", "default": "1 Days"},
        {"name": "PIPELINE_CONVERSION_FACTOR", "label": "pipeline_conversion_factor", "default": ""},
        {"name": "TOUCH_POINT_TO_VISIT_LOCK_DAYS", "label": "touch_point_to_visit_lock_days", "default": ""},
        {"name": "DYNAMIC_PERIOD_LENGTH", "label": "dynamic_period_length", "default": "12"},
    ],
    "advanced_analytics": [
        {"name": "SIGNUP_LOCK", "label": "signup_lock", "default": ""},
        {"name": "REPORT_GRANULARITY", "label": "report_granularity", "default": ""},
        {"name": "LOCALIZATION_COUNTRIES", "label": "localization_countries", "default": ""},
        {"name": "DYNAMIC_PERIOD_LENGTH", "label": "dynamic_period_length", "default": ""},
    ],
    "linkedin_habu": [],
}

Z2H_APP_BASE = "https://bigbrain.me/bigbrain-vibe/campaign-explore"
