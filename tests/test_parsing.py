import unittest

import cwsreviews.parsing


class TestParsing(unittest.TestCase):
    def test_parse_wiz_global_data(self) -> None:
        html = (
            "<html><head><script>"
            'window.WIZ_global_data = {"FdrFJe":"123","cfb2h":"bl","Im6cmf":"/_/X"};'
            "</script></head></html>"
        )
        wiz = cwsreviews.parsing.parse_wiz_global_data(html)
        self.assertEqual(wiz["FdrFJe"], "123")
        self.assertEqual(wiz["cfb2h"], "bl")

    def test_parse_ds1_rpcid(self) -> None:
        html = (
            "<script>"
            "AF_dataServiceRequests = {'ds:0' : {id:'xY2Ddd',request:[\"abc\"]},"
            "'ds:1' : {id:'x1DgCd',request:[\"abc\",[10],2,null,null,null,0]}};"
            "</script>"
        )
        self.assertEqual(cwsreviews.parsing.parse_ds1_rpcid(html), "x1DgCd")


if __name__ == "__main__":
    unittest.main()
