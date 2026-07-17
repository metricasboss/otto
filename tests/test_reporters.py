import json

from otto.engine.reporters import get_renderer
from otto.engine.scanner import Finding
from otto.engine.scorer import compute_score

FINDING = Finding(
    rule_id="cpf_exposure", regulation="lgpd", severity="critical",
    category="sensitive_data", article="LGPD Art. 46 (Dados Sensíveis)",
    message="CPF brasileiro exposto no código", fix="Remova o CPF hardcoded.",
    fine="Até R$ 50 milhões", file_path="src/app.js", line=7,
    matched_text="529.982.247-25",
)
SCORE = compute_score([FINDING])


def test_text_contains_score_article_and_fix():
    out = get_renderer("text")([FINDING], SCORE, "lgpd")
    assert "59/100" in out
    assert "LGPD Art. 46" in out
    assert "Remova o CPF hardcoded." in out
    assert "src/app.js" in out


def test_text_clean_scan():
    clean = compute_score([])
    out = get_renderer("text")([], clean, "both")
    assert "100/100" in out
    assert "No violations" in out


def test_json_structure():
    data = json.loads(get_renderer("json")([FINDING], SCORE, "lgpd"))
    assert data["score"] == 59
    assert data["counts"]["critical"] == 1
    assert data["findings"][0]["rule_id"] == "cpf_exposure"
    assert data["findings"][0]["line"] == 7
    assert data["per_file"]["src/app.js"] == 59


def test_sarif_is_valid_2_1_0():
    doc = json.loads(get_renderer("sarif")([FINDING], SCORE, "lgpd"))
    assert doc["version"] == "2.1.0"
    run = doc["runs"][0]
    assert run["tool"]["driver"]["name"] == "OTTO"
    result = run["results"][0]
    assert result["ruleId"] == "cpf_exposure"
    assert result["level"] == "error"
    loc = result["locations"][0]["physicalLocation"]
    assert loc["artifactLocation"]["uri"] == "src/app.js"
    assert loc["region"]["startLine"] == 7
    rule_ids = [r["id"] for r in run["tool"]["driver"]["rules"]]
    assert "cpf_exposure" in rule_ids


def test_unknown_format_raises():
    import pytest
    with pytest.raises(ValueError):
        get_renderer("xml")
