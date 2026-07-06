from flask import Flask, render_template, request, jsonify, redirect, url_for
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)
app.config["DATABASE"] = "oficina.db"


# Função para conectar ao banco de dados
def get_db():
    db = sqlite3.connect(app.config["DATABASE"])
    db.row_factory = sqlite3.Row
    return db


# Inicializar banco de dados
def init_db():
    if not os.path.exists(app.config["DATABASE"]):
        db = get_db()
        cursor = db.cursor()

        # Tabela de clientes
        cursor.execute("""
            CREATE TABLE clientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                telefone TEXT NOT NULL,
                email TEXT,
                endereco TEXT,
                data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Tabela de veículos
        cursor.execute("""
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
        """)

        # NOVA TABELA: Agendamentos (HU05, HU06, HU07, HU08)
        cursor.execute("""
            CREATE TABLE agendamentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cliente_id INTEGER NOT NULL,
                veiculo_id INTEGER NOT NULL,
                data_agendamento DATE NOT NULL,
                hora_agendamento TIME NOT NULL,
                descricao TEXT,
                status TEXT DEFAULT 'Agendado',
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (cliente_id) REFERENCES clientes(id),
                FOREIGN KEY (veiculo_id) REFERENCES veiculos(id)
            )
        """)

        # Tabela Ordens de Serviço
        cursor.execute("""
            CREATE TABLE ordens_servico (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agendamento_id INTEGER NOT NULL,
                diagnostico TEXT,
                servicos_executados TEXT,
                status TEXT DEFAULT 'Aberta',
                data_abertura TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data_encerramento TIMESTAMP,
                FOREIGN KEY (agendamento_id) REFERENCES agendamentos(id)
            )
        """)
        
        db.commit()
        db.close()
        print("✅ Banco de dados criado com sucesso!")


# ==================== ROTAS ====================


@app.route("/")
def index():
    """Página inicial/dashboard"""
    return render_template("index.html")


# ==================== CLIENTE - CADASTRO ====================


@app.route("/cadastro-cliente", methods=["GET", "POST"])
def cadastro_cliente():
    """Cadastrar novo cliente"""
    if request.method == "POST":
        try:
            nome = request.form.get("nome", "").strip()
            telefone = request.form.get("telefone", "").strip()
            email = request.form.get("email", "").strip()
            endereco = request.form.get("endereco", "").strip()

            # Validação de campos obrigatórios
            if not nome or not telefone:
                return (
                    jsonify(
                        {
                            "sucesso": False,
                            "mensagem": "❌ Nome e Telefone são obrigatórios!",
                        }
                    ),
                    400,
                )

            # Validação de telefone (mínimo 10 dígitos)
            telefone_numeros = "".join(filter(str.isdigit, telefone))
            if len(telefone_numeros) < 10:
                return (
                    jsonify(
                        {
                            "sucesso": False,
                            "mensagem": "❌ Telefone deve ter no mínimo 10 dígitos!",
                        }
                    ),
                    400,
                )

            db = get_db()
            cursor = db.cursor()

            cursor.execute(
                """
                INSERT INTO clientes (nome, telefone, email, endereco)
                VALUES (?, ?, ?, ?)
            """,
                (nome, telefone, email, endereco),
            )

            db.commit()
            db.close()

            return (
                jsonify(
                    {
                        "sucesso": True,
                        "mensagem": f'✅ Cliente "{nome}" cadastrado com sucesso!',
                    }
                ),
                201,
            )

        except Exception as e:
            return (
                jsonify(
                    {
                        "sucesso": False,
                        "mensagem": f"❌ Erro ao cadastrar: {str(e)}",
                    }
                ),
                500,
            )

    return render_template("cadastro_cliente.html")


# ==================== AGENDAMENTOS ====================


@app.route("/agendamentos", methods=["GET"])
def consulta_agendamentos():
    """HU06: Consultar e visualizar todos os agendamentos"""
    db = get_db()
    cursor = db.cursor()

    # Busca agendamentos com os nomes dos clientes e veículos
    cursor.execute("""
        SELECT a.id, a.data_agendamento, a.hora_agendamento, a.descricao, a.status,
               c.nome as cliente_nome, v.marca, v.modelo, v.placa
        FROM agendamentos a
        JOIN clientes c ON a.cliente_id = c.id
        JOIN veiculos v ON a.veiculo_id = v.id
        ORDER BY a.data_agendamento ASC, a.hora_agendamento ASC
    """)
    agendamentos = cursor.fetchall()
    db.close()

    return render_template(
        "consulta_agendamentos.html", agendamentos=agendamentos
    )


@app.route("/agendar", methods=["GET", "POST"])
def cadastro_agendamento():
    """HU05: Criar novo agendamento de serviço"""
    db = get_db()
    cursor = db.cursor()

    if request.method == "POST":
        try:
            cliente_id = request.form.get("cliente_id", "").strip()
            veiculo_id = request.form.get("veiculo_id", "").strip()
            data_agendamento = request.form.get("data", "").strip()
            hora_agendamento = request.form.get("hora", "").strip()
            descricao = request.form.get("descricao", "").strip()

            if not all(
                [cliente_id, veiculo_id, data_agendamento, hora_agendamento]
            ):
                return (
                    jsonify(
                        {
                            "sucesso": False,
                            "mensagem": "❌ Cliente, Veículo, Data e Hora são obrigatórios!",
                        }
                    ),
                    400,
                )

            # Prevenção de conflitos (Regra de Negócio HU05)
            cursor.execute(
                """
                SELECT id FROM agendamentos 
                WHERE data_agendamento = ? AND hora_agendamento = ? AND status = 'Agendado'
            """,
                (data_agendamento, hora_agendamento),
            )

            if cursor.fetchone():
                return (
                    jsonify(
                        {
                            "sucesso": False,
                            "mensagem": "❌ Já existe um atendimento agendado para este horário!",
                        }
                    ),
                    400,
                )

            cursor.execute(
                """
                INSERT INTO agendamentos (cliente_id, veiculo_id, data_agendamento, hora_agendamento, descricao)
                VALUES (?, ?, ?, ?, ?)
            """,
                (
                    cliente_id,
                    veiculo_id,
                    data_agendamento,
                    hora_agendamento,
                    descricao,
                ),
            )

            db.commit()
            return (
                jsonify(
                    {
                        "sucesso": True,
                        "mensagem": "✅ Agendamento registrado com sucesso!",
                    }
                ),
                201,
            )

        except Exception as e:
            return (
                jsonify(
                    {
                        "sucesso": False,
                        "mensagem": f"❌ Erro ao agendar: {str(e)}",
                    }
                ),
                500,
            )
        finally:
            db.close()

    # GET: Buscar clientes para o formulário
    cursor.execute("SELECT id, nome FROM clientes ORDER BY nome ASC")
    clientes = cursor.fetchall()
    db.close()
    return render_template("cadastro_agendamento.html", clientes=clientes)


@app.route("/agendamento/<int:agendamento_id>/editar", methods=["POST"])
def editar_agendamento(agendamento_id):
    """HU07: Alterar data e horário do agendamento"""
    try:
        nova_data = request.form.get("nova_data", "").strip()
        nova_hora = request.form.get("nova_hora", "").strip()

        if not nova_data or not nova_hora:
            return (
                jsonify(
                    {
                        "sucesso": False,
                        "mensagem": "❌ Nova data e hora são obrigatórias!",
                    }
                ),
                400,
            )

        db = get_db()
        cursor = db.cursor()

        # Verificar conflito no novo horário
        cursor.execute(
            """
            SELECT id FROM agendamentos 
            WHERE data_agendamento = ? AND hora_agendamento = ? AND id != ? AND status = 'Agendado'
        """,
            (nova_data, nova_hora, agendamento_id),
        )

        if cursor.fetchone():
            return (
                jsonify(
                    {
                        "sucesso": False,
                        "mensagem": "❌ Horário indisponível. Já existe outro agendamento.",
                    }
                ),
                400,
            )

        cursor.execute(
            """
            UPDATE agendamentos
            SET data_agendamento = ?, hora_agendamento = ?
            WHERE id = ?
        """,
            (nova_data, nova_hora, agendamento_id),
        )

        db.commit()
        db.close()

        return (
            jsonify(
                {
                    "sucesso": True,
                    "mensagem": "✅ Horário do agendamento atualizado com sucesso!",
                }
            ),
            200,
        )

    except Exception as e:
        return (
            jsonify(
                {
                    "sucesso": False,
                    "mensagem": f"❌ Erro ao atualizar: {str(e)}",
                }
            ),
            500,
        )


@app.route("/agendamento/<int:agendamento_id>/cancelar", methods=["POST"])
def cancelar_agendamento(agendamento_id):
    """HU08: Cancelar agendamento"""
    try:
        db = get_db()
        cursor = db.cursor()

        cursor.execute(
            "UPDATE agendamentos SET status = 'Cancelado' WHERE id = ?",
            (agendamento_id,),
        )

        if cursor.rowcount == 0:
            return (
                jsonify(
                    {
                        "sucesso": False,
                        "mensagem": "❌ Agendamento não encontrado!",
                    }
                ),
                404,
            )

        db.commit()
        db.close()

        return (
            jsonify(
                {
                    "sucesso": True,
                    "mensagem": "✅ Agendamento cancelado com sucesso!",
                }
            ),
            200,
        )

    except Exception as e:
        return (
            jsonify(
                {
                    "sucesso": False,
                    "mensagem": f"❌ Erro ao cancelar: {str(e)}",
                }
            ),
            500,
        )


# ==================== CLIENTE - CONSULTA ====================


@app.route("/consulta-cliente", methods=["GET", "POST"])
def consulta_cliente():
    """Consultar clientes cadastrados"""
    clientes = []
    termo_busca = ""

    if request.method == "POST":
        termo_busca = request.form.get("busca", "").strip()

        if termo_busca:
            db = get_db()
            cursor = db.cursor()

            # Buscar por nome, telefone ou email
            cursor.execute(
                """
                SELECT id, nome, telefone, email, endereco, data_cadastro
                FROM clientes
                WHERE nome LIKE ? OR telefone LIKE ? OR email LIKE ?
                ORDER BY nome ASC
            """,
                (f"%{termo_busca}%", f"%{termo_busca}%", f"%{termo_busca}%"),
            )

            clientes = cursor.fetchall()
            db.close()

    return render_template(
        "consulta_cliente.html", clientes=clientes, termo_busca=termo_busca
    )


# ==================== CLIENTE - DETALHES ====================


@app.route("/cliente/<int:cliente_id>")
def detalhes_cliente(cliente_id):
    """Ver detalhes de um cliente e seus veículos"""
    db = get_db()
    cursor = db.cursor()

    # Buscar dados do cliente
    cursor.execute("SELECT * FROM clientes WHERE id = ?", (cliente_id,))
    cliente = cursor.fetchone()

    if not cliente:
        return "Cliente não encontrado", 404

    # Buscar veículos do cliente
    cursor.execute(
        "SELECT * FROM veiculos WHERE cliente_id = ? ORDER BY data_cadastro DESC",
        (cliente_id,),
    )
    veiculos = cursor.fetchall()

    db.close()

    return render_template(
        "detalhes_cliente.html", cliente=cliente, veiculos=veiculos
    )


# ==================== VEÍCULO - CADASTRO ====================


@app.route("/cadastro-veiculo", methods=["GET", "POST"])
def cadastro_veiculo():
    """Cadastrar novo veículo"""
    clientes = []

    # Buscar lista de clientes para o dropdown
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT id, nome FROM clientes ORDER BY nome ASC")
    clientes = cursor.fetchall()
    db.close()

    if request.method == "POST":
        try:
            cliente_id = request.form.get("cliente_id", "").strip()
            placa = request.form.get("placa", "").strip().upper()
            marca = request.form.get("marca", "").strip()
            modelo = request.form.get("modelo", "").strip()
            ano = request.form.get("ano", "").strip()
            cor = request.form.get("cor", "").strip()

            # Validações
            if not cliente_id or not placa or not marca or not modelo:
                return (
                    jsonify(
                        {
                            "sucesso": False,
                            "mensagem": "❌ Cliente, Placa, Marca e Modelo são obrigatórios!",
                        }
                    ),
                    400,
                )

            # Validar placa (formato simplificado)
            if len(placa) < 6:
                return (
                    jsonify(
                        {
                            "sucesso": False,
                            "mensagem": "❌ Placa deve ter no mínimo 6 caracteres!",
                        }
                    ),
                    400,
                )

            # Validar ano
            if ano:
                try:
                    ano_int = int(ano)
                    if ano_int < 1900 or ano_int > datetime.now().year + 1:
                        return (
                            jsonify(
                                {
                                    "sucesso": False,
                                    "mensagem": f"❌ Ano inválido! Deve estar entre 1900 e {datetime.now().year + 1}",
                                }
                            ),
                            400,
                        )
                except:
                    return (
                        jsonify(
                            {
                                "sucesso": False,
                                "mensagem": "❌ Ano deve ser um número válido!",
                            }
                        ),
                        400,
                    )
            else:
                ano = None

            db = get_db()
            cursor = db.cursor()

            # Verificar se placa já existe
            cursor.execute("SELECT id FROM veiculos WHERE placa = ?", (placa,))
            if cursor.fetchone():
                return (
                    jsonify(
                        {
                            "sucesso": False,
                            "mensagem": "❌ Já existe um veículo cadastrado com essa placa!",
                        }
                    ),
                    400,
                )

            # Inserir veículo
            cursor.execute(
                """
                INSERT INTO veiculos (cliente_id, placa, marca, modelo, ano, cor)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (cliente_id, placa, marca, modelo, ano, cor),
            )

            db.commit()
            db.close()

            return (
                jsonify(
                    {
                        "sucesso": True,
                        "mensagem": f'✅ Veículo "{marca} {modelo}" cadastrado com sucesso!',
                    }
                ),
                201,
            )

        except Exception as e:
            return (
                jsonify(
                    {
                        "sucesso": False,
                        "mensagem": f"❌ Erro ao cadastrar: {str(e)}",
                    }
                ),
                500,
            )

    return render_template("cadastro_veiculo.html", clientes=clientes)


# ==================== VEÍCULO - CONSULTA ====================


@app.route("/consulta-veiculo", methods=["GET", "POST"])
def consulta_veiculo():
    """Consultar veículos cadastrados"""
    veiculos = []
    termo_busca = ""

    if request.method == "POST":
        termo_busca = request.form.get("busca", "").strip()

        if termo_busca:
            db = get_db()
            cursor = db.cursor()

            # Buscar por placa, marca, modelo ou cliente
            cursor.execute(
                """
                SELECT v.id, v.placa, v.marca, v.modelo, v.ano, v.cor, v.data_cadastro, c.nome as cliente_nome, v.cliente_id
                FROM veiculos v
                JOIN clientes c ON v.cliente_id = c.id
                WHERE v.placa LIKE ? OR v.marca LIKE ? OR v.modelo LIKE ? OR c.nome LIKE ?
                ORDER BY v.data_cadastro DESC
            """,
                (
                    f"%{termo_busca}%",
                    f"%{termo_busca}%",
                    f"%{termo_busca}%",
                    f"%{termo_busca}%",
                ),
            )

            veiculos = cursor.fetchall()
            db.close()

    return render_template(
        "consulta_veiculo.html", veiculos=veiculos, termo_busca=termo_busca
    )


# ==================== API HELPER ====================


@app.route("/api/cliente/<int:cliente_id>")
def api_cliente(cliente_id):
    """API para buscar dados de um cliente (para JavaScript)"""
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT id, nome FROM clientes WHERE id = ?", (cliente_id,))
    cliente = cursor.fetchone()
    db.close()

    if cliente:
        return jsonify({"id": cliente[0], "nome": cliente[1]})
    return jsonify({"erro": "Cliente não encontrado"}), 404


@app.route("/api/veiculos-cliente/<int:cliente_id>")
def api_veiculos_cliente(cliente_id):
    """API para buscar veículos de um cliente específico (para popular selects no JS)"""
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "SELECT id, placa, modelo, marca FROM veiculos WHERE cliente_id = ?",
        (cliente_id,),
    )
    veiculos = cursor.fetchall()
    db.close()

    lista_veiculos = [
        {
            "id": v["id"],
            "descricao": f"{v['marca']} {v['modelo']} ({v['placa']})",
        }
        for v in veiculos
    ]
    return jsonify(lista_veiculos)
    
@app.route("/ordens-servico")
def consulta_ordens():
    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        SELECT
            os.id,
            os.status,
            os.diagnostico,
            os.servicos_executados,
            os.data_abertura,
            c.nome as cliente_nome,
            v.marca,
            v.modelo,
            v.placa
        FROM ordens_servico os
        JOIN agendamentos a
            ON os.agendamento_id = a.id
        JOIN clientes c
            ON a.cliente_id = c.id
        JOIN veiculos v
            ON a.veiculo_id = v.id
        ORDER BY os.id DESC
    """)

    ordens = cursor.fetchall()
    db.close()

    return render_template(
        "consulta_ordens.html",
        ordens=ordens
    )
@app.route("/ordem-servico/criar", methods=["POST"])
def criar_ordem():
    """HU09: Criar Ordem de Serviço a partir de um agendamento"""
    try:
        agendamento_id = request.form.get("agendamento_id")
        diagnostico = request.form.get("diagnostico", "").strip()
        servicos_executados = request.form.get("servicos_executados", "").strip()

        if not agendamento_id:
            return "❌ Agendamento inválido!", 400

        db = get_db()
        cursor = db.cursor()
        
        # Cria a OS vinculada ao agendamento, salvando também o diagnóstico e serviços iniciais
        cursor.execute("""
            INSERT INTO ordens_servico (agendamento_id, diagnostico, servicos_executados, status) 
            VALUES (?, ?, ?, 'Aberta')
        """, (agendamento_id, diagnostico, servicos_executados))
        
        # Atualiza o agendamento original para 'Em Atendimento'
        cursor.execute("UPDATE agendamentos SET status = 'Em Atendimento' WHERE id = ?", (agendamento_id,))
        
        db.commit()
        db.close()
        
        # Redireciona de volta para a listagem de ordens de serviço de forma elegante!
        return redirect("/ordens-servico")
        
    except Exception as e:
        return f"❌ Erro ao criar Ordem de Serviço: {str(e)}", 500


@app.route("/ordem-servico/<int:os_id>/atualizar", methods=["POST"])
def atualizar_ordem(os_id):
    """HU10, HU11, HU12: Atualizar Diagnóstico, Serviços Executados e Status"""
    try:
        diagnostico = request.form.get("diagnostico", "").strip()
        servicos_executados = request.form.get("servicos_executados", "").strip()
        status = request.form.get("status", "Aberta")

        db = get_db()
        cursor = db.cursor()
        cursor.execute("""
            UPDATE ordens_servico 
            SET diagnostico = ?, servicos_executados = ?, status = ?
            WHERE id = ?
        """, (diagnostico, servicos_executados, status, os_id))
        
        db.commit()
        db.close()
        return jsonify({"sucesso": True, "mensagem": "✅ Ordem de Serviço atualizada com sucesso!"}), 200
    except Exception as e:
        return jsonify({"sucesso": False, "mensagem": f"❌ Erro: {str(e)}"}), 500


@app.route("/ordem-servico/<int:os_id>/encerrar", methods=["POST"])
def encerrar_ordem(os_id):
    """HU13: Encerrar Ordem de Serviço registrando a data/hora final"""
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Encerra a OS mudando o status para 'Concluída' e registrando a data atual do computador
        cursor.execute("""
            UPDATE ordens_servico 
            SET status = 'Concluída', data_encerramento = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (os_id,))
        
        db.commit()
        db.close()
        return jsonify({"sucesso": True, "mensagem": "✅ Ordem de Serviço encerrada com sucesso!"}), 200
    except Exception as e:
        return jsonify({"sucesso": False, "mensagem": f"❌ Erro: {str(e)}"}), 500

@app.route("/ordem-servico/nova", methods=["GET"])
def nova_ordem_tela():
    """Rota para abrir a tela de formulário de Nova Ordem de Serviço"""
    db = get_db()
    cursor = db.cursor()
    
    # Busca os agendamentos que estão confirmados para listar no <select> do formulário
    cursor.execute("""
        SELECT a.id, c.nome 
        FROM agendamentos a
        JOIN clientes c ON a.cliente_id = c.id
        WHERE a.status = 'Agendado'
    """)
    agendamentos = cursor.fetchall()
    db.close()
    
    return render_template("cadastro_ordem.html", agendamentos=agendamentos)


# ==================== NOVAS FUNCIONALIDADES ====================
# HU: Atualizar Status/Etapa/Progresso da OS (com notificação automática)
# HU: Notificações ao Cliente
# HU: Acompanhamento de Serviços em Andamento (cliente)
# HU: Histórico Completo do Veículo
#
# As rotas abaixo foram adicionadas sem alterar nenhuma rota, função ou
# lógica já existente no arquivo original.


def migrar_banco():
    """Garante que as tabelas/colunas necessárias para as novas
    funcionalidades existam, tanto em bancos novos quanto em bancos
    já existentes (como o oficina.db atual), sem apagar nenhum dado."""
    db = get_db()
    cursor = db.cursor()

    # Novas colunas em ordens_servico: etapa, percentual de conclusão e observações
    colunas_novas = {
        "etapa": "TEXT",
        "percentual_conclusao": "INTEGER DEFAULT 0",
        "observacoes": "TEXT",
    }
    cursor.execute("PRAGMA table_info(ordens_servico)")
    colunas_existentes = [col["name"] for col in cursor.fetchall()]
    for nome, tipo in colunas_novas.items():
        if nome not in colunas_existentes:
            cursor.execute(f"ALTER TABLE ordens_servico ADD COLUMN {nome} {tipo}")

    # Tabela de histórico de serviços realizados por veículo
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS historico_servicos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            veiculo_id INTEGER NOT NULL,
            ordem_servico_id INTEGER,
            tipo_servico TEXT,
            descricao TEXT,
            valor REAL,
            data_servico DATE DEFAULT (DATE('now')),
            data_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (veiculo_id) REFERENCES veiculos(id),
            FOREIGN KEY (ordem_servico_id) REFERENCES ordens_servico(id)
        )
    """)

    # Tabela de notificações enviadas ao cliente
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notificacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER,
            veiculo_id INTEGER,
            ordem_servico_id INTEGER,
            tipo TEXT NOT NULL,
            mensagem TEXT NOT NULL,
            data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (cliente_id) REFERENCES clientes(id),
            FOREIGN KEY (veiculo_id) REFERENCES veiculos(id),
            FOREIGN KEY (ordem_servico_id) REFERENCES ordens_servico(id)
        )
    """)

    db.commit()
    db.close()
    print("✅ Migração de banco concluída (tabelas/colunas novas verificadas)!")


@app.route("/ordem-servico/<int:os_id>/atualizar-status", methods=["GET", "POST"])
def atualizar_status_ordem(os_id):
    """HU: Atualizar status, etapa e percentual de conclusão de uma OS,
    notificando automaticamente o cliente (inclusive ao concluir o serviço)."""
    db = get_db()
    cursor = db.cursor()

    if request.method == "POST":
        try:
            status = request.form.get("status", "").strip()
            etapa = request.form.get("etapa", "").strip()
            percentual = request.form.get("percentual", "0").strip()
            observacoes = request.form.get("observacoes", "").strip()

            if not status:
                db.close()
                return jsonify({"sucesso": False, "mensagem": "❌ Por favor, selecione um status!"}), 400

            try:
                percentual_int = int(percentual)
            except ValueError:
                percentual_int = 0
            percentual_int = max(0, min(100, percentual_int))

            # Busca dados do veículo/cliente vinculados à OS (necessário p/ notificação)
            cursor.execute("""
                SELECT os.id, a.veiculo_id, a.cliente_id, v.marca, v.modelo, v.placa
                FROM ordens_servico os
                JOIN agendamentos a ON os.agendamento_id = a.id
                JOIN veiculos v ON a.veiculo_id = v.id
                WHERE os.id = ?
            """, (os_id,))
            info = cursor.fetchone()

            if not info:
                db.close()
                return jsonify({"sucesso": False, "mensagem": "❌ Ordem de Serviço não encontrada!"}), 404

            if status == "Concluída":
                percentual_int = 100
                cursor.execute("""
                    UPDATE ordens_servico
                    SET status = ?, etapa = ?, percentual_conclusao = ?, observacoes = ?,
                        data_encerramento = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (status, etapa, percentual_int, observacoes, os_id))

                # Registra automaticamente no histórico do veículo
                cursor.execute("""
                    INSERT INTO historico_servicos (veiculo_id, ordem_servico_id, tipo_servico, descricao, data_servico)
                    VALUES (?, ?, ?, ?, DATE('now'))
                """, (info["veiculo_id"], os_id, etapa or "Serviço concluído", observacoes))

                tipo_notif = "conclusao"
                mensagem_notif = (
                    f"✅ Seu veículo {info['marca']} {info['modelo']} ({info['placa']}) "
                    f"está pronto para retirada!"
                )
            else:
                cursor.execute("""
                    UPDATE ordens_servico
                    SET status = ?, etapa = ?, percentual_conclusao = ?, observacoes = ?
                    WHERE id = ?
                """, (status, etapa, percentual_int, observacoes, os_id))

                tipo_notif = "atualizacao"
                etapa_txt = f" - Etapa: {etapa}" if etapa else ""
                mensagem_notif = (
                    f"🔧 Atualização no serviço do seu veículo {info['marca']} {info['modelo']} "
                    f"({info['placa']}): {status}{etapa_txt} ({percentual_int}% concluído)"
                )

            # Gera a notificação automática para o cliente
            cursor.execute("""
                INSERT INTO notificacoes (cliente_id, veiculo_id, ordem_servico_id, tipo, mensagem)
                VALUES (?, ?, ?, ?, ?)
            """, (info["cliente_id"], info["veiculo_id"], os_id, tipo_notif, mensagem_notif))

            db.commit()
            db.close()

            return jsonify({"sucesso": True, "mensagem": "✅ Status da Ordem de Serviço atualizado com sucesso!"}), 200

        except Exception as e:
            db.close()
            return jsonify({"sucesso": False, "mensagem": f"❌ Erro ao atualizar: {str(e)}"}), 500

    # GET: exibe o formulário já preenchido com os dados atuais da OS
    cursor.execute("""
        SELECT os.id, os.status, os.etapa, os.percentual_conclusao, os.observacoes,
               c.nome as cliente_nome, v.marca, v.modelo, v.placa
        FROM ordens_servico os
        JOIN agendamentos a ON os.agendamento_id = a.id
        JOIN clientes c ON a.cliente_id = c.id
        JOIN veiculos v ON a.veiculo_id = v.id
        WHERE os.id = ?
    """, (os_id,))
    ordem = cursor.fetchone()
    db.close()

    if not ordem:
        return render_template("erro.html", mensagem="Ordem de Serviço não encontrada"), 404

    return render_template("atualizar_status_ordem.html", os_id=os_id, ordem=ordem)


@app.route("/notificacoes")
def notificacoes():
    """HU: Exibir as notificações geradas para o cliente (atualizações e conclusão de serviço).
    Aceita opcionalmente ?cliente_id=<id> para filtrar por cliente."""
    cliente_id = request.args.get("cliente_id", "").strip()

    db = get_db()
    cursor = db.cursor()

    if cliente_id:
        cursor.execute("""
            SELECT n.id, n.tipo, n.mensagem, n.data_criacao, v.placa, v.marca, v.modelo
            FROM notificacoes n
            LEFT JOIN veiculos v ON n.veiculo_id = v.id
            WHERE n.cliente_id = ?
            ORDER BY n.data_criacao DESC
        """, (cliente_id,))
    else:
        cursor.execute("""
            SELECT n.id, n.tipo, n.mensagem, n.data_criacao, v.placa, v.marca, v.modelo
            FROM notificacoes n
            LEFT JOIN veiculos v ON n.veiculo_id = v.id
            ORDER BY n.data_criacao DESC
        """)

    lista_notificacoes = cursor.fetchall()
    db.close()

    return render_template("notificacoes.html", notificacoes=lista_notificacoes)


@app.route("/acompanhamento-servicos")
def acompanhamento_servicos():
    """HU: Permite ao cliente acompanhar em tempo real o status/progresso do serviço.
    Aceita opcionalmente ?cliente_id=<id> para filtrar apenas os serviços de um cliente."""
    cliente_id = request.args.get("cliente_id", "").strip()

    db = get_db()
    cursor = db.cursor()

    query = """
        SELECT os.id, os.status, os.etapa, os.percentual_conclusao,
               os.data_abertura, os.data_encerramento,
               a.descricao as descricao_agendamento,
               v.marca, v.modelo, v.placa
        FROM ordens_servico os
        JOIN agendamentos a ON os.agendamento_id = a.id
        JOIN veiculos v ON a.veiculo_id = v.id
        WHERE os.status != 'Cancelada'
    """
    parametros = ()
    if cliente_id:
        query += " AND a.cliente_id = ?"
        parametros = (cliente_id,)
    query += " ORDER BY os.data_abertura DESC"

    cursor.execute(query, parametros)
    servicos = cursor.fetchall()
    db.close()

    return render_template("acompanhamento_servicos.html", servicos=servicos)


@app.route("/veiculo/<int:veiculo_id>/historico")
def historico_veiculo(veiculo_id):
    """HU: Exibe o histórico completo de serviços realizados em um veículo,
    além das últimas ordens de serviço registradas."""
    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        SELECT v.id, v.placa, v.marca, v.modelo, v.ano, v.cor, c.nome as cliente_nome
        FROM veiculos v
        JOIN clientes c ON v.cliente_id = c.id
        WHERE v.id = ?
    """, (veiculo_id,))
    veiculo = cursor.fetchone()

    if not veiculo:
        db.close()
        return render_template("erro.html", mensagem="Veículo não encontrado"), 404

    cursor.execute("""
        SELECT data_servico, data_registro, tipo_servico, descricao, valor
        FROM historico_servicos
        WHERE veiculo_id = ?
        ORDER BY data_servico DESC, data_registro DESC
    """, (veiculo_id,))
    historico = cursor.fetchall()

    cursor.execute("""
        SELECT os.id, os.status, os.data_abertura, os.data_encerramento,
               COALESCE(os.diagnostico, os.servicos_executados) as descricao
        FROM ordens_servico os
        JOIN agendamentos a ON os.agendamento_id = a.id
        WHERE a.veiculo_id = ?
        ORDER BY os.id DESC
        LIMIT 10
    """, (veiculo_id,))
    ultimas_ordens = cursor.fetchall()

    db.close()

    return render_template(
        "historico_veiculo.html",
        veiculo=veiculo,
        historico=historico,
        ultimas_ordens=ultimas_ordens,
    )


# ==================== ERROS ====================


@app.errorhandler(404)
def nao_encontrado(error):
    return render_template("erro.html", mensagem="Página não encontrada"), 404


@app.errorhandler(500)
def erro_servidor(error):
    return render_template("erro.html", mensagem="Erro no servidor"), 500


# ==================== INICIALIZAR ====================

if __name__ == "__main__":
    init_db()
    migrar_banco()  # Cria/atualiza tabelas e colunas das novas funcionalidades
    # Debug=True permite recarregar automaticamente quando você modifica o código
    porta = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=porta)