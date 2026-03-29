from app.i18n import TRANSLATIONS, get_t, t


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


class TestTranslationCompleteness:
    def test_all_keys_have_both_languages(self):
        for key, entry in TRANSLATIONS.items():
            assert "en" in entry, f"Missing English for key: {key}"
            assert "ru" in entry, f"Missing Russian for key: {key}"
