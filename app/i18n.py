"""Internationalization support for English and Russian."""

TRANSLATIONS: dict[str, dict[str, str]] = {
    # Navigation
    "app_name": {"en": "Flight Tracker", "ru": "Трекер Авиабилетов"},
    "sign_out": {"en": "Sign out", "ru": "Выйти"},
    "delete_profile": {"en": "Delete profile", "ru": "Удалить профиль"},
    "delete_profile_confirm": {"en": "Delete all your data and sign out?", "ru": "Удалить все данные и выйти?"},

    # Login
    "welcome": {"en": "Welcome", "ru": "Добро пожаловать"},
    "welcome_to": {"en": "Welcome to Flight Tracker", "ru": "Добро пожаловать в Трекер Авиабилетов"},
    "sign_in_prompt": {"en": "Sign in to track flight prices", "ru": "Войдите, чтобы отслеживать цены на авиабилеты"},
    "sign_in_google": {"en": "Sign in with Google", "ru": "Войти через Google"},
    "access_denied_for": {"en": "Access denied for", "ru": "Доступ запрещён для"},

    # Index page
    "tracked_routes": {"en": "Tracked Routes", "ru": "Отслеживаемые маршруты"},
    "no_routes_yet": {"en": "No routes tracked yet. Add one below to get started.", "ru": "Маршрутов пока нет. Добавьте первый ниже."},
    "add_new_route": {"en": "Add New Route", "ru": "Добавить маршрут"},
    "origin": {"en": "Origin", "ru": "Откуда"},
    "destination": {"en": "Destination", "ru": "Куда"},
    "origin_placeholder": {"en": "SFO or San Francisco, US", "ru": "SVO или Москва, Россия"},
    "destination_placeholder": {"en": "NRT or Tokyo, Japan", "ru": "NRT или Токио, Япония"},
    "departure": {"en": "Departure", "ru": "Вылет"},
    "return": {"en": "Return", "ru": "Возврат"},
    "round_trip": {"en": "Round Trip", "ru": "Туда-обратно"},
    "cabin": {"en": "Cabin", "ru": "Класс"},
    "airlines_label": {"en": "Airlines", "ru": "Авиакомпании"},
    "alliances_label": {"en": "Alliances", "ru": "Альянсы"},
    "travelers": {"en": "Travelers", "ru": "Пассажиры"},
    "travelers_ages": {"en": "Travelers (ages)", "ru": "Пассажиры (возраст)"},
    "add_traveler": {"en": "+ Add Traveler", "ru": "+ Добавить пассажира"},
    "add_route_btn": {"en": "Add Route", "ru": "Добавить маршрут"},
    "remove": {"en": "Remove", "ru": "Убрать"},

    # Cabin types
    "economy_plus": {"en": "Economy Plus", "ru": "Эконом Плюс"},
    "premium_economy": {"en": "Premium Economy", "ru": "Премиум Эконом"},
    "business": {"en": "Business", "ru": "Бизнес"},
    "first": {"en": "First", "ru": "Первый"},
    "economy": {"en": "Economy", "ru": "Эконом"},
    "any_cabin": {"en": "Any cabin", "ru": "Любой класс"},
    "any": {"en": "Any", "ru": "Любой"},

    # Route card actions
    "pause": {"en": "Pause", "ru": "Пауза"},
    "resume": {"en": "Resume", "ru": "Возобновить"},
    "check_now": {"en": "Check Now", "ru": "Проверить"},
    "edit": {"en": "Edit", "ru": "Изменить"},
    "delete": {"en": "Delete", "ru": "Удалить"},
    "delete_route_confirm": {"en": "Delete this route and all its data?", "ru": "Удалить маршрут и все данные?"},
    "checking": {"en": "Checking\u2026", "ru": "Проверяем\u2026"},

    # Nearby dates
    "nearby_hidden": {"en": "Nearby dates: hidden", "ru": "Ближайшие даты: скрыты"},
    "pm_1_day": {"en": "\u00b11 day", "ru": "\u00b11 день"},
    "pm_2_days": {"en": "\u00b12 days", "ru": "\u00b12 дня"},
    "pm_3_days": {"en": "\u00b13 days", "ru": "\u00b13 дня"},

    # Plural forms handled by plural() function, these are fallbacks
    "traveler_1": {"en": "traveler", "ru": "пассажир"},
    "traveler_2": {"en": "travelers", "ru": "пассажира"},
    "traveler_5": {"en": "travelers", "ru": "пассажиров"},

    # Route detail
    "all_routes": {"en": "All Routes", "ru": "Все маршруты"},
    "type": {"en": "Type", "ru": "Тип"},
    "one_way": {"en": "One Way", "ru": "В одну сторону"},
    "ages": {"en": "ages", "ru": "возраст"},
    "status": {"en": "Status", "ru": "Статус"},
    "active": {"en": "Active", "ru": "Активен"},
    "paused": {"en": "Paused", "ru": "Приостановлен"},
    "current_prices": {"en": "Current Prices", "ru": "Текущие цены"},
    "requested": {"en": "requested", "ru": "запрошенная дата"},
    "nearby_dates": {"en": "Nearby dates", "ru": "Ближайшие даты"},
    "hidden": {"en": "Hidden", "ru": "Скрыты"},
    "ai_prediction": {"en": "AI Prediction", "ru": "Прогноз ИИ"},
    "trend": {"en": "Trend", "ru": "Тренд"},
    "recommendation": {"en": "Recommendation", "ru": "Рекомендация"},
    "confidence": {"en": "confidence", "ru": "уверенность"},
    "best_buy": {"en": "Best buy", "ru": "Лучшая дата покупки"},
    "price_history": {"en": "Price History", "ru": "История цен"},
    "no_price_data": {"en": "No price data yet. Click \"Check Prices Now\" to fetch.", "ru": "Данных о ценах пока нет. Нажмите «Проверить цены»."},
    "prediction_history": {"en": "Prediction History", "ru": "История прогнозов"},
    "check_prices_now": {"en": "Check Prices Now", "ru": "Проверить цены"},
    "checked": {"en": "Checked", "ru": "Проверено"},
    "total_price": {"en": "Total Price", "ru": "Итого"},
    "flight": {"en": "Flight", "ru": "Рейс"},
    "date": {"en": "Date", "ru": "Дата"},
    "summary": {"en": "Summary", "ru": "Описание"},

    # Trend values
    "up": {"en": "Up", "ru": "Рост"},
    "down": {"en": "Down", "ru": "Снижение"},
    "stable": {"en": "Stable", "ru": "Стабильно"},

    # Edit modal
    "edit_route": {"en": "Edit Route", "ru": "Изменить маршрут"},
    "cancel": {"en": "Cancel", "ru": "Отмена"},
    "save_changes": {"en": "Save Changes", "ru": "Сохранить"},

    # Footer
    "prices_shown_in_usd": {"en": "Prices are shown in US Dollars ($). Totals include all travelers.", "ru": "Цены указаны в долларах США ($). Итого включает всех пассажиров."},
    "prices_shown_in_rub": {"en": "Prices are shown in Russian Rubles (\u20bd). Totals include all travelers.", "ru": "Цены указаны в российских рублях (\u20bd). Итого включает всех пассажиров."},

    # Traveler count (for pluralization, see plural() function)
    "traveler_s": {"en": "traveler", "ru": "пассажир"},
    "travelers_s": {"en": "travelers", "ru": "пассажиров"},

    # Validation errors
    "failed_add": {"en": "Failed to add route. Check your input.", "ru": "Не удалось добавить маршрут. Проверьте данные."},
    "failed_update": {"en": "Failed to update route.", "ru": "Не удалось обновить маршрут."},
}


def t(key: str, lang: str = "en") -> str:
    """Get translation for a key in the given language."""
    entry = TRANSLATIONS.get(key, {})
    return entry.get(lang, entry.get("en", key))


def _ru_plural_form(n: int) -> int:
    """Return 0 for '1 пассажир', 1 for '2 пассажира', 2 for '5 пассажиров'."""
    abs_n = abs(n)
    if abs_n % 10 == 1 and abs_n % 100 != 11:
        return 0
    if 2 <= abs_n % 10 <= 4 and not (12 <= abs_n % 100 <= 14):
        return 1
    return 2


# Russian plural forms: (1-form, 2-4-form, 5+-form)
_RU_PLURALS = {
    "traveler": ("пассажир", "пассажира", "пассажиров"),
    "day": ("день", "дня", "дней"),
}


def plural(n: int, word: str, lang: str = "en") -> str:
    """Return correct plural form for a number."""
    if lang == "ru" and word in _RU_PLURALS:
        forms = _RU_PLURALS[word]
        return forms[_ru_plural_form(n)]
    # English: simple s/no-s
    if lang == "en":
        if word == "traveler":
            return "traveler" if n == 1 else "travelers"
        if word == "day":
            return "day" if n == 1 else "days"
    return word


def get_t(lang: str):
    """Return a translation function bound to a language."""
    def _t(key: str) -> str:
        return t(key, lang)
    _t.plural = lambda n, word: plural(n, word, lang)
    _t.lang = lang
    return _t
