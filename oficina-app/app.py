from flask import Flask, render_template, request, jsonify, redirect, url_for
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)
app.config['DATABASE'] = 'oficina.db'

# Função para conectar ao banco de dados
def get_db():
    db = sqlite3.connect(app.config['DATABASE'])
    db.row_factory = sqlite3.Row
    return db

# Inicializar banco de dados
def init_db():
    if not os.path.exists(app.config['DATABASE']):
        db = get_db()
        cursor = db.cursor()
        
        # Tabela de clientes
        cursor.execute('''
            CREATE TABLE clientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                telefone TEXT NOT NULL,
                email TEXT,
                endereco TEXT,
                data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabela de veículos
        cursor.execute('''
            CREATE TABLE veiculos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cliente_id INTEGER NOT NULL,
                placa TEXT NOT NULL UNIQUE,
                marca TEXT NOT NULL,
                modelo TEXT NOT NULL,
                ano INTEGER,
                cor TEXT,
                data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (cliente_id) REFERENCES clientes(id)
            )
        ''')
        
        db.commit()
        db.close()
        print("✅ Banco de dados criado com sucesso!")

# ==================== ROTAS ====================

@app.route('/')
def index():
    """Página inicial/dashboard"""
    return render_template('index.html')

# ==================== CLIENTE - CADASTRO ====================

@app.route('/cadastro-cliente', methods=['GET', 'POST'])
def cadastro_cliente():
    """Cadastrar novo cliente"""
    if request.method == 'POST':
        try:
            nome = request.form.get('nome', '').strip()
            telefone = request.form.get('telefone', '').strip()
            email = request.form.get('email', '').strip()
            endereco = request.form.get('endereco', '').strip()
            
            # Validação de campos obrigatórios
            if not nome or not telefone:
                return jsonify({'sucesso': False, 'mensagem': '❌ Nome e Telefone são obrigatórios!'}), 400
            
            # Validação de telefone (mínimo 10 dígitos)
            telefone_numeros = ''.join(filter(str.isdigit, telefone))
            if len(telefone_numeros) < 10:
                return jsonify({'sucesso': False, 'mensagem': '❌ Telefone deve ter no mínimo 10 dígitos!'}), 400
            
            db = get_db()
            cursor = db.cursor()
            
            cursor.execute('''
                INSERT INTO clientes (nome, telefone, email, endereco)
                VALUES (?, ?, ?, ?)
            ''', (nome, telefone, email, endereco))
            
            db.commit()
            db.close()
            
            return jsonify({'sucesso': True, 'mensagem': f'✅ Cliente "{nome}" cadastrado com sucesso!'}), 201
            
        except Exception as e:
            return jsonify({'sucesso': False, 'mensagem': f'❌ Erro ao cadastrar: {str(e)}'}), 500
    
    return render_template('cadastro_cliente.html')

# ==================== CLIENTE - CONSULTA ====================

@app.route('/consulta-cliente', methods=['GET', 'POST'])
def consulta_cliente():
    """Consultar clientes cadastrados"""
    clientes = []
    termo_busca = ''
    
    if request.method == 'POST':
        termo_busca = request.form.get('busca', '').strip()
        
        if termo_busca:
            db = get_db()
            cursor = db.cursor()
            
            # Buscar por nome, telefone ou email
            cursor.execute('''
                SELECT id, nome, telefone, email, endereco, data_cadastro
                FROM clientes
                WHERE nome LIKE ? OR telefone LIKE ? OR email LIKE ?
                ORDER BY nome ASC
            ''', (f'%{termo_busca}%', f'%{termo_busca}%', f'%{termo_busca}%'))
            
            clientes = cursor.fetchall()
            db.close()
    
    return render_template('consulta_cliente.html', clientes=clientes, termo_busca=termo_busca)

# ==================== CLIENTE - DETALHES ====================

@app.route('/cliente/<int:cliente_id>')
def detalhes_cliente(cliente_id):
    """Ver detalhes de um cliente e seus veículos"""
    db = get_db()
    cursor = db.cursor()
    
    # Buscar dados do cliente
    cursor.execute('SELECT * FROM clientes WHERE id = ?', (cliente_id,))
    cliente = cursor.fetchone()
    
    if not cliente:
        return "Cliente não encontrado", 404
    
    # Buscar veículos do cliente
    cursor.execute('SELECT * FROM veiculos WHERE cliente_id = ? ORDER BY data_cadastro DESC', (cliente_id,))
    veiculos = cursor.fetchall()
    
    db.close()
    
    return render_template('detalhes_cliente.html', cliente=cliente, veiculos=veiculos)

# ==================== VEÍCULO - CADASTRO ====================

@app.route('/cadastro-veiculo', methods=['GET', 'POST'])
def cadastro_veiculo():
    """Cadastrar novo veículo"""
    clientes = []
    
    # Buscar lista de clientes para o dropdown
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT id, nome FROM clientes ORDER BY nome ASC')
    clientes = cursor.fetchall()
    db.close()
    
    if request.method == 'POST':
        try:
            cliente_id = request.form.get('cliente_id', '').strip()
            placa = request.form.get('placa', '').strip().upper()
            marca = request.form.get('marca', '').strip()
            modelo = request.form.get('modelo', '').strip()
            ano = request.form.get('ano', '').strip()
            cor = request.form.get('cor', '').strip()
            
            # Validações
            if not cliente_id or not placa or not marca or not modelo:
                return jsonify({'sucesso': False, 'mensagem': '❌ Cliente, Placa, Marca e Modelo são obrigatórios!'}), 400
            
            # Validar placa (formato simplificado)
            if len(placa) < 6:
                return jsonify({'sucesso': False, 'mensagem': '❌ Placa deve ter no mínimo 6 caracteres!'}), 400
            
            # Validar ano
            if ano:
                try:
                    ano_int = int(ano)
                    if ano_int < 1900 or ano_int > datetime.now().year + 1:
                        return jsonify({'sucesso': False, 'mensagem': f'❌ Ano inválido! Deve estar entre 1900 e {datetime.now().year + 1}'}), 400
                except:
                    return jsonify({'sucesso': False, 'mensagem': '❌ Ano deve ser um número válido!'}), 400
            else:
                ano = None
            
            db = get_db()
            cursor = db.cursor()
            
            # Verificar se placa já existe
            cursor.execute('SELECT id FROM veiculos WHERE placa = ?', (placa,))
            if cursor.fetchone():
                return jsonify({'sucesso': False, 'mensagem': '❌ Já existe um veículo cadastrado com essa placa!'}), 400
            
            # Inserir veículo
            cursor.execute('''
                INSERT INTO veiculos (cliente_id, placa, marca, modelo, ano, cor)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (cliente_id, placa, marca, modelo, ano, cor))
            
            db.commit()
            db.close()
            
            return jsonify({'sucesso': True, 'mensagem': f'✅ Veículo "{marca} {modelo}" cadastrado com sucesso!'}), 201
            
        except Exception as e:
            return jsonify({'sucesso': False, 'mensagem': f'❌ Erro ao cadastrar: {str(e)}'}), 500
    
    return render_template('cadastro_veiculo.html', clientes=clientes)

# ==================== VEÍCULO - CONSULTA ====================

@app.route('/consulta-veiculo', methods=['GET', 'POST'])
def consulta_veiculo():
    """Consultar veículos cadastrados"""
    veiculos = []
    termo_busca = ''
    
    if request.method == 'POST':
        termo_busca = request.form.get('busca', '').strip()
        
        if termo_busca:
            db = get_db()
            cursor = db.cursor()
            
            # Buscar por placa, marca, modelo ou cliente
            cursor.execute('''
                SELECT v.id, v.placa, v.marca, v.modelo, v.ano, v.cor, v.data_cadastro, c.nome as cliente_nome, v.cliente_id
                FROM veiculos v
                JOIN clientes c ON v.cliente_id = c.id
                WHERE v.placa LIKE ? OR v.marca LIKE ? OR v.modelo LIKE ? OR c.nome LIKE ?
                ORDER BY v.data_cadastro DESC
            ''', (f'%{termo_busca}%', f'%{termo_busca}%', f'%{termo_busca}%', f'%{termo_busca}%'))
            
            veiculos = cursor.fetchall()
            db.close()
    
    return render_template('consulta_veiculo.html', veiculos=veiculos, termo_busca=termo_busca)

# ==================== API HELPER ====================

@app.route('/api/cliente/<int:cliente_id>')
def api_cliente(cliente_id):
    """API para buscar dados de um cliente (para JavaScript)"""
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT id, nome FROM clientes WHERE id = ?', (cliente_id,))
    cliente = cursor.fetchone()
    db.close()
    
    if cliente:
        return jsonify({'id': cliente[0], 'nome': cliente[1]})
    return jsonify({'erro': 'Cliente não encontrado'}), 404

# ==================== ERROS ====================

@app.errorhandler(404)
def nao_encontrado(error):
    return render_template('erro.html', mensagem='Página não encontrada'), 404

@app.errorhandler(500)
def erro_servidor(error):
    return render_template('erro.html', mensagem='Erro no servidor'), 500

# ==================== INICIALIZAR ====================

if __name__ == '__main__':
    init_db()
    # Debug=True permite recarregar automaticamente quando você modifica o código
    app.run(debug=True, host='0.0.0.0', port=5000)
