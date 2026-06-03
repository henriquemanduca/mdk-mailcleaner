# MDK Mail Cleaner

API FastAPI para receber jobs de limpeza de HTML em base64, enfileirar o processamento no Redis e publicar o resultado em uma fila Redis definida por request.

## Como funciona

1. O cliente envia um job em `POST /jobs`.
2. A API grava o job na fila Redis configurada em `REQUEST_QUEUE`.
3. Um worker em background, no mesmo serviço, consome essa fila.
4. O worker decodifica o HTML, remove tags não legíveis e extrai o texto.
5. O resultado é publicado com `RPUSH` na fila `resultQueue` enviada no request.

## Rodando com Docker

```bash
docker compose up --build
```

A API ficará disponível em:

```text
http://localhost:8000
```

Health check:

```bash
curl http://localhost:8000/health
```

## Variáveis de ambiente

| Variável | Padrão | Descrição |
| --- | --- | --- |
| `REDIS_HOST` | `redis` | Host do Redis |
| `REDIS_PORT` | `6379` | Porta do Redis |
| `REDIS_PW` | `password` | Senha do Redis. Use vazio para Redis sem senha |
| `REDIS_DB` | `0` | Database Redis |
| `REQUEST_QUEUE` | `mailcleaner:requests` | Fila Redis List usada para jobs de entrada |
| `WORKER_ENABLED` | `true` | Habilita o worker em background |
| `LOG_LEVEL` | `INFO` | Nível de log |

## Criando um job

Payload:

```json
{
  "jobId": "job-001",
  "resultQueue": "mailcleaner:results",
  "payload": {
    "emailId": "email-123",
    "folderId": "folder-456",
    "base64Content": "PGh0bWw+PGJvZHk+PHA+T2xhIG11bmRvPC9wPjxzY3JpcHQ+YWxlcnQoMSk8L3NjcmlwdD48L2JvZHk+PC9odG1sPg=="
  }
}
```

Exemplo:

```bash
curl -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "jobId": "job-001",
    "resultQueue": "mailcleaner:results",
    "payload": {
      "emailId": "email-123",
      "folderId": "folder-456",
      "base64Content": "PGh0bWw+PGJvZHk+PHA+T2xhIG11bmRvPC9wPjxzY3JpcHQ+YWxlcnQoMSk8L3NjcmlwdD48L2JvZHk+PC9odG1sPg=="
    }
  }'
```

Resposta:

```json
{
  "jobId": "job-001",
  "status": "queued"
}
```

## Consumindo resultados

Com o Compose rodando:

```bash
docker compose exec redis redis-cli -a password BRPOP mailcleaner:results 10
```

Resultado de sucesso:

```json
{
  "jobId": "job-001",
  "status": "success",
  "emailId": "email-123",
  "folderId": "folder-456",
  "base64Content": "T2xhIG11bmRv"
}
```

Resultado de erro:

```json
{
  "jobId": "job-001",
  "status": "error",
  "emailId": "email-123",
  "folderId": "folder-456",
  "errorCode": "invalid_base64",
  "message": "invalid base64 content"
}
```

## Endpoints

### `GET /health`

Valida conectividade com Redis.

### `POST /jobs`

Agenda um job de limpeza na fila configurada em `REQUEST_QUEUE`.

Campos obrigatórios:

| Campo | Descrição |
| --- | --- |
| `jobId` | Identificador do job |
| `resultQueue` | Fila Redis List onde o resultado será publicado |
| `payload.emailId` | Identificador do e-mail |
| `payload.folderId` | Identificador da pasta |
| `payload.base64Content` | HTML original codificado em base64 |
