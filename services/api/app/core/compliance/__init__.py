"""Scotch compliance engine — Phase 27 (NBC) + Phase 32 (TN advisory)."""

from app.core.compliance.engine import run_compliance
from app.core.compliance.models import (
    ComplianceReport,
    RuleResult,
    TNAdvisoryReport,
    TNRuleResult,
)
from app.core.compliance.rules import (
    DEFAULT_FRONT_SETBACK,
    DEFAULT_MAX_FSI,
    DEFAULT_REAR_SETBACK,
    DEFAULT_SIDE_SETBACK,
)
from app.core.compliance.tamil_nadu import run_tn_advisory

__all__ = [
    "run_compliance",
    "ComplianceReport",
    "RuleResult",
    "DEFAULT_FRONT_SETBACK",
    "DEFAULT_SIDE_SETBACK",
    "DEFAULT_REAR_SETBACK",
    "DEFAULT_MAX_FSI",
    # Phase 32
    "run_tn_advisory",
    "TNAdvisoryReport",
    "TNRuleResult",
]
