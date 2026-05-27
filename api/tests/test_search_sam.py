from datetime import date
import json
from urllib.parse import parse_qs, urlparse

from api.agent.tools.search_sam import search_sam_opportunities


class FakeResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def test_search_sam_builds_expected_query_and_normalizes(monkeypatch):
    captured = {}

    def fake_urlopen(url, timeout):
        captured["url"] = url
        captured["timeout"] = timeout
        return FakeResponse({
            "totalRecords": 1,
            "opportunitiesData": [{
                "noticeId": "abc-123",
                "title": "Facilities support services",
                "fullParentPathName": "DEPT OF VETERANS AFFAIRS",
                "solicitationNumber": "VA-001",
                "postedDate": "05/01/2026",
                "responseDeadLine": "2026-05-21T16:00:00-05:00",
                "naicsCode": "561210",
                "type": "Presolicitation",
                "setAside": "Total Small Business Set-Aside",
                "placeOfPerformance": {"city": {"name": "Austin"}, "state": {"name": "Texas"}},
                "description": "Maintain and repair VA facilities.",
                "resourceLinks": ["https://example.test/solicitation.pdf"],
                "uiLink": "https://sam.gov/opp/abc-123/view",
            }]
        })

    monkeypatch.setattr("api.agent.tools.search_sam.urllib.request.urlopen", fake_urlopen)

    out = search_sam_opportunities(
        keyword="facilities support",
        api_key="SAM-test-key",
        posted_from=date(2026, 5, 1),
        posted_to=date(2026, 5, 9),
        limit=5,
    )

    parsed = urlparse(captured["url"])
    qs = parse_qs(parsed.query)
    assert parsed.netloc == "api.sam.gov"
    assert qs["keyword"] == ["facilities support"]
    assert qs["postedFrom"] == ["05/01/2026"]
    assert qs["postedTo"] == ["05/09/2026"]
    assert qs["limit"] == ["5"]
    assert qs["api_key"] == ["SAM-test-key"]
    assert captured["timeout"] == 20

    assert out.total_records == 1
    assert len(out.opportunities) == 1
    opp = out.opportunities[0]
    assert opp.notice_id == "abc-123"
    assert opp.title == "Facilities support services"
    assert opp.agency == "DEPT OF VETERANS AFFAIRS"
    assert opp.naics == "561210"
    assert opp.due_date == "2026-05-21"
    assert opp.attachments == ["https://example.test/solicitation.pdf"]
    assert opp.source_url == "https://sam.gov/opp/abc-123/view"


def test_search_sam_requires_api_key(monkeypatch, tmp_path):
    monkeypatch.delenv("SAM_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)
    try:
        search_sam_opportunities(keyword="cyber", api_key=None)
    except RuntimeError as exc:
        assert "SAM_API_KEY" in str(exc)
    else:
        raise AssertionError("expected missing key error")
