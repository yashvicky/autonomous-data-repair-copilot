"""Compare explicit detector findings with a complete, labeled evaluation scope."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class Finding:
    """One exact finding, identified by kind, column and zero-based row positions."""

    kind: str
    column: str | None
    row_indices: tuple[int, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.kind, str) or not self.kind.strip():
            raise ValueError("kind must be a non-empty string")
        if self.column is not None and (
            not isinstance(self.column, str) or not self.column.strip()
        ):
            raise ValueError("column must be None or a non-empty string")
        if not isinstance(self.row_indices, tuple) or not self.row_indices:
            raise ValueError("row_indices must be a non-empty tuple")
        if any(type(i) is not int or i < 0 for i in self.row_indices):
            raise ValueError("row indices must be non-negative integers")
        if len(set(self.row_indices)) != len(self.row_indices):
            raise ValueError("row indices must be unique")
        object.__setattr__(self, "row_indices", tuple(sorted(self.row_indices)))


@dataclass(frozen=True)
class DetectorMetrics:
    true_positives: int
    false_positives: int
    false_negatives: int
    precision: float | None
    recall: float | None


def evaluate_detectors(
    predicted: Mapping[str, Sequence[Finding]],
    ground_truth: Mapping[str, Sequence[Finding]],
) -> dict[str, DetectorMetrics]:
    """Evaluate exact findings per detector; undefined ratios are None.

    Both mappings must name the same detectors, including any with zero findings.
    Ground truth must be complete for the selected scope to interpret the result.
    A duplicate group is one finding, and all its row indices must match exactly.
    """
    if any(not isinstance(k, str) or not k.strip() for k in (*predicted, *ground_truth)):
        raise ValueError("detector names must be non-empty strings")
    if predicted.keys() != ground_truth.keys():
        raise ValueError("predicted and ground truth detector names must match")
    results = {}
    for detector in predicted:
        groups = []
        for findings in (predicted[detector], ground_truth[detector]):
            if any(not isinstance(finding, Finding) for finding in findings):
                raise ValueError("all findings must be Finding instances")
            unique = set(findings)
            if len(unique) != len(findings):
                raise ValueError("duplicate findings are not allowed")
            groups.append(unique)
        actual, expected = groups
        tp = len(actual & expected)
        fp = len(actual - expected)
        fn = len(expected - actual)
        results[detector] = DetectorMetrics(
            true_positives=tp,
            false_positives=fp,
            false_negatives=fn,
            precision=tp / (tp + fp) if tp + fp else None,
            recall=tp / (tp + fn) if tp + fn else None,
        )
    return results
