BTN_FAL = "🔮 فال حافظ"
BTN_SUB = "👤 اشتراک من"
BTN_GUIDE = "📖 آموزش فال"
BTN_INVITE = "🎁 دعوت از دوستان"
BTN_PROFILE = "👤 پروفایل من"
BTN_BUY = "💳 خرید اشتراک"
BTN_BACK = "⬅️ بازگشت به منو"
BTN_AGAIN = "🔮 فال دوباره"
BTN_HOME = "🏠 بازگشت به منو"

BTN_PAYMENT = "💳 ادامه به پرداخت"


def main_menu():
    return {
        "keyboard": [
            [{"text": BTN_FAL}],
            [{"text": BTN_SUB}, {"text": BTN_PROFILE}],
            [{"text": BTN_GUIDE}, {"text": BTN_INVITE}],
        ],
        "resize_keyboard": True,
    }


def subscription_menu():
    return {
        "keyboard": [
            [{"text": BTN_BUY}],
            [{"text": BTN_BACK}],
        ],
        "resize_keyboard": True,
    }


def purchase_menu():
    return {
        "keyboard": [
            [{"text": BTN_PAYMENT}],
            [{"text": BTN_BACK}],
        ],
        "resize_keyboard": True,
    }


def fortune_menu():
    return {
        "keyboard": [[{"text": BTN_AGAIN}], [{"text": BTN_HOME}]],
        "resize_keyboard": True,
    }