# 🛡️ Sistema de Gestão de Backups - NOC Dashboard (Clube Naval)

![Status](https://img.shields.io/badge/Status-Produção-success)
![Version](https://img.shields.io/badge/Version-Auto--Deploy-blue)
![Docker](https://img.shields.io/badge/Docker-Conteinerizado-2496ED?logo=docker&logoColor=white)
![Python](https://img.shields.io/badge/Python-Flask-3776AB?logo=python&logoColor=white)
![MySQL](https://img.shields.io/badge/Database-MySQL%208.0-4479A1?logo=mysql&logoColor=white)

Painel de monitoramento centralizado (NOC - *Network Operations Center*) de nível Enterprise, desenvolvido para auditar e gerenciar rotinas de backup de múltiplos servidores físicos, máquinas virtuais e containers. 

O sistema possui uma arquitetura baseada em microsserviços (Docker), composta por uma **API RESTful (Flask)** e um banco de dados **MySQL**, além de um pipeline de CI/CD automatizado via **GitHub Actions**.

---

## ✨ Funcionalidades Principais

* 🖥️ **Monitoramento em Tempo Real:** Painel de NOC com atualização silenciosa assíncrona (AJAX), ideal para exibição em TVs.
  
* 💽 **Micro-HDDs Virtuais (UI Avançada):** O painel lê dinamicamente a topologia de discos físicos (`/dev/*`) dos servidores de origem e os desenha como "Hard Disks" em puro CSS, com simulação de barramento SATA, LED de atividade e preenchimento condicional de acordo com o armazenamento.
  
* 📊 **Histórico e Dashboards Analíticos:** Telas de relatórios com paginação, filtros avançados e gráficos renderizados via *Chart.js*.
  
* 🐳 **Arquitetura 100% Docker:** Aplicação e banco de dados isolados em containers, garantindo portabilidade, resiliência e facilidade de deploy.
  
* 🚀 **CI/CD Integrado:** Pipeline configurado no GitHub Actions para build e publicação automática de imagens no GHCR (*GitHub Container Registry*).
  
* ⚙️ **Integração Universal:** Agentes em Bash que interceptam comandos do sistema (`df`, `rsync`, `tar`) e enviam *payloads* em JSON para a API.

---

## 🏗️ Arquitetura e Componentes

O ambiente é orquestrado via `docker-compose.yml` e conta com os seguintes serviços:

1. **`db` (MySQL 8.0):** Armazena os logs de backup e a topologia em JSON dos discos dos servidores. Possui persistência mapeada via volumes.
   
3. **`web` (Flask App):** Container da aplicação Python (construído a partir do `Dockerfile` baseado em `python:3.11-slim`), expondo a API na porta `5000`.
   
5. **Agentes (Scripts Bash):** Executados remotamente via `cron` nos servidores da infraestrutura, enviando dados para a API do container `web`.

---

## 🚀 Como Fazer o Deploy (Ambiente Docker)

### Pré-requisitos
* Docker Engine
* Docker Compose

### Instalação Rápida
1. Clone o repositório:

```
git clone https://github.com/clubenaval/backups.git
cd backups
```

2. Ajuste as credenciais e variáveis no arquivo `docker-compose.yml` (se necessário):
* `MYSQL_ROOT_PASSWORD`, `MYSQL_USER`, `MYSQL_PASSWORD`
* Certifique-se de que o diretório de persistência do volume do banco (`/srv/bkp/db`) exista ou altere para um volume nomeado padrão.

3. Suba a stack em modo *detached*:
```
docker-compose up -d --build
```

A aplicação estará disponível no endereço `http://IP_DO_SERVIDOR:5000`. O banco de dados e as tabelas são provisionados automaticamente na primeira inicialização do container Python.

---

## 🔄 Fluxo de Trabalho e CI/CD (GitHub Actions)

Este repositório possui um fluxo de deploy contínuo integrado. Sempre que uma nova funcionalidade for homologada, utilize o script de deploy automatizado.

### Como lançar uma nova versão:

O script `deploy.sh` foi criado para gerenciar o versionamento de forma segura.

1. Trabalhe as suas alterações na branch `dev`.
2. Quando estiver pronto, execute o script de deploy na raiz do projeto:

```
./deploy.sh
```

3. **O que o script faz?**
* Verifica o status das suas modificações.
* Realiza o *Merge* automático da branch `dev` para a `main`.
* Calcula de forma inteligente o versionamento semântico (*SemVer*) da próxima Tag (Ex: `v1.0.5` -> `v1.0.6`).
* Realiza o *Push* das tags, engatilhando o **GitHub Actions**.

O *workflow* do Actions irá buildar a imagem Docker e publicá-la no registro **GHCR** (GitHub Container Registry) com as devidas tags de versão.

---

## 📡 Integração de Novos Servidores (Bash)

Para adicionar um novo servidor ao NOC, inclua a seguinte lógica no script de backup local:

1. **Geração Mágica da Topologia (Discos Físicos):**
Use o comando `awk` abaixo para mapear apenas discos locais válidos (`/dev/*`) e transformá-los num JSON inline compatível com a API:

```
DISCOS_JSON="["$(df -hP | awk 'NR>1 && $1 ~ /^\/dev\// { printf "{\"fs\":\"%s\", \"uso\":\"%s\", \"mount\":\"%s\", \"size\":\"%s\"},", $1, $5, $6, $2 }' | sed 's/,$//')"]"
```

2. **Envio à API via cURL:**
Crie um payload estruturado e dispare o POST:

```
API_URL="http://IP_DO_DASHBOARD:5000/api/backup"

cat <<EOF > /tmp/payload.json
{
    "servidor": "$(hostname)",
    "tipo_backup": "FULL",
    "status": "SUCESSO",
    "espaco_livre_origem": "100GB",
    "uso_percentual_origem": "45%",
    "espaco_livre_destino": "2TB",
    "uso_percentual_destino": "80%",
    "diretorio_gerado": "/mnt/nas/bkp",
    "proximo_a_expirar": "2026-03-10",
    "data_inicio": "$(date +'%d/%m/%Y %H:%M')",
    "data_fim": "$(date +'%d/%m/%Y %H:%M')",
    "diretorio_origem": "/dados",
    "discos_origem": $DISCOS_JSON
}
EOF

curl -s -X POST -H "Content-Type: application/json" -d @/tmp/payload.json "$API_URL"
rm -f /tmp/payload.json
```

---

## 👨‍💻 Autor

Desenvolvido e arquitetado por **Henrique Fagundes**.

🌐 [www.henrique.tec.br](https://www.henrique.tec.br)

🏢 Assessoria de TI - Clube Naval

*(Este software é de uso interno e foi estruturado sob os preceitos de observabilidade e confiabilidade de infraestrutura).*
