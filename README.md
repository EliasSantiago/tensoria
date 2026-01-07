# Tensoria - Open Source LLM API Infrastructure

API de inferência de LLMs open source para a plataforma OrkestrAI.

## 🏗️ Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                      Tensoria                                │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   ┌─────────────┐         ┌─────────────────────────────┐   │
│   │   Client    │ ──────▶ │  FastAPI Backend (API)     │   │
│   └─────────────┘         │  - /v1/chat/completions    │   │
│                           │  - /v1/completions         │   │
│                           │  - /v1/models              │   │
│                           │  - /health                 │   │
│                           └───────────┬─────────────────┘   │
│                                       │                      │
│                                       ▼                      │
│                           ┌─────────────────────────────┐   │
│                           │       Ollama Service        │   │
│                           │  (LLM Inference Engine)     │   │
│                           └───────────┬─────────────────┘   │
│                                       │                      │
│                                       ▼                      │
│                           ┌─────────────────────────────┐   │
│                           │   Persistent Volume         │   │
│                           │   (Downloaded Models)       │   │
│                           └─────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### 1. Subir os containers

```bash
cd tensoria
docker compose up -d
```

> ⚠️ **IMPORTANTE**: Nenhum modelo é baixado automaticamente!

### 2. Instalar modelos manualmente

```bash
# Mistral (recomendado para começar - ~4GB)
docker exec -it tensoria-ollama ollama pull mistral

# DeepSeek Coder (bom para código)
docker exec -it tensoria-ollama ollama pull deepseek-coder:6.7b

# Qwen (bom custo-benefício)
docker exec -it tensoria-ollama ollama pull qwen:7b
```

### 3. Verificar status

```bash
# Health check
curl http://localhost:8002/health

# Listar modelos instalados
curl http://localhost:8002/v1/models
```

## 📡 Endpoints da API

### Chat Completions (OpenAI-compatible)

```bash
curl -X POST http://localhost:8002/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "mistral",
    "messages": [
      {"role": "user", "content": "Olá, como vai?"}
    ],
    "temperature": 0.7
  }'
```

### Text Completions (Legacy)

```bash
curl -X POST http://localhost:8002/v1/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "mistral",
    "prompt": "O céu é",
    "max_tokens": 50
  }'
```

### List Models

```bash
curl http://localhost:8002/v1/models
```

### Health Check

```bash
curl http://localhost:8002/health
```

## 🔒 Segurança

O Tensoria implementa múltiplas camadas de segurança:

### 1. API Key Authentication

Todas as requisições (exceto `/health`) requerem o header `X-API-Key`:

```bash
# Gerar uma API Key segura
python -c "import secrets; print(f'tensoria_{secrets.token_urlsafe(48)}')"

# Configurar no .env do servidor
API_KEY=tensoria_sua_chave_aqui
```

**Exemplo de requisição autenticada:**

```bash
curl -X POST https://tensoria.orkestrai.com.br/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "X-API-Key: tensoria_sua_chave_aqui" \
  -d '{"model": "mistral", "messages": [{"role": "user", "content": "Olá!"}]}'
```

### 2. IP Allowlist (Nginx)

O Nginx está configurado para aceitar apenas requisições do servidor orkestrai-api:

```nginx
allow 34.42.168.19;  # orkestrai-api
deny all;
```

### 3. Documentação Desabilitada em Produção

Quando `API_KEY` está configurada, os endpoints `/docs`, `/redoc` e `/openapi.json` são desabilitados automaticamente.

## ⚙️ Configuração

Variáveis de ambiente disponíveis (arquivo `.env`):

```env
# Segurança (OBRIGATÓRIO em produção!)
API_KEY=tensoria_sua_chave_aqui

# Portas
OLLAMA_PORT=11434
API_PORT=8002

# Ollama
OLLAMA_TIMEOUT=120
OLLAMA_KEEP_ALIVE=5m
OLLAMA_NUM_PARALLEL=1

# API
LOG_LEVEL=INFO
DEFAULT_MODEL=mistral
MAX_TOKENS=4096
DEFAULT_TEMPERATURE=0.7
```

## 🤖 Modelos Suportados

| Modelo | Tamanho | Uso Recomendado |
|--------|---------|-----------------|
| `mistral` | ~4GB | Uso geral, chat |
| `mistral:7b-instruct` | ~4GB | Instruções precisas |
| `deepseek-coder` | ~4GB | Código |
| `deepseek-coder:6.7b` | ~4GB | Código (equilibrado) |
| `deepseek-coder:33b` | ~20GB | Código (alta qualidade) |
| `qwen:7b` | ~4GB | Uso geral, multilíngue |
| `qwen2:7b` | ~4GB | Versão mais recente |

## 🔧 Comandos Úteis

```bash
# Ver logs da API
docker compose logs -f api

# Ver logs do Ollama
docker compose logs -f ollama

# Parar tudo
docker compose down

# Remover volumes (apaga modelos baixados)
docker compose down -v

# Ver modelos instalados no Ollama
docker exec -it tensoria-ollama ollama list

# Remover um modelo específico
docker exec -it tensoria-ollama ollama rm mistral
```

## 🔮 Preparação para Futuro

Esta arquitetura foi projetada para permitir:

- [ ] Roteamento inteligente de modelos
- [ ] Fallback entre modelos
- [ ] Integração com LiteLLM
- [ ] Uso como provider interno do OrkestrAI
- [ ] Escalonamento por GPU/VRAM

## 📁 Estrutura do Projeto

```
tensoria/
├── docker-compose.yml    # Configuração dos serviços
├── Dockerfile            # Build da API
├── requirements.txt      # Dependências Python
├── README.md             # Esta documentação
└── api/
    ├── __init__.py
    ├── main.py           # Entry point FastAPI
    ├── config.py         # Configurações
    ├── models.py         # Schemas Pydantic
    ├── ollama_client.py  # Cliente HTTP Ollama
    └── routes/
        ├── __init__.py
        ├── chat.py       # /v1/chat/completions
        ├── completions.py # /v1/completions
        ├── models.py     # /v1/models
        └── health.py     # /health
```

## 🛡️ Produção

Para deploy em GCP:

1. Configurar GPU (se disponível)
2. Ajustar variáveis de ambiente
3. Configurar reverse proxy (nginx)
4. Implementar autenticação
5. Configurar monitoramento

---

**OrkestrAI** - Infraestrutura de IA Open Source
