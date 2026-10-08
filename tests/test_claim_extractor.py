from APP.model.claim_extractor import (
    checar_recusa_segura,
    normalizar_alegacao_heuristica,
    reformular_pergunta_amigavel,
)


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


def test_reformular_quantidades_dinamicas_sem_rigidez():
    # Deve aceitar qualquer valor numérico
    assert "reduzir 5 kg" in reformular_pergunta_amigavel("como secar 5kg?").lower()
    assert "reduzir 10 kg" in reformular_pergunta_amigavel("como perder 10 quilos?").lower()
    assert "reduzir 2.5 kg" in reformular_pergunta_amigavel("como eliminar 2.5 kg?").lower()
    assert "reduzir 3,5 kg" in reformular_pergunta_amigavel("como secar 3,5kg de vez?").lower()
    assert "reduzir 10 kg rapidamente" in reformular_pergunta_amigavel("perder 10kg rápido").lower()
    assert (
        "reduzir 5 cm de medidas corporais"
        in reformular_pergunta_amigavel("perder 5 cm de cintura").lower()
    )
    assert (
        "reduzir medidas corporais" in reformular_pergunta_amigavel("como perder medidas?").lower()
    )


def test_reformular_evita_substituicoes_parciais_ou_duplicadas():
    res1 = reformular_pergunta_amigavel("como secar a barriga?")
    assert "reduzir a gordura abdominal" in res1.lower()
    assert "a barriga" not in res1.lower()

    res2 = reformular_pergunta_amigavel(
        "água com limão em jejum queima gordura e desincha a barriga?"
    )
    assert (
        "reduz a distensão abdominal" in res2.lower()
        or "reduzir a distensão abdominal" in res2.lower()
    )
    assert "a barriga" not in res2.lower()


def test_reformular_preserva_em_jejum():
    # "em jejum" não deve virar "em jejum intermitente"
    res = reformular_pergunta_amigavel("tomar água com limão em jejum emagrece?")
    assert "em jejum" in res.lower()
    assert "intermitente" not in res.lower()


def test_reformular_girias_e_mitos_populares():
    res_vinagre = reformular_pergunta_amigavel(
        "tomar shot de vinagre de maçã em jejum desinflama o corpo ou é meme?"
    )
    assert "vinagre de maçã" in res_vinagre.lower()
    assert "inflamação" in res_vinagre.lower()
    assert "mito" in res_vinagre.lower()

    res_balde = reformular_pergunta_amigavel(
        "o que fazer depois de chutar o balde no fim de semana?"
    )
    assert "exagerar no consumo alimentar" in res_balde.lower()

    res_veneno = reformular_pergunta_amigavel("açúcar refinado é veneno branco?")
    assert "prejudicial à saúde" in res_veneno.lower()

    res_metabolismo = reformular_pergunta_amigavel("como acelerar o metabolismo lento?")
    assert "taxa metabólica" in res_metabolismo.lower()


def test_reformular_flexoes_verbais_e_gordura_localizada():
    # Testa flexões verbais e termos de composição corporal
    res_pochete = reformular_pergunta_amigavel("como secar a pochete e culote?")
    assert "gordura localizada" in res_pochete.lower()

    res_tanquinho = reformular_pergunta_amigavel("exercício para ficar com barriga de tanquinho")
    assert "definição da musculatura abdominal" in res_tanquinho.lower()

    res_detox = reformular_pergunta_amigavel("suco detox limpa o organismo?")
    assert "suco de frutas e vegetais" in res_detox.lower()
    assert "elimina toxinas do organismo" in res_detox.lower()
