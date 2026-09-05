"""O registro precisa chegar ao stdout de verdade — Docs/Production/02, secao 3.

A suite do pytest captura logs pelo proprio framework de logging, entao ela
passa mesmo sem handler nenhum configurado. Estes testes cobrem justamente o
que a captura do pytest esconde.
"""

import logging
import sys

from APP.observabilidade import LOGGER_INFERENCIA, configurar_logging


def test_o_logger_escreve_no_stdout():
    configurar_logging()
    logger = logging.getLogger(LOGGER_INFERENCIA)

    handlers = [h for h in logger.handlers if isinstance(h, logging.StreamHandler)]
    assert len(handlers) == 1
    assert handlers[0].stream is sys.stdout


def test_configurar_duas_vezes_nao_duplica_o_registro():
    """Handler duplicado = duas linhas por requisicao, quebrando o
    "um registro por requisicao" da secao 3.1."""
    configurar_logging()
    configurar_logging()

    logger = logging.getLogger(LOGGER_INFERENCIA)
    assert len(logger.handlers) == 1


def test_o_registro_sai_puro_sem_prefixo_do_logging():
    """A linha tem que ser JSON valido: qualquer prefixo ("INFO:...") quebraria
    o parser de quem coleta o log."""
    configurar_logging()
    logger = logging.getLogger(LOGGER_INFERENCIA)
    handler = logger.handlers[0]

    registro = logging.LogRecord(
        LOGGER_INFERENCIA, logging.INFO, __file__, 1, '{"trace_id": "x"}', None, None
    )
    assert handler.format(registro) == '{"trace_id": "x"}'


def test_nao_propaga_para_o_logger_raiz():
    """Se propagar, uma configuracao de root handler duplicaria a linha."""
    configurar_logging()
    assert logging.getLogger(LOGGER_INFERENCIA).propagate is False
