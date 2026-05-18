# Instagram Reel Transcriber (Whisper local)

Aplicação FastAPI para transcrever Reels públicos do Instagram usando um resolvedor externo para obter a mídia e `faster-whisper` para transcrever localmente, sem usar a OpenAI API.

## Como funciona

1. O usuário cola o link do Reel.
2. O backend chama o Apify, ou outro resolvedor compatível, para resolver a mídia do Instagram.
3. O backend baixa a mídia temporariamente no servidor.
4. O servidor transcreve localmente com `faster-whisper`.
5. A interface devolve o texto.

## Resolvendo o erro `INSTAGRAM_RESOLVER_TOKEN não configurada`

Esse erro significa que o deploy está usando o resolvedor padrão do Apify, mas a variável `INSTAGRAM_RESOLVER_TOKEN` não chegou ao runtime da aplicação.

Para corrigir na Vercel:

1. Acesse **Vercel > Project Settings > Environment Variables**.
2. Crie a variável `INSTAGRAM_RESOLVER_TOKEN` nos ambientes em que você usa o app, normalmente **Production** e **Preview**.
3. Use o valor completo com o prefixo `Bearer`, por exemplo:

   ```env
   INSTAGRAM_RESOLVER_TOKEN=Bearer apify_api_xxxxx
   ```

4. Salve a variável e faça um **Redeploy**. Deploys antigos não recebem variáveis novas automaticamente.
5. Abra `https://SEU_DOMINIO/health` ou `https://SEU_DOMINIO/api/config-check` e confirme que `has_resolver_token` está `true` e que `pending` está vazio.

> Importante: não coloque aspas no valor da variável na Vercel e não comite tokens reais no repositório.

## Variáveis de ambiente

Configure estas variáveis no provedor de hospedagem, por exemplo em **Vercel > Project Settings > Environment Variables**, e faça um novo deploy depois de salvar.

| Variável | Obrigatória? | Valor sugerido |
| --- | --- | --- |
| `INSTAGRAM_RESOLVER_TOKEN` | Sim, ao usar Apify | `Bearer apify_api_xxxxx` |
| `INSTAGRAM_RESOLVER_URL` | Opcional | `https://api.apify.com/v2/acts/apify~instagram-scraper/run-sync-get-dataset-items` |
| `INSTAGRAM_RESOLVER_AUTH_HEADER` | Opcional | `Authorization` |
| `WHISPER_MODEL_SIZE` | Opcional | `tiny` |

A aplicação usa o endpoint do Apify acima como padrão quando `INSTAGRAM_RESOLVER_URL` não está definida. Por isso, no deploy básico do Vercel você precisa adicionar pelo menos:

```env
INSTAGRAM_RESOLVER_TOKEN=Bearer apify_api_xxxxx
WHISPER_MODEL_SIZE=tiny
```

Se você usar outro resolvedor externo, defina `INSTAGRAM_RESOLVER_URL` e ajuste `INSTAGRAM_RESOLVER_AUTH_HEADER`/`INSTAGRAM_RESOLVER_TOKEN` conforme a API desse serviço.

## Checklist de configuração pendente

Use este checklist antes de testar uma transcrição real:

- [ ] `INSTAGRAM_RESOLVER_TOKEN` existe no ambiente correto da Vercel (**Production**, **Preview** e/ou **Development**).
- [ ] O valor de `INSTAGRAM_RESOLVER_TOKEN` começa com `Bearer ` quando o resolvedor é o Apify.
- [ ] Depois de salvar as variáveis, foi feito um **Redeploy** do projeto.
- [ ] `/health` retorna `configuration_ok: true`, `has_resolver_token: true` e `pending: []`.
- [ ] `/api/config-check` não lista pendências e só mostra avisos esperados.
- [ ] O Reel usado no teste é público e o link começa com `https://www.instagram.com/reel/`, `/p/` ou `/tv/`.
- [ ] `WHISPER_MODEL_SIZE` está como `tiny` no primeiro deploy para reduzir risco de timeout/memória em ambiente serverless.

## Verificando a configuração no deploy

Acesse `/health` no seu deploy para confirmar as variáveis carregadas. A resposta mostra, sem revelar tokens:

- `configuration_ok`: `true` quando não há pendências bloqueantes.
- `resolver_url_source`: `default_apify` quando a URL padrão do Apify está em uso, ou `environment` quando `INSTAGRAM_RESOLVER_URL` foi definida.
- `has_resolver_token`: `true` quando `INSTAGRAM_RESOLVER_TOKEN` está configurada com algum valor não vazio.
- `pending`: lista de configurações obrigatórias que ainda faltam.
- `warnings`: lista de configurações suspeitas que podem impedir a transcrição.
- `whisper_model_size`: modelo carregado pelo Whisper.

Também existe `/api/config-check`, que devolve um diagnóstico mais detalhado da configuração sem revelar o token.

Se `has_resolver_token` estiver `false`, o endpoint de transcrição retornará erro pedindo `INSTAGRAM_RESOLVER_TOKEN`.

## Observações sobre Vercel

- Depois de criar ou alterar variáveis de ambiente na Vercel, faça redeploy. Deploys já publicados não recebem automaticamente os novos valores.
- O primeiro uso pode ser mais lento porque o modelo precisa ser carregado/baixado.
- `tiny` é a opção mais leve para ambientes serverless. Modelos maiores podem ultrapassar limites de memória ou tempo.
- Se a transcrição falhar por limite de tempo ou memória mesmo com as variáveis corretas, rode via Docker em um provedor com processo persistente ou aumente os limites do ambiente.

## Desenvolvimento local

1. Crie um ambiente virtual e instale as dependências:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Copie `.env.example` para `.env` e preencha seu token real.
3. Exporte as variáveis do `.env` antes de iniciar, ou defina-as no shell.
4. Rode a aplicação:

   ```bash
   uvicorn app.main:app --reload
   ```
