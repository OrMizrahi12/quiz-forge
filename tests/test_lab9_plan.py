"""Lab 9, FR-2: the blueprint drives the plan. No API calls. The imports sit inside the tests, so a project without
quizforge/plan.py fails each test with the reason instead of failing to collect."""

import importlib
import json
import tomllib

import pytest

from quizforge.config import CODE, ROOT, load_config


def plan_module():
    try:
        return importlib.import_module("quizforge.plan")
    except ModuleNotFoundError:
        pytest.fail("quizforge/plan.py is missing (Lab 9, step 1)")


def write(tmp_path, text, lessons=("A1", "A2", "B1", "C1")):
    (tmp_path / "MANIFEST.json").write_text(json.dumps({"lessons": [{"lesson": lesson} for lesson in lessons]}))
    (tmp_path / "blueprint.toml").write_text(text)
    return tmp_path / "blueprint.toml"


THREE = """
[[domain]]
name = "Alpha"
weight = 50
lessons = ["A1", "A2"]

[[domain]]
name = "Beta"
weight = 30
lessons = ["B1"]

[[domain]]
name = "Gamma"
weight = 20
"""


def test_largest_remainder_sums_to_n():
    split = plan_module().split
    for n in range(1, 40):
        counts = split([21, 14, 12, 12], n)
        assert sum(counts) == n
        assert all(abs(c - n * w / 59) < 1 for c, w in zip(counts, [21, 14, 12, 12]))


def test_counts_follow_the_weights_over_the_covered_domains(tmp_path):
    plan = plan_module()
    rows, gaps = plan.plan(plan.load(write(tmp_path, THREE), tmp_path), 8)
    per_domain = {}
    for domain, _, k in rows:
        per_domain[domain] = per_domain.get(domain, 0) + k
    assert per_domain == {"Alpha": 5, "Beta": 3}  # 8 x 50/80 and 8 x 30/80
    assert gaps == [("Gamma", 20.0)]
    assert [(lesson, k) for domain, lesson, k in rows if domain == "Alpha"] == [("A1", 3), ("A2", 2)]


def test_the_plan_is_reproducible(tmp_path):
    plan = plan_module()
    domains = plan.load(write(tmp_path, THREE), tmp_path)
    assert plan.plan(domains, 11) == plan.plan(domains, 11)


@pytest.mark.parametrize(
    "text, reason",
    [
        (THREE.replace("weight = 20", "weight = 25"), "add up to 105"),
        (THREE.replace('["B1"]', '["B1", "A1"]'), "A1 is in two domains"),
        (THREE.replace('["B1"]', '["B9"]'), "not in the library: B9"),
    ],
)
def test_a_bad_blueprint_is_refused_with_its_reason(tmp_path, text, reason):
    plan = plan_module()
    with pytest.raises(plan.BlueprintError, match=reason):
        plan.load(write(tmp_path, text), tmp_path)


def test_fewer_items_than_covered_domains_is_refused(tmp_path):
    plan = plan_module()
    with pytest.raises(plan.BlueprintError, match="fewer than the 2 domains"):
        plan.plan(plan.load(write(tmp_path, THREE), tmp_path), 1)


def test_the_course_blueprint_matches_the_library():
    plan = plan_module()
    domains = plan.load(ROOT / "blueprint.toml", load_config().library)
    assert sum(weight for _, weight, _ in domains) == 100
    rows, _ = plan.plan(domains, 20)
    assert sum(k for _, _, k in rows) == 20


def test_qf_plan_prints_the_table(capsys):
    plan_module()
    from quizforge import cli

    assert cli.main(["plan", "--n", "6"]) in (0, None)
    lines = capsys.readouterr().out.splitlines()
    total = next(line for line in lines if line.startswith("total"))
    assert total.split()[-1] == "6" and lines[-1].startswith("not covered by this library")


def test_qf_init_writes_a_blueprint(tmp_path):
    plan = plan_module()
    from quizforge.init import init

    folder = tmp_path / "bakery"
    init(folder, CODE / "examples/sample-library/v1", "bakery", "home bakers learning to make bread")
    domains = plan.load(folder / "blueprint.toml", folder / "library")
    assert [lesson for _, _, lessons in domains for lesson in lessons] == ["B1.1", "B1.2", "B1.3"]
    assert tomllib.loads((folder / "blueprint.toml").read_text())["domain"][0]["weight"] == 100
