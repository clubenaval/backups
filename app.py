from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import desc
import os
import time

app = Flask(__name__)

db_user = os.environ.get('DB_USER', 'app_user')
db_pass = os.environ.get('DB_PASSWORD', 'app_password_segura')
db_host = os.environ.get('DB_HOST', 'db')
db_name = os.environ.get('DB_NAME', 'backups_db')

app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+pymysql://{db_user}:{db_pass}@{db_host}/{db_name}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class BackupLog(db.Model):
    __tablename__ = 'backup_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    servidor = db.Column(db.String(100), nullable=False)
    tipo_backup = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), nullable=False)
    data_inicio = db.Column(db.String(50))
    data_fim = db.Column(db.String(50))
    espaco_livre_origem = db.Column(db.String(20))
    uso_percentual_origem = db.Column(db.String(10))
    espaco_livre_destino = db.Column(db.String(20))
    uso_percentual_destino = db.Column(db.String(10))
    diretorio_gerado = db.Column(db.String(255))
    proximo_a_expirar = db.Column(db.String(255))
    detalhes_erro = db.Column(db.Text, nullable=True)

def init_db():
    retries = 5
    while retries > 0:
        try:
            with app.app_context():
                db.create_all()
            print("Tabelas criadas/verificadas com sucesso!")
            break
        except Exception as e:
            print(f"Aguardando o banco de dados iniciar... ({retries} tentativas restantes)")
            retries -= 1
            time.sleep(5)

init_db()

@app.route('/api/backup', methods=['POST'])
def registrar_backup():
    try:
        dados = request.get_json()
        
        novo_log = BackupLog(
            servidor=dados.get('servidor'),
            tipo_backup=dados.get('tipo_backup'),
            status=dados.get('status'),
            data_inicio=dados.get('data_inicio', 'N/A'),
            data_fim=dados.get('data_fim', 'N/A'),
            espaco_livre_origem=dados.get('espaco_livre_origem', 'N/A'),
            uso_percentual_origem=dados.get('uso_percentual_origem', '0%'),
            espaco_livre_destino=dados.get('espaco_livre_destino', 'N/A'),
            uso_percentual_destino=dados.get('uso_percentual_destino', '0%'),
            diretorio_gerado=dados.get('diretorio_gerado', 'N/A'),
            proximo_a_expirar=dados.get('proximo_a_expirar', 'N/A'),
            detalhes_erro=dados.get('detalhes_erro', '')
        )
        
        db.session.add(novo_log)
        db.session.commit()
        return jsonify({'mensagem': 'Log registrado com sucesso!', 'id': novo_log.id}), 201

    except Exception as e:
        return jsonify({'erro': str(e)}), 400

@app.route('/')
def dashboard():
    subquery = db.session.query(
        BackupLog.servidor,
        BackupLog.tipo_backup,
        db.func.max(BackupLog.id).label('max_id')
    ).group_by(BackupLog.servidor, BackupLog.tipo_backup).subquery()

    ultimos_backups = db.session.query(BackupLog).join(
        subquery,
        db.and_(
            BackupLog.servidor == subquery.c.servidor,
            BackupLog.tipo_backup == subquery.c.tipo_backup,
            BackupLog.id == subquery.c.max_id
        )
    ).order_by(BackupLog.servidor, BackupLog.tipo_backup).all()

    versao_app = os.environ.get('APP_VERSION', 'dev-local')
    return render_template('index.html', backups=ultimos_backups, version=versao_app)

@app.route('/historico')
def historico():
    # Coleta de Parâmetros de Filtro e Página atual (padrão é 1)
    filtro_servidor = request.args.get('servidor', '')
    filtro_status = request.args.get('status', '')
    filtro_tipo = request.args.get('tipo_backup', '')
    page = request.args.get('page', 1, type=int)

    # Constrói a Query Dinamicamente
    query = BackupLog.query
    if filtro_servidor: query = query.filter(BackupLog.servidor == filtro_servidor)
    if filtro_status: query = query.filter(BackupLog.status == filtro_status)
    if filtro_tipo: query = query.filter(BackupLog.tipo_backup == filtro_tipo)

    # =======================================================
    # SOLUÇÃO DE PERFORMANCE: Paginação Real no Banco (15 por pág)
    # =======================================================
    paginacao = query.order_by(BackupLog.id.desc()).paginate(page=page, per_page=15, error_out=False)

    # Gráficos: Limitado aos últimos 100 registros do filtro para não travar o Chart.js
    grafico_backups = query.order_by(BackupLog.id.desc()).limit(100).all()

    # Busca lista de servidores únicos para popular o combobox do filtro
    servidores_unicos = [s[0] for s in db.session.query(BackupLog.servidor).distinct().all()]

    # ===============================
    # PROCESSAMENTO DOS GRÁFICOS
    # ===============================
    sucesso = sum(1 for b in grafico_backups if b.status == 'SUCESSO')
    falha = sum(1 for b in grafico_backups if b.status == 'FALHA')
    progresso = sum(1 for b in grafico_backups if b.status == 'EM PROGRESSO')

    datas_dict = {}
    for b in reversed(grafico_backups): # Do mais antigo pro mais novo dentro do limite
        dia = str(b.data_inicio)[:10] if b.data_inicio else "N/A"
        if dia not in datas_dict:
            datas_dict[dia] = {'sucesso': 0, 'falha': 0}
        if b.status == 'SUCESSO': datas_dict[dia]['sucesso'] += 1
        elif b.status == 'FALHA': datas_dict[dia]['falha'] += 1

    labels_linha = list(datas_dict.keys())
    dados_sucesso = [datas_dict[d]['sucesso'] for d in labels_linha]
    dados_falha = [datas_dict[d]['falha'] for d in labels_linha]

    versao_app = os.environ.get('APP_VERSION', 'dev-local')
    
    # Envia a variável 'paginacao' em vez de 'backups' para a tela
    return render_template('historico.html', 
                           paginacao=paginacao, 
                           servidores=servidores_unicos,
                           filtros={'servidor': filtro_servidor, 'status': filtro_status, 'tipo': filtro_tipo},
                           grafico_pizza=[sucesso, falha, progresso],
                           grafico_linha={'labels': labels_linha, 'sucesso': dados_sucesso, 'falha': dados_falha},
                           version=versao_app)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)