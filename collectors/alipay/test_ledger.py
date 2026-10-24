import copy
import tempfile
import unittest
from pathlib import Path

from ledger import Ledger, parse_row


def fixture(amount="- 6.00", status="交易成功"):
    return {"headers": ["创建时间", "名称", "商家订单号 | 交易号", "对方", "金额", "状态"],
            "cells": ["2026.10.23\n17:56", "测试商户", "订单号:123 | 交易号:202610230001", "测试商户", amount, status],
            "links": [{"text": "测试商户", "href": "https://consumeprod.alipay.com/record/detail/simpleDetail.htm?bizType=TRADE&bizInNo=202610230001&gmtBizCreate=20261023175613"}]}


class FinancialRowsTest(unittest.TestCase):
    def test_amount_is_decimal_cents_and_not_order_number(self):
        row = parse_row(fixture("- 1,234.59"))
        self.assertEqual(row["amount_cents"], 123459)
        self.assertEqual(row["direction"], "outflow")
        self.assertEqual(row["created_at"], "2026-10-23T17:56:13+08:00")

    def test_income_is_not_classified_as_spending(self):
        row = parse_row(fixture("+ 30.00"))
        self.assertEqual((row["amount_cents"], row["direction"]), (3000, "inflow"))

    def test_ambiguous_or_absent_amount_fails_instead_of_guessing(self):
        for value in ("1234567890123456", "6.00", "- 6.999", "付款成功"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_row(fixture(value))
        row = fixture()
        row["cells"].append("+ 1.00")
        with self.assertRaises(ValueError):
            parse_row(row)

    def test_untrusted_or_missing_external_identity_is_rejected(self):
        for suffix in ("https://evil.example/record/detail/simpleDetail.htm?bizType=TRADE&bizInNo=202610230001", "https://consumeprod.alipay.com/record/detail/simpleDetail.htm?bizType=TRADE"):
            row = fixture()
            row["links"][0]["href"] = suffix
            with self.assertRaises(ValueError):
                parse_row(row)

    def test_duplicate_scans_keep_one_transaction_and_changed_status_keeps_history(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Ledger(Path(directory) / "ledger.sqlite3")
            row = parse_row(fixture())
            self.assertEqual(ledger.save([row], "2026-10-23T10:00:00Z"), {"new": 1, "changed": 0, "total": 1})
            self.assertEqual(ledger.save([row], "2026-10-23T10:10:00Z"), {"new": 0, "changed": 0, "total": 1})
            changed = parse_row(fixture(status="退款成功"))
            self.assertEqual(ledger.save([changed], "2026-10-24T10:00:00Z"), {"new": 0, "changed": 1, "total": 1})
            self.assertEqual(ledger.db.execute("SELECT COUNT(*) FROM transaction_versions").fetchone()[0], 2)
            self.assertEqual(ledger.db.execute("SELECT version,status FROM transactions").fetchone(), (2, "退款成功"))

    def test_page_without_counterparty_column_does_not_shift_amount(self):
        row = fixture("- 0.01")
        row["headers"].remove("对方")
        row["cells"].pop(3)
        parsed = parse_row(row)
        self.assertEqual(parsed["counterparty"], "")
        self.assertEqual(parsed["amount_cents"], 1)


if __name__ == "__main__":
    unittest.main()
