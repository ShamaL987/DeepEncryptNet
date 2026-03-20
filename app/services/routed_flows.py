from datetime import timezone, datetime


def normalize_dt(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def compute_risk_status(
    max_p: float,
    entropy: float,
    margin: float,
) -> str:
    if max_p < 0.40 or entropy > 1.00 or margin < 0.10:
        return "High Risk"

    if max_p < 0.60 or entropy > 0.70 or margin < 0.20:
        return "Medium Risk"

    return "Low Risk"