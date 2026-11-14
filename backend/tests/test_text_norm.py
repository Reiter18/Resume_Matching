from app.text_norm import company_key, normalize_city, normalize_title, number_tokens, seniority_of


def test_company_and_title_normalization():
    assert company_key("Acme GmbH") == company_key("ACME") == company_key("Acme GmbH & Co. KG") == "acme"
    assert company_key("ООО «Ромашка»") == company_key("Ромашка") == "ромашка"
    assert company_key("GmbH") == "gmbh"  
    assert normalize_title("Junior Python Developer (m/f/d)") == "junior python developer"
    assert normalize_title("Python Developer (w/m/d) - Remote") == "python developer"
    assert normalize_title("Python-разработчик (удалённо)") == "python разработчик"


def test_seniority_numbers_and_city():
    assert seniority_of("Junior Python Developer") == {"junior"} and seniority_of("Ведущий разработчик") == {"lead"}
    assert seniority_of("Python Developer") == frozenset()
    assert number_tokens("Developer 2 (Team 5)") == {"2", "5"}
    assert normalize_city("Berlin, Germany") == normalize_city("10115 Berlin") == "berlin"
    assert normalize_city("Remote") == "" and normalize_city(None) == ""
