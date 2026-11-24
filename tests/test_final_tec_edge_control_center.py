import pytest

from final_tec_edge_control_center import parse_edge_inputs
from final_tec_edge_engine import EdgeSelectionError


def test_parses_profile_and_candidate_list():
    profile, candidates = parse_edge_inputs('{"region":"eu"}', '[{"resource_id":"r1"}]')
    assert profile == {"region": "eu"}
    assert candidates == [{"resource_id": "r1"}]


@pytest.mark.parametrize(("profile", "candidates"), [
    ("not-json", "[]"),
    ("{}", "not-json"),
    ("[]", "[]"),
    ("{}", "{}"),
])
def test_rejects_malformed_or_wrong_json_shapes(profile, candidates):
    with pytest.raises(EdgeSelectionError):
        parse_edge_inputs(profile, candidates)
