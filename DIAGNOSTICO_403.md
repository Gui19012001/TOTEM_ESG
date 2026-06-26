# Correção do erro 403 do Gemini

O APK recebia resposta HTTP 403 da API do Gemini. Isso comprova que o tablet possui internet; portanto, o texto "Offline" era enganoso.

Foram corrigidos estes pontos:

1. O modelo antigo `gemini-1.5-flash` foi substituído por `gemini-2.5-flash`.
2. A chave passou a ser enviada no cabeçalho oficial `x-goog-api-key`.
3. O workflow agora falha se algum Secret estiver vazio ou não for injetado.
4. O aplicativo agora mostra o detalhe real devolvido pela API.
5. Erros HTTP de autenticação aparecem como `Erro IA`, e não como `Offline`.
6. A versão do APK foi alterada para 5.0.1.

## Passos obrigatórios no GitHub

1. No Google AI Studio, crie uma chave nova. As chaves novas são do tipo Auth.
2. Substitua o Secret `GEMINI_API_KEY` pelo novo valor.
3. No GitHub, abra Actions > Build APK > Run workflow.
4. Aguarde terminar e baixe o novo Artifact.
5. Desinstale a versão antiga do tablet e instale o APK novo.

Observação: alterar um Secret no GitHub não recompila automaticamente o APK. É obrigatório executar novamente o workflow.
