from cronometragem import TIME_LIMIT_SECONDS, format_duration, is_censored, DIFICULDADES, slugify, validate_trial_form


def test_is_censored_false_below_limit():
    assert is_censored(2099, limit_seconds=2100) is False


def test_is_censored_true_at_limit():
    assert is_censored(2100, limit_seconds=2100) is True


def test_is_censored_true_above_limit():
    assert is_censored(2200, limit_seconds=2100) is True


def test_is_censored_uses_default_limit_of_35_minutes():
    assert TIME_LIMIT_SECONDS == 35 * 60
    assert is_censored(TIME_LIMIT_SECONDS) is True
    assert is_censored(TIME_LIMIT_SECONDS - 1) is False


def test_format_duration_zero():
    assert format_duration(0) == "00:00"


def test_format_duration_under_a_minute():
    assert format_duration(45) == "00:45"


def test_format_duration_minutes_and_seconds():
    assert format_duration(90) == "01:30"


def test_format_duration_at_time_limit():
    assert format_duration(2100) == "35:00"


def test_format_duration_truncates_fractional_seconds():
    assert format_duration(59.9) == "00:59"


def test_slugify_lowercases_and_joins_with_underscore():
    assert slugify("Miguel Diniz") == "miguel_diniz"


def test_slugify_strips_accents():
    assert slugify("João") == "joao"


def test_slugify_falls_back_when_nothing_left():
    assert slugify("   ") == "integrante"


def test_dificuldades_are_the_three_expected_levels():
    assert DIFICULDADES == ["facil", "medio", "dificil"]


def test_validate_trial_form_accepts_valid_input():
    assert validate_trial_form("Miguel", "two-sum", "facil", "5") == []


def test_validate_trial_form_rejects_empty_integrante():
    errors = validate_trial_form("", "two-sum", "facil", "5")
    assert "Integrante é obrigatório." in errors


def test_validate_trial_form_rejects_empty_kata():
    errors = validate_trial_form("Miguel", "  ", "facil", "5")
    assert "Kata é obrigatório." in errors


def test_validate_trial_form_rejects_invalid_dificuldade():
    errors = validate_trial_form("Miguel", "two-sum", "muito-dificil", "5")
    assert "Dificuldade deve ser facil, medio ou dificil." in errors


def test_validate_trial_form_rejects_negative_testes_passados():
    errors = validate_trial_form("Miguel", "two-sum", "facil", "-1")
    assert "Testes passados não pode ser negativo." in errors


def test_validate_trial_form_rejects_non_numeric_testes_passados():
    errors = validate_trial_form("Miguel", "two-sum", "facil", "abc")
    assert "Testes passados deve ser um número inteiro." in errors


def test_validate_trial_form_reports_multiple_errors_at_once():
    errors = validate_trial_form("", "", "invalida", "abc")
    assert len(errors) == 4
