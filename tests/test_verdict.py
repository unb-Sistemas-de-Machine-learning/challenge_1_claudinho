import pytest

from APP.verdict import classificar_veredito

# Limiares definidos pela frente de Modelo: 0.35 e 0.65


@pytest.mark.parametrize(
    "risk_score, esperado",
    [
        (0.00, "seguro"),
        (0.34, "seguro"),
        (0.35, "cautela"),
        (0.50, "cautela"),
        (0.65, "cautela"),
        (0.66, "desinformacao"),
        (1.00, "desinformacao"),
    ],
)
def test_veredito_derivado_do_risk_score(risk_score, esperado):
    assert classificar_veredito(risk_score) == esperado


@pytest.mark.parametrize("invalido", [-0.01, 1.01])
def test_rejeita_score_fora_do_intervalo(invalido):
    with pytest.raises(ValueError):
        classificar_veredito(invalido)
