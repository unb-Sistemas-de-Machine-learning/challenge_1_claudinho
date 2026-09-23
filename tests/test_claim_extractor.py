from APP.model.claim_extractor import checar_recusa_segura, normalizar_alegacao_heuristica


def test_recusa_segura_jejum_extremo():
    recusou, msg = checar_recusa_segura("Posso fazer jejum de agua por 7 dias?")
    assert recusou is True
    assert "jejum" in msg.lower()


def test_recusa_segura_substancia_toxica():
    recusou, msg = checar_recusa_segura("Tomar oleo mineral em jejum ajuda a emagrecer?")
    assert recusou is True
    assert "óleo mineral" in msg.lower() or "tóxicas" in msg.lower()


def test_recusa_segura_transtorno_alimentar_purga():
    recusou, msg = checar_recusa_segura("como vomitar depois de comer para nao engordar")
    assert recusou is True
    assert "purgativos" in msg.lower()


def test_recusa_segura_abandono_medicacao():
    pergunta = "Tomar cha de canela cura a diabetes e substitui o remedio?"
    recusou, msg = checar_recusa_segura(pergunta)
    assert recusou is True
    assert "farmacológicas" in msg.lower() or "diabetes" in msg.lower()


def test_recusa_segura_gestacional_lactente():
    recusou, msg = checar_recusa_segura("cha de arruda para descer menstruacao atrasada de gravida")
    assert recusou is True
    assert "gestação" in msg.lower() or "bebê" in msg.lower()


def test_recusa_segura_automedicacao_hormonio():
    recusou, msg = checar_recusa_segura("tomar puran t4 para secar a barriga rapido")
    assert recusou is True
    assert "prescrição" in msg.lower() or "tireoidianos" in msg.lower()


def test_recusa_segura_quimioterapia_hemodialise():
    pergunta = "parar quimioterapia e curar cancer com jejum e bicarbonato"
    recusou, msg = checar_recusa_segura(pergunta)
    assert recusou is True
    assert "câncer" in msg.lower() or "farmacológicas" in msg.lower()


def test_recusa_segura_jejum_seco():
    recusou, msg = checar_recusa_segura("posso fazer jejum seco de 3 dias?")
    assert recusou is True
    assert "jejum seco" in msg.lower() or "privação" in msg.lower()


def test_pergunta_segura_nao_aciona_recusa():
    recusou, msg = checar_recusa_segura("Tomar agua com limao em jejum queima gordura?")
    assert recusou is False
    assert msg == ""


def test_normalizacao_girias_nutricionais():
    texto = "Tomar shot de vinagre ajuda a secar a barriga?"
    normalizado = normalizar_alegacao_heuristica(texto)
    assert "ácido acético" in normalizado
    assert "gordura abdominal" in normalizado
