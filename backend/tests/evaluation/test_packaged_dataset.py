from importlib.resources import files


def test_fixed_evaluation_dataset_is_packaged_with_backend() -> None:
    dataset = files("xiaodianji.evaluation").joinpath("cases.jsonl")

    assert dataset.is_file()
    assert len(dataset.read_text(encoding="utf-8").splitlines()) == 20
