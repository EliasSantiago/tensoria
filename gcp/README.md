# Deploy do Tensoria no Google Cloud Run

Este guia explica como fazer o deploy do Tensoria no Cloud Run usando a arquitetura de **Sidecar** (API + Ollama no mesmo serviço) e **GCS FUSE** para persistência dos modelos.

## 📋 Pré-requisitos

1.  Google Cloud CLI (`gcloud`) instalado e autenticado.
2.  Um projeto no Google Cloud.
3.  APIs habilitadas: Cloud Run, Cloud Build, Artifact Registry.

## 🚀 Passo a Passo

### 1. Configurar Variáveis

Defina as variáveis do seu projeto:

```bash
export PROJECT_ID="seu-projeto-id"
export REGION="us-central1"
export BUCKET_NAME="${PROJECT_ID}-tensoria-models"
export API_KEY="sua-chave-api-gerada-aqui"
```

### 2. Criar Bucket para Modelos

O Ollama precisa de um lugar persistente para salvar os modelos (que são grandes). Usaremos um bucket GCS.

```bash
# Criar bucket
gcloud storage buckets create gs://${BUCKET_NAME} --location=${REGION}

# (Opcional) Configurar ciclo de vida ou classe de armazenamento se desejar economizar
```

### 3. Build e Push da Imagem da API

```bash
# Habilitar Artifact Registry API
gcloud services enable artifactregistry.googleapis.com cloudbuild.googleapis.com run.googleapis.com

# Submeter build para o Google Cloud Build
# Execute este comando na raiz do projeto 'tensoria'
gcloud builds submit --tag gcr.io/${PROJECT_ID}/tensoria-api:latest .
```

### 4. Preparar o Arquivo de Serviço

O arquivo `gcp/service.yaml` precisa ter as variáveis substituídas. Você pode usar `envsubst` ou editar manualmente.

```bash
# Usando envsubst (se disponível)
envsubst < gcp/service.yaml > gcp/service-deployed.yaml

# OU edite manualmente gcp/service.yaml substituindo:
# ${PROJECT_ID} -> seu ID do projeto
# ${API_KEY} -> sua chave API
# ${BUCKET_NAME} -> nome do bucket criado
```

### 5. Deploy no Cloud Run

```bash
gcloud run services replace gcp/service-deployed.yaml --region ${REGION}
```

### 6. Configurar Permissões

A conta de serviço padrão do Cloud Run precisa de permissão para ler/escrever no bucket.

```bash
# Obter a conta de serviço padrão
SERVICE_ACCOUNT=$(gcloud run services describe tensoria --region ${REGION} --format 'value(spec.template.spec.serviceAccountName)')

# Se retornar vazio, é a default compute service account:
# SERVICE_ACCOUNT="${PROJECT_ID}-compute@developer.gserviceaccount.com"

# Dar permissão de Storage Admin (ou Storage Object Admin) no bucket
gcloud storage buckets add-iam-policy-binding gs://${BUCKET_NAME} \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/storage.objectAdmin"
```

### 7. Instalar Modelos (Primeira Execução)

Como o bucket começa vazio, você precisa "instalar" os modelos. Você pode fazer isso chamando a API do Ollama através da sua API (se tiver endpoint para isso) ou, mais fácil, rodando um job temporário ou usando a API do Tensoria.

O Tensoria não tem endpoint de "pull" exposto publicamente por segurança, mas você pode usar o comando `curl` na sua máquina local apontando para a URL do Cloud Run (se tiver autenticação) ou usar um Job do Cloud Run.

**Método Recomendado (Via API Tensoria):**
A API do Tensoria expõe endpoints do Ollama internamente? Não diretamente.
Você precisará adicionar um endpoint de "pull" na API do Tensoria ou usar um script de inicialização.

**Solução Alternativa:**
Rodar o Ollama localmente, baixar os modelos, e fazer upload da pasta `~/.ollama` para o bucket `gs://${BUCKET_NAME}`.

```bash
# Localmente
ollama pull mistral

# Copiar para o bucket
gcloud storage cp -r ~/.ollama/* gs://${BUCKET_NAME}/
```

Isso é o mais rápido para popular o bucket!

## ⚠️ Considerações de Performance

O Cloud Run padrão usa **CPU**. A inferência de LLMs em CPU pode ser lenta (alguns tokens por segundo).
Para produção de alta performance, considere:
1.  **Cloud Run for GPUs** (Preview - requer configuração especial).
2.  **GKE Autopilot** com GPUs.
3.  **VM (Compute Engine)** com GPU (T4/L4) - **Recomendado para custo-benefício**.
