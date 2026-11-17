import unittest

from backend.web_research import search_web


class WebResearchTests(unittest.TestCase):
    def test_returns_source_linked_results_and_caps_count(self):
        calls = []

        def fake_search(query, **kwargs):
            calls.append((query, kwargs))
            return [
                {"title": "Docs", "href": "https://docs.example.org/guide", "body": "Official documentation."},
                {"title": "Unsafe scheme", "href": "javascript:alert(1)", "body": "Must be discarded."},
                {"title": "Second", "href": "https://example.org/page", "body": "Another source."},
            ]

        result = search_web("  treinamento de modelos  ", max_results=2, searcher=fake_search)
        self.assertEqual(result["query"], "treinamento de modelos")
        self.assertEqual(result["count"], 2)
        self.assertTrue(all(item["url"].startswith("https://") for item in result["results"]))
        self.assertIn("https://docs.example.org/guide", result["summary"])
        self.assertEqual(calls[0][1]["max_results"], 2)

    def test_rejects_empty_and_overlong_queries(self):
        with self.assertRaises(ValueError):
            search_web("   ", searcher=lambda *_args, **_kwargs: [])
        with self.assertRaises(ValueError):
            search_web("x" * 501, searcher=lambda *_args, **_kwargs: [])

    def test_returns_explicit_empty_result_without_fabricating_sources(self):
        result = search_web("ULTRON pesquisa", searcher=lambda *_args, **_kwargs: [])
        self.assertEqual(result["count"], 0)
        self.assertEqual(result["results"], [])
        self.assertIn("não retornou resultados", result["summary"])

    def test_tries_fallback_backend_after_empty_first_attempt(self):
        backends = []

        def fake_search(_query, **kwargs):
            backends.append(kwargs["backend"])
            return [] if len(backends) == 1 else [
                {"title": "Result", "href": "https://example.org", "body": "Found."}
            ]

        result = search_web("consulta", searcher=fake_search)
        self.assertEqual(len(backends), 2)
        self.assertEqual(result["count"], 1)


if __name__ == "__main__":
    unittest.main()
