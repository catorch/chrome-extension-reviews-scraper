import unittest

import cwsreviews.scraper


class TestScraperInputs(unittest.TestCase):
    def test_resolve_raw_id(self) -> None:
        url = cwsreviews.scraper.resolve_input_to_reviews_url(
            "chphlpgkkbolifaimnlloiipkdnihall", hl="en"
        )
        self.assertIn("/detail/", url)
        self.assertIn("/reviews?hl=en", url)

    def test_resolve_detail_url(self) -> None:
        url = cwsreviews.scraper.resolve_input_to_reviews_url(
            "https://chromewebstore.google.com/detail/onetab/chphlpgkkbolifaimnlloiipkdnihall?hl=en",
            hl="en",
        )
        self.assertEqual(
            url,
            "https://chromewebstore.google.com/detail/onetab/chphlpgkkbolifaimnlloiipkdnihall/reviews?hl=en",
        )


if __name__ == "__main__":
    unittest.main()
