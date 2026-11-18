import unittest

from backend.web_research import search_web


class WebResearchTests(unittest.TestCase):
    def test_video_request_uses_video_results_and_filters_non_youtube_urls(self):
        def videos(query, **kwargs):
            return [
                {
                    "title": "GTA V - melhores carros e gameplay",
                    "content": "https://www.youtube.com/watch?v=abc123",
                    "description": "Lista de carros do GTA V.",
                    "duration": "12:30",
                },
                {
                    "title": "GTA V cars",
                    "content": "https://example.org/article",
                    "description": "Artigo sobre carros.",
                },
            ]

        result = search_web("vídeos no YouTube sobre melhores carros do GTA V", searcher=videos)
        self.assertEqual(result["search_type"], "video")
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["results"][0]["url"], "https://www.youtube.com/watch?v=abc123")
        self.assertIn("YouTube", result["summary"])

    def test_video_search_excludes_unrelated_wikipedia_and_keeps_youtube_links(self):
        from backend.web_research import search_web
        raw = [
            {"title": "Minecraft survival gameplay", "content": "https://www.youtube.com/watch?v=abc123", "description": "Minecraft gameplay"},
            {"title": "Video - Wikipedia", "content": "https://en.wikipedia.org/wiki/Video", "description": "Definition of video"},
            {"title": "GTA V cars", "content": "https://www.youtube.com/watch?v=car123", "description": "Cars in GTA V"},
        ]
        result = search_web("vídeo do YouTube sobre minecraft", searcher=lambda *a, **k: raw)
        self.assertEqual(result["search_type"], "video")
        self.assertEqual(result["count"], 1)
        self.assertIn("youtube.com", result["results"][0]["url"])
        self.assertIn("Minecraft", result["results"][0]["title"])

    def test_video_search_returns_clear_empty_result_when_no_relevant_youtube_video(self):
        def videos(query, **kwargs):
            return [{
                "title": "Receita de bolo",
                "content": "https://www.youtube.com/watch?v=cake",
                "description": "Como fazer bolo.",
            }]

        result = search_web("vídeo de carros do GTA V", searcher=videos)
        self.assertEqual(result["count"], 0)
        self.assertIn("Não encontrei vídeos", result["summary"])

    def test_general_search_ranks_relevant_results_and_deduplicates(self):
        def text_search(query, **kwargs):
            return [
                {"title": "Wikipédia - carros", "href": "https://pt.wikipedia.org/wiki/Carro", "body": "Definição geral de carro."},
                {"title": "GTA V: melhores carros", "href": "https://example.org/gta-cars", "body": "Guia dos melhores carros do GTA V."},
                {"title": "GTA V: melhores carros", "href": "https://example.org/gta-cars", "body": "Duplicado."},
            ]

        result = search_web("GTA V melhores carros", searcher=text_search)
        self.assertEqual(result["count"], 2)
        self.assertEqual(result["results"][0]["url"], "https://example.org/gta-cars")
        self.assertGreaterEqual(result["results"][0]["relevance"], result["results"][1]["relevance"])


    def test_bm25_reranker_prefers_title_and_topic_match(self):
        from backend.web_research import _bm25_scores
        scores = _bm25_scores("Minecraft survival", [
            ("Minecraft survival guide", "Building and exploring"),
            ("Cooking recipes", "Minecraft is not mentioned"),
        ])
        self.assertGreater(scores[0], scores[1])

    def test_canonical_url_rejects_http_and_local_addresses(self):
        from backend.web_research import _canonical_url
        self.assertIsNone(_canonical_url("http://example.org/article"))
        self.assertIsNone(_canonical_url("https://127.0.0.1/private"))
        self.assertIsNone(_canonical_url("https://localhost/admin"))

    def test_search_strips_tracking_parameters_and_marks_verification_limit(self):
        raw = [{"title": "Guia Minecraft", "href": "https://example.org/guide?utm_source=mail&x=1",
                "body": "Guia completo de Minecraft", "date": "2026-11-17"}]
        result = search_web("Minecraft guia", searcher=lambda *a, **k: raw)
        self.assertEqual(result["count"], 1)
        item = result["results"][0]
        self.assertEqual(item["url"], "https://example.org/guide?x=1")
        self.assertEqual(item["published_at"], "2026-11-17")
        self.assertEqual(item["source_verification"], "url_validated_content_not_independently_verified")

    def test_empty_query_is_rejected(self):
        with self.assertRaises(ValueError):
            search_web("   ")

    def test_general_search_falls_back_to_all_engines(self):
        calls = []

        def flaky_search(query, **kwargs):
            calls.append(kwargs.get("backend"))
            if kwargs.get("backend") == "auto":
                raise RuntimeError("temporary provider failure")
            if kwargs.get("backend") == "bing,duckduckgo,yahoo,startpage":
                return []
            return [{
                "title": "Documentação oficial do Python",
                "href": "https://docs.python.org/3/",
                "body": "Documentação da linguagem Python.",
            }]

        result = search_web("documentação Python", searcher=flaky_search)
        self.assertEqual(calls, ["auto", "bing,duckduckgo,yahoo,startpage", "all"])
        self.assertEqual(result["count"], 1)
        self.assertIn("docs.python.org", result["results"][0]["url"])


if __name__ == "__main__":
    unittest.main()
