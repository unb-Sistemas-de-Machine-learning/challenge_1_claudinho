"""Script para teste interativo da IA via terminal.

Uso:
  python testar_interativo.py "agua com limao queima gordura?"
ou apenas:
  python testar_interativo.py
"""

import sys

from fastapi.testclient import TestClient

from APP.config import obter_settings
from APP.main import app


def testar(texto: str):
    obter_settings.cache_clear()
    client = TestClient(app)

    print("\n" + "=" * 60)
    print(f"ENTRADA DO USUARIO: {texto}")
    print("=" * 60)

    resposta = client.post(
        "/api/v1/check-claim",
        headers={"Authorization": "Bearer token-teste-interativo"},
        json={"input_type": "text", "text": texto},
    )

    if resposta.status_code != 200:
        print(f"Erro na requisicao ({resposta.status_code}):", resposta.text)
        return

    dados = resposta.json()
    print(f"Alegacao Canonica: {dados.get('canonical_claim')}")
    print(f"Veredito:          {dados.get('verdict').upper()}")
    print(f"Risk Score:        {dados.get('risk_score')} (Nivel: {dados.get('risk_level')})")
    print(f"Modelo:            {dados.get('model_version')}")
    print(f"Tempo de Resposta: {dados.get('latency_ms')} ms")
    print("\nRESPOSTA GERADA:")
    print(dados.get("answer"))

    fontes = dados.get("sources", [])
    print(f"\nFONTES CIENTIFICAS DO SUPABASE CONSULTADAS ({len(fontes)}):")
    if not fontes:
        print("  (Nenhuma fonte retornada - caso de recusa segura ou sem evidencia)")
    for i, f in enumerate(fontes, 1):
        print(f"  {i}. {f.get('title')}")
        print(f"     Autores:   {f.get('authors')}")
        print(f"     Periodico: {f.get('journal')} ({f.get('published_at')})")
        print(f"     DOI:       {f.get('doi')}")

    print("\nDISCLAIMER:")
    print(dados.get("disclaimer"))
    print("=" * 60 + "\n")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        entrada = " ".join(sys.argv[1:])
        testar(entrada)
    else:
        print("Modo Interativo - Digite sua duvida nutricional (ou 'sair' para encerrar):")
        while True:
            try:
                pergunta = input("\nPergunta: ").strip()
                if not pergunta or pergunta.lower() in ("sair", "exit", "quit"):
                    break
                testar(pergunta)
            except (KeyboardInterrupt, EOFError):
                break
