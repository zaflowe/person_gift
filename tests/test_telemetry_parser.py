from app.routers.telemetry import _parse_transaction


def test_alipay_expense():
    result = _parse_transaction("支付宝 你已向某某餐饮付款￥36.50")
    assert result["type"] == "expense"
    assert result["amount"] == 36.50


def test_refund():
    result = _parse_transaction("支付宝退款 18.00元已退回")
    assert result["type"] == "refund"
    assert result["amount"] == 18.0


def test_non_transaction():
    assert _parse_transaction("今晚记得带伞") is None
