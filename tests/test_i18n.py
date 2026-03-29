from app.i18n import TRANSLATIONS, _ru_plural_form, get_t, plural, t


class TestTranslate:
    def test_english(self):
        assert t("app_name", "en") == "Flight Tracker"

    def test_russian(self):
        assert t("app_name", "ru") == "Трекер Авиабилетов"

    def test_missing_key_returns_key(self):
        assert t("nonexistent_key", "en") == "nonexistent_key"

    def test_missing_lang_falls_back_to_en(self):
        assert t("app_name", "fr") == "Flight Tracker"

    def test_cabin_names_exist(self):
        for key in ("economy", "economy_plus", "premium_economy", "business", "first"):
            assert t(key, "en") != key
            assert t(key, "ru") != key


class TestGetT:
    def test_get_t_en(self):
        _t = get_t("en")
        assert _t("sign_out") == "Sign out"

    def test_get_t_ru(self):
        _t = get_t("ru")
        assert _t("sign_out") == "Выйти"

    def test_get_t_unknown_key(self):
        _t = get_t("en")
        assert _t("xyz_unknown") == "xyz_unknown"


class TestRuPluralForm:
    def test_1(self):
        assert _ru_plural_form(1) == 0
        assert _ru_plural_form(21) == 0
        assert _ru_plural_form(101) == 0

    def test_2_to_4(self):
        assert _ru_plural_form(2) == 1
        assert _ru_plural_form(3) == 1
        assert _ru_plural_form(4) == 1
        assert _ru_plural_form(22) == 1
        assert _ru_plural_form(34) == 1

    def test_5_plus(self):
        assert _ru_plural_form(5) == 2
        assert _ru_plural_form(11) == 2
        assert _ru_plural_form(12) == 2
        assert _ru_plural_form(14) == 2
        assert _ru_plural_form(20) == 2
        assert _ru_plural_form(0) == 2

    def test_negative(self):
        assert _ru_plural_form(-1) == 0
        assert _ru_plural_form(-2) == 1


class TestPlural:
    def test_en_traveler(self):
        assert plural(1, "traveler", "en") == "traveler"
        assert plural(2, "traveler", "en") == "travelers"
        assert plural(5, "traveler", "en") == "travelers"

    def test_en_day(self):
        assert plural(1, "day", "en") == "day"
        assert plural(3, "day", "en") == "days"

    def test_ru_traveler(self):
        assert plural(1, "traveler", "ru") == "пассажир"
        assert plural(2, "traveler", "ru") == "пассажира"
        assert plural(3, "traveler", "ru") == "пассажира"
        assert plural(5, "traveler", "ru") == "пассажиров"
        assert plural(11, "traveler", "ru") == "пассажиров"
        assert plural(21, "traveler", "ru") == "пассажир"
        assert plural(22, "traveler", "ru") == "пассажира"

    def test_ru_day(self):
        assert plural(1, "day", "ru") == "день"
        assert plural(2, "day", "ru") == "дня"
        assert plural(5, "day", "ru") == "дней"

    def test_unknown_word(self):
        assert plural(2, "unknown", "en") == "unknown"
        assert plural(2, "unknown", "ru") == "unknown"


class TestGetTPlural:
    def test_get_t_has_plural(self):
        _t = get_t("ru")
        assert _t.plural(2, "traveler") == "пассажира"
        assert _t.lang == "ru"

    def test_get_t_en_plural(self):
        _t = get_t("en")
        assert _t.plural(1, "traveler") == "traveler"
        assert _t.plural(2, "traveler") == "travelers"


class TestTranslationCompleteness:
    def test_all_keys_have_both_languages(self):
        for key, entry in TRANSLATIONS.items():
            assert "en" in entry, f"Missing English for key: {key}"
            assert "ru" in entry, f"Missing Russian for key: {key}"
