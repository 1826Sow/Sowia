from funding_hub import safe_external_url


def test_accepts_https_support_destination():
    url = "https://paypal.me/example"
    assert safe_external_url(url) == url


def test_rejects_non_https_destinations():
    assert safe_external_url("http://example.com/support") is None
    assert safe_external_url("javascript:alert(1)") is None
    assert safe_external_url("mailto:contact@example.com") is None


def test_rejects_credentials_and_fragments():
    assert safe_external_url("https://user:password@example.com") is None
    assert safe_external_url("https://example.com/support#private") is None


def test_rejects_empty_malformed_and_overlong_values():
    assert safe_external_url("") is None
    assert safe_external_url(None) is None
    assert safe_external_url("https://") is None
    assert safe_external_url("https://example.com:invalid") is None
    assert safe_external_url("https://example.com/" + "x" * 2000) is None
