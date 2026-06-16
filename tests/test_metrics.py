from app.metrics import dilution_ratio, equity_ratio, ratio_percent, sales_ratio


def test_ratio_percent() -> None:
    assert ratio_percent(300, 1000) == 30.0
    assert ratio_percent(1, 3) == 33.33
    assert ratio_percent(None, 1000) is None
    assert ratio_percent(300, None) is None
    assert ratio_percent(300, 0) is None


def test_named_ratios() -> None:
    assert sales_ratio(300, 1000) == 30.0
    assert equity_ratio(50, 200) == 25.0
    assert dilution_ratio(10, 100) == 10.0

