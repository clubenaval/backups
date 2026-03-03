# 🛡️ Sistema de Gestão de Backups - NOC Dashboard (Clube Naval)

![Status](https://img.shields.io/badge/Status-Produção-success)
![Version](https://img.shields.io/badge/Version-1.0.0-blue)
![Python](https://img.shields.io/badge/Python-3.x-3776AB?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-Web%20Framework-000000?logo=flask&logoColor=white)
![Bash](https://img.shields.io/badge/Bash-Scripts-4EAA25?logo=gnu-bash&logoColor=white)

Um painel de monitoramento (NOC - *Network Operations Center*) de nível Enterprise desenvolvido para gerenciar, auditar e monitorar rotinas de backup de múltiplos servidores físicos, máquinas virtuais e containers. 

O sistema é composto por uma **API RESTful em Python (Flask)** que recebe telemetria dos servidores em tempo real, e um **Frontend Responsivo** que exibe o status das cópias, alertas de falhas e gráficos de ocupação de discos rígidos em formato de hardware virtual.

---

## ✨ Funcionalidades Principais

* 🖥️ **Monitoramento em Tempo Real (NOC):** Painel otimizado para TVs e monitores grandes, com atualização silenciosa via AJAX (sem *refresh* de tela).
* 💽 **Miniaturas Inteligentes de Hard Disks:** Leitura nativa e em tempo real dos discos físicos (`/dev/*`) da origem, exibindo uso de armazenamento através de "micro-HDDs" desenhados em puro CSS com animações de leitura/escrita e Tooltips de contexto.
* 📊 **Histórico e Relatórios:** Tabela paginada com buscas avançadas (filtros por servidor, data, status e tipo de backup).
* 📈 **Dashboards Gerenciais:** Gráficos interativos (via *Chart.js*) mostrando a evolução temporal de sucessos vs falhas.
* 🔌 **API Universal:** Recebimento de *payloads* em JSON facilmente integráveis a qualquer script Shell, Python ou rotina de Cron.
* 🛡️ **Tolerância a Múltiplos Destinos:** Suporte para scripts que enviam dados para múltiplos *storages* simultaneamente (Ex: NAS Local, NAS Remoto e Amazon S3).

---

## 🏗️ Arquitetura do Sistema

O sistema opera no modelo **Cliente-Servidor (Agente -> API)**:

1. **Agentes (Scripts Bash):** Executados via `cron` nos servidores de origem. Compactam, transferem os arquivos (`rsync`, `tar`, `rclone`, `docker`), processam a saída do comando `df -hP` e fazem um `POST` em formato JSON para a API.
2. **Backend (Python/Flask):** Recebe o JSON, valida e insere no banco de dados MySQL via SQLAlchemy.
3. **Database (MySQL):** Armazena toda a telemetria, histórico de execuções e strings JSON correspondentes à topologia de discos físicos de cada servidor.
4. **Frontend (Jinja2/HTML/CSS):** Renderiza o Dashboard NOC consumindo as informações do banco de dados.

---

## 🚀 Como Executar o Projeto (Backend)

### Pré-requisitos
* Python 3.8+
* Servidor MySQL / MariaDB
* Pip e Virtualenv (Recomendado)

### 1. Clonando o Repositório
```bash
git clone [https://github.com/seu-usuario/backups-clubenaval.git](https://github.com/seu-usuario/backups-clubenaval.git)
cd backups-clubenaval

```

### 2. Configurando o Ambiente e Variáveis

Crie um ambiente virtual e instale as dependências listadas no `requirements.txt`:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

```

Defina as variáveis de ambiente para conexão com o banco de dados. Você pode exportá-las diretamente no terminal ou usar um arquivo `.env`:

```bash
export DB_USER="seu_usuario_mysql"
export DB_PASSWORD="sua_senha_mysql"
export DB_HOST="localhost"
export DB_NAME="backups_db"
export APP_VERSION="v1.0.0-PROD"

```

### 3. Iniciando a Aplicação

O sistema criará a tabela `backup_logs` automaticamente na primeira execução, caso não exista.

```bash
python app.py

```

A aplicação estará disponível em `http://0.0.0.0:5000`.

---

## 📡 Integração com Servidores (Cliente Bash)

Para que um servidor reporte ao Dashboard, basta incluir a função `enviar_dashboard()` no seu script de backup.

O "pulo do gato" deste sistema é o comando `awk` que captura magicamente todos os discos físicos do servidor (`/dev/`) ignorando compartilhamentos de rede (NFS/SMB) e partições temporárias (`tmpfs`), gerando um JSON perfeito para os "micro-HDDs" da tela principal.

### Exemplo de Implementação em Script Bash:

```bash
#!/bin/bash

API_URL="http://IP_DO_DASHBOARD:5000/api/backup"

enviar_dashboard() {
    local status="$1"
    local espaco_origem="$2"
    local uso_origem="$3"
    local espaco_destino="$4"
    local uso_destino="$5"
    local dir_gerado="$6"
    local expirar="$7"
    local d_inicio="$8"
    local d_fim="$9"
    local d_origem="${10}"
    local discos="${11}"

    cat <<EOF > /tmp/payload_bkp.json
{
    "servidor": "$(hostname | cut -d. -f1)",
    "tipo_backup": "FULL",
    "status": "$status",
    "espaco_livre_origem": "$espaco_origem",
    "uso_percentual_origem": "$uso_origem",
    "espaco_livre_destino": "$espaco_destino",
    "uso_percentual_destino": "$uso_destino",
    "diretorio_gerado": "$dir_gerado",
    "proximo_a_expirar": "$expirar",
    "data_inicio": "$d_inicio",
    "data_fim": "$d_fim",
    "diretorio_origem": "$d_origem",
    "discos_origem": $discos
}
EOF
    curl -s -X POST -H "Content-Type: application/json" -d @/tmp/payload_bkp.json "$API_URL"
    rm -f /tmp/payload_bkp.json
}

# 1. CAPTURAR OS DISCOS DA MÁQUINA EM JSON
DISCOS_JSON="["$(df -hP | awk 'NR>1 && $1 ~ /^\/dev\// { printf "{\"fs\":\"%s\", \"uso\":\"%s\", \"mount\":\"%s\", \"size\":\"%s\"},", $1, $5, $6, $2 }' | sed 's/,$//')"]"

# 2. AVISAR O INÍCIO AO DASHBOARD
enviar_dashboard "EM PROGRESSO" "Calculando..." "0%" "Calculando..." "0%" "Aguardando..." "Calculando..." "$(date +'%d/%m/%Y %H:%M')" "Rodando..." "/etc" "$DISCOS_JSON"

# => AQUI VAI A SUA LÓGICA DE BACKUP (Rsync, Tar, etc) <=
sleep 5

# 3. RECAPTURAR DISCOS E AVISAR O FIM AO DASHBOARD
DISCOS_JSON="["$(df -hP | awk 'NR>1 && $1 ~ /^\/dev\// { printf "{\"fs\":\"%s\", \"uso\":\"%s\", \"mount\":\"%s\", \"size\":\"%s\"},", $1, $5, $6, $2 }' | sed 's/,$//')"]"

enviar_dashboard "SUCESSO" "500GB" "45%" "2TB" "80%" "/mnt/nas/2026-03-01" "2026-03-06" "Data Inicial" "$(date +'%d/%m/%Y %H:%M')" "/etc" "$DISCOS_JSON"

```

---

## 🎨 Estrutura do Frontend

O layout foi projetado utilizando:

* **Puro CSS3 e Flexbox/CSS Grid:** Sem necessidade de frameworks pesados como Bootstrap.
* **FontAwesome:** Para ícones institucionais e alertas.
* **Chart.js:** Para a plotagem gráfica do histórico.
* **Componente Micro-HDD:** Um projeto de *UI Design* construído via CSS que simula carcaça de alumínio, prato magnético, barramento SATA e LED animado, alterando sua cor (Verde, Laranja, Vermelho) baseado no consumo de disco enviado pela API.

---

## 👨‍💻 Autor

Desenvolvido e arquitetado por **Henrique Fagundes**.

🌐 [www.henrique.tec.br](https://www.henrique.tec.br)

🏢 Departamento de TI - Clube Naval

*(Este software é de uso interno e foi estruturado sob os preceitos de observabilidade e confiabilidade de infraestrutura).*
