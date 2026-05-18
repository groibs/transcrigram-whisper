# Instagram Reel Transcriber (Whisper local)

Aplicação FastAPI para transcrever Reels públicos do Instagram usando um resolvedor externo para obter a mídia e `faster-whisper` para transcrever localmente, sem usar a OpenAI API.

## Como funciona

1. O usuário cola o link do Reel.
2. O backend chama o Apify, ou outro resolvedor compatível, para resolver a mídia do Instagram.
3. O backend baixa a mídia temporariamente no servidor.
4. O servidor transcreve localmente com `faster-whisper`.
5. A interface devolve o texto.

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

## Verificando a configuração no deploy

Acesse `/health` no seu deploy para confirmar as variáveis carregadas. A resposta mostra, sem revelar tokens:

- `resolver_url_source`: `default_apify` quando a URL padrão do Apify está em uso, ou `environment` quando `INSTAGRAM_RESOLVER_URL` foi definida.
- `has_resolver_token`: `true` quando `INSTAGRAM_RESOLVER_TOKEN` está configurada.
- `whisper_model_size`: modelo carregado pelo Whisper.

Se `has_resolver_token` estiver `false`, o endpoint de transcrição retornará erro pedindo `INSTAGRAM_RESOLVER_TOKEN`.

## Observações sobre Vercel

- Depois de criar ou alterar variáveis de ambiente na Vercel, faça redeploy. Deploys já publicados não recebem automaticamente os novos valores.
- O primeiro uso pode ser mais lento porque o modelo precisa ser carregado/baixado.
- `tiny` é a opção mais leve para ambientes serverless. Modelos maiores podem ultrapassar limites de memória ou tempo.
