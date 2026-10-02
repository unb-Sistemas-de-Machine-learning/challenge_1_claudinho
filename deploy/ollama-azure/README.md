# LLM próprio do Claudinho (Ollama numa VM da Azure)

Alternativa ao Space do Hugging Face (`deploy/ollama-space/`), que exige plano pago para
criar Spaces Docker. Aqui o Ollama roda numa máquina virtual, atrás de um proxy que exige
token, e serve a mesma API compatível com a OpenAI que a `APP/model/llm.py` já sabe chamar.

## O que está no ar

| Item | Valor |
|---|---|
| Endereço | `https://52-162-239-138.sslip.io/v1` |
| Modelo | `qwen2.5:3b` (o mesmo do Space) |
| Máquina | Azure `Standard_B2als_v2` — 2 vCPU, 4 GiB, North Central US |
| Custo | ~US$ 27/mês ligada; crédito de estudante de US$ 100 |
| Token | está no `/etc/caddy/Caddyfile`, dentro da VM |
| Acesso | `ssh -i claudinho_key.pem azureuser@52.162.239.138` |

O `sslip.io` é um DNS gratuito que resolve para o IP escrito no nome. Ele existe porque o
Caddy precisa de um domínio para emitir o certificado HTTPS; com IP puro não dá.

## Por que não está ligado na API

Medições feitas na própria VM, com uma resposta de 100 palavras (o tamanho de uma resposta
real do Claudinho):

| Caminho | Tempo |
|---|---|
| Ollama nesta VM | **17 a 24 s** |
| Gemini `gemini-3.5-flash-lite` | 2 a 3 s |
| Meta do `docs/Production/03` | < 5 s (p95) |

A variação de 17 a 24 s é a série B: ela acumula crédito de CPU quando está ociosa e perde
velocidade quando trabalha seguido. Numa apresentação, isso significa a primeira resposta
rápida e as seguintes mais lentas.

Como a `APP/model/llm.py` tenta o LLM próprio **antes** do Gemini, preencher `LLM_BASE_URL`
faria toda checagem passar a demorar isso. Por isso a variável **não está cadastrada na
Vercel**, e o Gemini segue como provedor.

Duas saídas, para o grupo decidir:

1. **Deixar como está.** A VM fica no ar e o Ollama é demonstrado à parte. O argumento de
   não depender de provedor externo continua verdadeiro e demonstrável.
2. **Inverter a ordem dos provedores**: Gemini primeiro, Ollama quando `dados_sensiveis`
   for verdadeiro — o caso em que `docs/Ethics/02` proíbe mandar dado de saúde para fora.
   Aí a espera longa aparece só numa fração das consultas, e em troca o dado sensível nunca
   sai. Exige mudança na `APP/model/llm.py`.

## Ligar na API, se o grupo decidir

Na Vercel, em Settings → Environment Variables, e depois **Redeploy**:

    LLM_BASE_URL = https://52-162-239-138.sslip.io/v1
    LLM_API_KEY  = <token do /etc/caddy/Caddyfile>

## Manutenção

**Desalocar quando não estiver usando.** No portal, botão **Parar**, aceitando desalocar.
Máquina parada mas alocada continua sendo cobrada.

**Ver se está no ar:**

    curl -s -o /dev/null -w "%{http_code}\n" https://52-162-239-138.sslip.io/v1/models          # 401
    curl -s -o /dev/null -w "%{http_code}\n" -H "Authorization: Bearer <token>" \
      https://52-162-239-138.sslip.io/v1/models                                                 # 200

O 401 sem token é parte do teste: se ele responder 200, o Ollama está aberto na internet.
Ele não tem autenticação própria, então quem alcança a porta usa a máquina.

**Trocar o token:** gere com `openssl rand -hex 24`, edite o `/etc/caddy/Caddyfile`, rode
`sudo systemctl restart caddy` e atualize a `LLM_API_KEY` na Vercel.

**Logs:** `sudo journalctl -u ollama -n 50` e `sudo journalctl -u caddy -n 50`.

## Como foi montado (para refazer em outra conta)

1. **Conta de estudante** em azure.microsoft.com/free/students: US$ 100, sem cartão.
2. **VM**: Ubuntu Server 24.04 LTS **x64**, tamanho com 2 vCPU e ≥ 4 GiB, portas **22** e
   **443** liberadas — **nunca a 11434**, que é a do Ollama, sem autenticação.
3. **Ollama**, com a mesma configuração do Space (contexto de 8192 porque o prompt do RAG
   passa de 2 mil tokens; modelo sempre na memória, senão são ~10 s a mais por pergunta;
   uma geração por vez, porque com 2 vCPU duas ao mesmo tempo só deixam as duas lentas):

       curl -fsSL https://ollama.com/install.sh | sh
       sudo mkdir -p /etc/systemd/system/ollama.service.d
       sudo tee /etc/systemd/system/ollama.service.d/claudinho.conf > /dev/null <<'EOF'
       [Service]
       Environment="OLLAMA_CONTEXT_LENGTH=8192"
       Environment="OLLAMA_KEEP_ALIVE=-1"
       Environment="OLLAMA_NUM_PARALLEL=1"
       EOF
       sudo systemctl daemon-reload && sudo systemctl restart ollama
       ollama pull qwen2.5:3b

4. **Proxy com token** (o Ollama não tem autenticação; sem isto, qualquer um usa a máquina):

       sudo apt update && sudo apt install -y caddy
       sudo tee /etc/caddy/Caddyfile > /dev/null <<'EOF'
       <IP-COM-TRACOS>.sslip.io {
         @sem_token not header Authorization "Bearer <TOKEN>"
         respond @sem_token 401
         reverse_proxy localhost:11434 {
           header_up Host {upstream_hostport}
         }
       }
       EOF
       sudo systemctl restart caddy

   O `header_up Host` é obrigatório: o Ollama recusa requisição cujo `Host` não seja local
   (responde 403), e sem essa linha o proxy repassa o domínio externo.

### Erros que aparecem no caminho

| Sintoma | Causa |
|---|---|
| `NotAvailableForSubscription` no tamanho da VM | Conta de estudante não tem aquela família naquela região |
| `RequestDisallowedByAzure` ao criar | A assinatura só permite algumas regiões. Veja quais com: `az policy assignment list --disable-scope-strict-match --query "[?displayName=='Allowed resource deployment regions'].parameters"` |
| 401 mesmo com o token certo | Espaço perdido entre `Bearer` e o token ao colar no Caddyfile |
| 403 com o token certo | Falta o `header_up Host {upstream_hostport}` |
