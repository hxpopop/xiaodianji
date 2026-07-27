import json
from pathlib import Path


DATASET = Path(__file__).resolve().parents[3] / "evaluation" / "cases.jsonl"
REQUIRED_TAGS = {
    "single_product", "multi_product", "unpaid", "paid", "payment", "quote",
    "customer_alias", "product_spec", "date_omitted", "low_confidence",
    "ambiguous_customer", "provider_failure",
}


def test_fixed_dataset_is_valid_desensitized_and_covers_required_cases() -> None:
    cases = [json.loads(line) for line in DATASET.read_text(encoding="utf-8").splitlines() if line]

    assert len(cases) >= 20
    assert len({case["stable_key"] for case in cases}) == len(cases)
    assert REQUIRED_TAGS <= {tag for case in cases for tag in case["tags"]}
    for case in cases:
        assert set(case) == {"stable_key", "input_type", "input", "expected", "tags"}
        assert case["input_type"] == "text"
        assert case["input"]["text"].strip()
        assert case["expected"]["customer_name"]
        assert "138" not in json.dumps(case, ensure_ascii=False)
