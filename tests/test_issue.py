import pytest
from pydantic import ValidationError

from data_repair_copilot.models.issue import Issue


def valid_issue() -> dict:
    return {
        "issue_type": "missing_value",
        "severity": "medium",
        "evidence": ["Empty value in column age"],
        "affected_rows": [0, 3],
        "recommendation": "Review the missing value with the data owner.",
    }


def test_issue_round_trip() -> None:
    issue = Issue.model_validate(valid_issue())
    assert issue.issue_type == "missing_value"
    assert issue.severity == "medium"
    assert issue.evidence == ["Empty value in column age"]
    assert issue.affected_rows == [0, 3]
    assert issue.recommendation.startswith("Review")
    assert Issue.model_validate_json(issue.model_dump_json()) == issue


def test_invalid_issues() -> None:
    for key in valid_issue():
        data = valid_issue()
        del data[key]
        with pytest.raises(ValidationError):
            Issue.model_validate(data)
    for key, value in [
        ("issue_type", "  "),
        ("severity", "urgent"),
        ("evidence", []),
        ("evidence", [" "]),
        ("recommendation", "\t"),
        ("unknown", "ignored?"),
    ]:
        with pytest.raises(ValidationError):
            Issue.model_validate({**valid_issue(), key: value})


def test_row_indices() -> None:
    assert Issue.model_validate({**valid_issue(), "affected_rows": []}).affected_rows == []
    for invalid in [[-1], [True], [1, 1], ["1"], [1.0]]:
        with pytest.raises(ValidationError):
            Issue.model_validate({**valid_issue(), "affected_rows": invalid})
