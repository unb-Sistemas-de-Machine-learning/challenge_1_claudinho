import APP.model.database as database


def test_importar_o_modulo_nao_cria_client():
    """O client so pode ser criado sob demanda: importar o modulo em um ambiente
    sem credenciais (CI, por exemplo) nao pode quebrar a aplicacao.

    O modulo ja foi importado no topo do arquivo; se a criacao fosse feita no
    import, o cache do lru_cache ja estaria populado neste ponto.
    """
    assert database.obter_supabase.cache_info().currsize == 0


def test_obter_supabase_usa_as_credenciais_do_settings(monkeypatch):
    database.obter_supabase.cache_clear()
    monkeypatch.setattr(database, "create_client", lambda url, key: {"url": url, "key": key})

    client = database.obter_supabase()

    assert client["url"] == "https://teste.supabase.co"
    assert client["key"] == "chave-de-teste"
    database.obter_supabase.cache_clear()


def test_obter_supabase_reaproveita_o_mesmo_client(monkeypatch):
    database.obter_supabase.cache_clear()
    monkeypatch.setattr(database, "create_client", lambda url, key: object())

    assert database.obter_supabase() is database.obter_supabase()
    database.obter_supabase.cache_clear()
