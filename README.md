# Instagram Reel Transcriber (Whisper local)

Versão pronta para Railway sem usar OpenAI API.

## Como funciona

1. O usuário cola o link do Reel.
2. O backend chama o Apify para resolver a mídia do Instagram.
3. O backend baixa a mídia temporariamente no servidor.
4. O servidor transcreve localmente com `faster-whisper`.
5. A interface devolve o texto.

## Variáveis de ambiente

Cadastre no Railway:

- `INSTAGRAM_RESOLVER_URL`
- `INSTAGRAM_RESOLVER_TOKEN`
- `INSTAGRAM_RESOLVER_AUTH_HEADER`
- `WHISPER_MODEL_SIZE` (`tiny` ou `base`)

Sugestão inicial:

- `WHISPER_MODEL_SIZE=tiny`

## Valores sugeridos

### INSTAGRAM_RESOLVER_URL

```https://api.apify.com/v2/acts/apify~instagram-scraper/run-sync-get-dataset-items
```

### INSTAGRAM_RESOLVER_AUTH_HEADER

```Authorization
```

### INSTAGRAM_RESOLVER_TOKEN

```Bearer apify_api_xxxxx
```

## Observações

- O primeiro uso pode ser mais lento porque o modelo precisa ser carregado/baixado.
- `tiny` é a opção mais realista para Railway simples.
- Se faltar memória no Railway, volte para `tiny`.
