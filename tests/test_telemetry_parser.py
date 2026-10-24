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


import pytest


@pytest.mark.parametrize('text,amount', [
    ('支付成功通知\n账户193****9886于10月24日12时01分成功付款14.00元', 14),
    ('交易提醒\n你有一笔4.00元的支出，领1元生活缴费红包。使用花呗支付，请及时还款。', 4),
    ('交易提醒\n你在友宝有一笔3.10元的免密/自动扣款支付，点击领取6个支付宝积分。', 3.1),
    ('微信支付\n你已向商家付款￥28.00', 28),
])
def test_transaction_amount_ignores_other_numbers(text, amount):
    value = _parse_transaction(text)
    assert value['amount'] == amount
    assert value['amount_cents'] == round(amount * 100)
    assert value['parser'] == 'rules-v2'


@pytest.mark.parametrize('text', [
    '支付宝通知\n登录提醒：你的账户193******86于10月24日15:02登录支付宝',
    '微信支付 : 昨日记账日报，点击查看详情',
    '支付通知\n麻烦你发一下支付宝码',
    '支付通知',
    '田一帆\n跑个之前5.5的动画',
    '支付宝：领取1元生活缴费红包',
    '支付14元；退款4元',
])
def test_non_payments_and_ambiguous_amounts_not_counted(text):
    assert _parse_transaction(text) is None
