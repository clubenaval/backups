from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
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
    data_inicio = db.Column(db.String(50))   # <-- NOVA COLUNA
    data_fim = db.Column(db.String(50))      # <-- NOVA COLUNA
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
    # AGORA AGRUPA POR SERVIDOR E TIPO DE BACKUP (Para ter card do full e incremental separados)
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

    return render_template('index.html', backups=ultimos_backups)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)