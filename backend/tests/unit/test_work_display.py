from app.works.service import work_display


def test_work_name_uses_original_product_and_picture_purpose():
    original = {"product": {"name": "陶瓷杯"}, "parameters": {"purpose": "场景图"}}
    assert work_display("image", original) == "陶瓷杯场景图"


def test_missing_original_name_does_not_invent_a_product():
    assert work_display('video', {}) is None


def test_copy_title_uses_original_product_instead_of_current_editor():
    assert work_display('copy', {'product': {'name': '原商品'}}) == '原商品文案'
