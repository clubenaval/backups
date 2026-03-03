#!/bin/bash

# ==============================================================================
# CONFIGURAÇÕES GERAIS E VARIÁVEIS DO SERVIDOR
# ==============================================================================
#DIR_ORIGEM="/mnt/dados"
DIR_ORIGEM="/etc"
DIR_DESTINO="/mnt/nas-sede-full"
NOME_COMPARTILHAMENTO="nas-sede-full"
RETENCAO="5"                # Quantidade de dias para manter os backups
VOLUME_GROUP="discos"       # Nome do VG para checagem de espaço livre
STORAGE="172.16.2.99"       # STORAGE NAS
# ==============================================================================

# MARCA O HORÁRIO DE INÍCIO E NOMEIA ARQUIVOS DE FORMA ÚNICA
DATA_INICIO=$(date +"%d/%m/%Y às %H:%M:%S")
DATA=$(date +%Y-%m-%d)
LOG="/tmp/BKP-FULL-${DATA}.txt"
ANEXO="/tmp/BKP-FULL-${DATA}.zip"

API_URL="http://clubenaval337.clubenaval.intra:5000/api/backup"
DESTINATARIO="servidores@cnsocial.org.br"

ASSUNTO1="Backup FULL do Servidor $(hostname | cut -d. -f1) para o $(ssh $STORAGE "hostname -s" 2>/dev/null) INICIADO em $(date +%d/%m/%Y) às $(date +%H:%M:%S)."
ASSUNTO2="Backup FULL do Servidor $(hostname | cut -d. -f1) para o $(ssh $STORAGE "hostname -s" 2>/dev/null) FINALIZADO em $(date +%d/%m/%Y) às $(date +%H:%M:%S)."

SYNC="rsync -av --chmod=a+rwx --exclude=lixeira/"
TEMPS="$LOG $ANEXO /root/sent"

enviar_dashboard() {
    local status="$1"
    local detalhes="$2"
    local espaco_origem="$3"
    local uso_origem="$4"
    local espaco_destino="$5"
    local uso_destino="$6"
    local dir_gerado="$7"
    local expirar="$8"
    local d_inicio="$9"
    local d_fim="${10}"
    local d_origem="${11}"
    local discos="${12}"

    if [ -z "$discos" ]; then discos="[]"; fi
    if [ -z "$d_origem" ]; then d_origem="N/A"; fi

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
    "detalhes_erro": "$detalhes",
    "data_inicio": "$d_inicio",
    "data_fim": "$d_fim",
    "diretorio_origem": "$d_origem",
    "discos_origem": $discos
}
EOF
    curl -s -X POST -H "Content-Type: application/json" -d @/tmp/payload_bkp.json "$API_URL"
    rm -f /tmp/payload_bkp.json
}

# CAPTURA OS DISCOS FÍSICOS E SEUS TAMANHOS (Size)
DISCOS_JSON="["$(df -hP | awk 'NR>1 && $1 ~ /^\/dev\// { printf "{\"fs\":\"%s\", \"uso\":\"%s\", \"mount\":\"%s\", \"size\":\"%s\"},", $1, $5, $6, $2 }' | sed 's/,$//')"]"

enviar_dashboard "EM PROGRESSO" "Sincronizando arquivos..." "Calculando..." "0%" "Calculando..." "0%" "Aguardando..." "Calculando..." "$DATA_INICIO" "Rodando..." "$DIR_ORIGEM" "$DISCOS_JSON"

mount $DIR_DESTINO 2>&- 1>&-
verifica_montagem_destino=$(df -h | grep "$NOME_COMPARTILHAMENTO" | awk '{print $6}' | awk -F/ '{print $NF}')

if [ "$verifica_montagem_destino" = "$NOME_COMPARTILHAMENTO" ]
  then
	echo "Este arquivo e para simples conferencia." > "$LOG"
	echo "Nele e mostrado o Log de Saida do Backup do servidor $(hostname) no dia $(date +%d/%m/%Y)." >> "$LOG"
	echo >> "$LOG"
	
    mkdir -p /tmp/vazio
    pastas_antigas=$(ls -1dt $DIR_DESTINO/*/ 2>/dev/null | tail -n +$((RETENCAO + 1)))
    if [ -n "$pastas_antigas" ]; then
        for pasta in $pastas_antigas; do
            echo "Apagando backup antigo ($pasta) de forma otimizada com rsync..." >> "$LOG"
            rsync -a --delete /tmp/vazio/ "$pasta/"
            rmdir "$pasta"
        done
    fi
    rmdir /tmp/vazio

    mkdir -p "$DIR_DESTINO/$DATA" 
    
	$SYNC "$DIR_ORIGEM/" "$DIR_DESTINO/$DATA/" >> "$LOG" 2>&1
    tar -zcf "$DIR_DESTINO/$DATA/confs.tar.gz" /root /etc /usr/local/bin
	
    rm -f "$ANEXO"
    zip -j -q "$ANEXO" "$LOG"

    LIVRE_ORIGEM=$(df -h $DIR_ORIGEM | awk 'NR==2 {print $4}')
    USO_ORIGEM=$(df -h $DIR_ORIGEM | awk 'NR==2 {print $5}')
    LIVRE_DESTINO=$(df -h $DIR_DESTINO | awk 'NR==2 {print $4}')
    USO_DESTINO=$(df -h $DIR_DESTINO | awk 'NR==2 {print $5}')
    
    PROXIMO_EXPIRAR=$(find $DIR_DESTINO -maxdepth 1 -mindepth 1 -type d | sort | head -n 1)
    [ -z "$PROXIMO_EXPIRAR" ] && PROXIMO_EXPIRAR="Nenhum"

    DATA_FIM=$(date +"%d/%m/%Y às %H:%M:%S")

    # ATUALIZA O JSON NOVAMENTE PARA PEGAR O STATUS FINAL
    DISCOS_JSON="["$(df -hP | awk 'NR>1 && $1 ~ /^\/dev\// { printf "{\"fs\":\"%s\", \"uso\":\"%s\", \"mount\":\"%s\", \"size\":\"%s\"},", $1, $5, $6, $2 }' | sed 's/,$//')"]"

    enviar_dashboard "SUCESSO" "" "$LIVRE_ORIGEM" "$USO_ORIGEM" "$LIVRE_DESTINO" "$USO_DESTINO" "$DIR_DESTINO/$DATA" "$PROXIMO_EXPIRAR" "$DATA_INICIO" "$DATA_FIM" "$DIR_ORIGEM" "$DISCOS_JSON"

    ARQUIVO_TEMP=$(mktemp /tmp/uso_disco.XXXXXX.html)
    VG_LIVRE=$(vgs --noheadings -o vg_free --units g --nosuffix "$VOLUME_GROUP" 2>/dev/null | awk '{print $1}')
    [ -z "$VG_LIVRE" ] && VG_LIVRE="N/A"

    {
        echo "<html><body><h3>$ASSUNTO2<br>Confira os LOGS em ANEXO</h3><table border='1' cellpadding='5' cellspacing='0' style='border-collapse: collapse;'>"
        echo "<tr><th>Filesystem</th><th>Size</th><th>Used</th><th>Avail</th><th>Use%</th><th>Mounted on</th></tr>"

        df -lh | grep "dados" | sort | awk '
        BEGIN { OFS="" }
        NR>1 {
            if ($5+0 > 95) { color = "red" } else if ($5+0 > 80) { color = "darkorange" } else { color = "black" }
            print "<tr><td>" $1 "</td><td>" $2 "</td><td>" $3 "</td><td>" $4 "</td><td style=\"color:" color "\">" $5 "</td><td>" $6 "</td></tr>"
        }'

        echo "<tr style='background-color: #f2f2f2; font-weight: bold;'>"
        echo "<td colspan='4' style='text-align:right;'>Espaço Livre no Volume Group \"$VOLUME_GROUP\"</td>"
        echo "<td colspan='2' style='text-align:left; color:blue;'>$VG_LIVRE GB</td>"
        echo "</tr>"
        echo "</table></body></html>"
    } > "$ARQUIVO_TEMP"

    mutt -e "set content_type=text/html" -s "$ASSUNTO2" -a "$ANEXO" -- "$DESTINATARIO" < "$ARQUIVO_TEMP"
    rm -f "$ARQUIVO_TEMP"

	rm $TEMPS 2>&- 1>&-
	umount $DIR_DESTINO
  else
        erro_msg="Compartilhamento NAO MONTADO! O Backup FULL do dia $(date +%d/%m/%Y) do Servidor $(hostname | cut -d. -f1) NAO FOI FEITO!"
        echo "$erro_msg" > "$LOG"
	    
        LIVRE_ORIGEM=$(df -h $DIR_ORIGEM | awk 'NR==2 {print $4}')
        USO_ORIGEM=$(df -h $DIR_ORIGEM | awk 'NR==2 {print $5}')
        DATA_FIM=$(date +"%d/%m/%Y às %H:%M:%S")

        enviar_dashboard "FALHA" "$erro_msg" "$LIVRE_ORIGEM" "$USO_ORIGEM" "N/A" "0%" "N/A" "N/A" "$DATA_INICIO" "$DATA_FIM" "$DIR_ORIGEM" "$DISCOS_JSON"

        cat "$LOG" | mutt -s "O Backup FULL do dia $(date +%d/%m/%Y) do Servidor $(hostname | cut -d. -f1) NAO FOI FEITO!" -- "$DESTINATARIO"

  fi

rm -rf /mnt/dados/lixeira/*