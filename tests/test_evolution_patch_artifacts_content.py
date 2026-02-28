from pathlib import Path

from app.evolution.schemas import EvolutionProposal, EvolutionProposalChange, EvolutionRiskAssessment
from app.evolution.patch_artifacts import render_patch_artifacts


def test_render_patch_artifacts_writes_real_unified_diff(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    target = Path("app/sample.py")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("print(\"hello\")\n", encoding="utf-8")

    proposal = EvolutionProposal(
        proposal_id="prop_test",
        created_at="2026-02-27T00:00:00Z",
        source_subject="Sample",
        title="Improve sample",
        summary="Add review context to sample.",
        suggested_changes=[
            EvolutionProposalChange(file="app/sample.py", action="modify", rationale="Need review metadata")
        ],
        risk=EvolutionRiskAssessment(risk_score=2, risk_level="low", factors=[]),
    )

    paths = render_patch_artifacts(proposal)
    patch = Path(paths["patch"]).read_text(encoding="utf-8")
    assert "--- a/app/sample.py" in patch
    assert "+++ b/app/sample.py" in patch
    assert "proposal-id: prop_test" in patch
    assert "TODO" not in patch
