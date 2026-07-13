from unittest.mock import MagicMock, patch

from claims import ClaimList, extract_claims


def test_extract_claims_returns_list_from_response():
    fake_claims = ClaimList(claims=["Claim A.", "Claim B."])
    fake_response = MagicMock(parsed=fake_claims)

    with patch("claims.genai.Client") as mock_client_cls:
        mock_client_cls.return_value.models.generate_content.return_value = fake_response
        result = extract_claims("Summary with two facts.")

    assert result == ["Claim A.", "Claim B."]
