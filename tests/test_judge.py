from unittest.mock import MagicMock, patch

from judge import Judgment, judge_claim


def test_judge_claim_returns_parsed_response():
    fake_judgment = Judgment(verdict="SUPPORTED", reason="matches evidence")
    fake_response = MagicMock(parsed=fake_judgment)

    with patch("judge.genai.Client") as mock_client_cls:
        mock_client_cls.return_value.models.generate_content.return_value = fake_response
        result = judge_claim(
            "The drug improved survival.", ["Survival increased from 40% to 62%."]
        )

    assert result.verdict == "SUPPORTED"
    assert result.reason == "matches evidence"


def test_judge_claim_handles_no_evidence():
    fake_judgment = Judgment(verdict="UNVERIFIABLE", reason="no evidence")
    fake_response = MagicMock(parsed=fake_judgment)

    with patch("judge.genai.Client") as mock_client_cls:
        mock_client = mock_client_cls.return_value
        mock_client.models.generate_content.return_value = fake_response

        result = judge_claim("Some claim", [])

    assert result.verdict == "UNVERIFIABLE"
    call_kwargs = mock_client.models.generate_content.call_args.kwargs
    assert "(no evidence retrieved)" in call_kwargs["contents"]
