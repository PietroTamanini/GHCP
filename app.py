from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import re
import os
import json
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'GHCP-2o25'

@app.template_filter('from_json')
def from_json_filter(value):
    if value:
        try:
            return json.loads(value)
        except:
            return []
    return []

DB_CONFIG = {
    'host': 'localhost',
    'port': '3406',
    'user': 'root',
    'password': '',
    'database': 'loja_informatica'
}

UPLOAD_FOLDER = 'static/uploads/produtos'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db_connection():
    try:
        return mysql.connector.connect(**DB_CONFIG)
    except mysql.connector.Error as err:
        print(f"Erro ao conectar ao banco de dados: {err}")
        return None

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            flash('⚠️ Por favor, faça login para acessar esta página.', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            flash('⚠️ Acesso restrito para administradores.', 'warning')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

def validar_cpf(cpf):
    cpf = re.sub(r'\D', '', cpf)
    if len(cpf) != 11:
        return False
    if cpf == cpf[0] * 11:
        return False
    soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
    digito1 = (soma * 10 % 11) % 10
    if digito1 != int(cpf[9]):
        return False
    soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
    digito2 = (soma * 10 % 11) % 10
    return digito2 == int(cpf[10])

def validar_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def formatar_cpf(cpf):
    cpf = re.sub(r'\D', '', cpf)
    return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"

def formatar_telefone(telefone):
    telefone = re.sub(r'\D', '', telefone)
    if len(telefone) == 11:
        return f"({telefone[:2]}) {telefone[2:7]}-{telefone[7:]}"
    elif len(telefone) == 10:
        return f"({telefone[:2]}) {telefone[2:6]}-{telefone[6:]}"
    return telefone

@app.route('/')
def inicio():
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erro ao conectar ao banco de dados.', 'error')
            return render_template('index.html', produtos_destaque=[])
        
        cursor = conn.cursor(dictionary=True)
        
        # Buscar produtos em destaque (ativos) - máximo 8 produtos
        cursor.execute("""
            SELECT p.* 
            FROM produto p 
            WHERE p.ativo = TRUE 
            ORDER BY p.destaque DESC, p.data_cadastro DESC 
            LIMIT 8
        """)
        produtos_base = cursor.fetchall()
        
        # Buscar ofertas ativas
        cursor.execute("""
            SELECT o.*, p.nome, p.descricao, p.categoria, p.marca, p.imagens
            FROM ofertas o
            JOIN produto p ON o.id_produto = p.id_produto
            WHERE o.ativa = TRUE 
            AND (o.validade IS NULL OR o.validade >= CURDATE())
            AND p.ativo = TRUE
            ORDER BY o.desconto DESC
            LIMIT 6
        """)
        ofertas = cursor.fetchall()
        
        # Combinar produtos base com ofertas
        produtos_destaque = []
        
        # Primeiro adicionar as ofertas
        for oferta in ofertas:
            produto_com_oferta = {
                'id_produto': oferta['id_produto'],
                'nome': oferta['nome'],
                'descricao': oferta['descricao'],
                'categoria': oferta['categoria'],
                'marca': oferta['marca'],
                'preco': oferta['preco_original'],
                'preco_com_desconto': oferta['preco_com_desconto'],
                'desconto': oferta['desconto'],
                'tem_oferta': True,
                'imagens': oferta['imagens']
            }
            produtos_destaque.append(produto_com_oferta)
        
        # Adicionar produtos base (sem repetir)
        produtos_base_ids = [p['id_produto'] for p in produtos_destaque]
        for produto in produtos_base:
            if produto['id_produto'] not in produtos_base_ids and len(produtos_destaque) < 8:
                produto_base = {
                    'id_produto': produto['id_produto'],
                    'nome': produto['nome'],
                    'descricao': produto['descricao'],
                    'categoria': produto['categoria'],
                    'marca': produto['marca'],
                    'preco': produto['preco'],
                    'preco_com_desconto': produto['preco'],
                    'desconto': 0,
                    'tem_oferta': False,
                    'imagens': produto['imagens']
                }
                produtos_destaque.append(produto_base)
        
        return render_template('index.html', produtos_destaque=produtos_destaque)
        
    except mysql.connector.Error as err:
        flash(f'Erro ao carregar produtos: {err}', 'error')
        return render_template('index.html', produtos_destaque=[])
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'usuario_id' in session:
        return redirect(url_for('inicio'))
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        senha = request.form.get('senha', '')
        if not email or not senha:
            flash('❌ Por favor, preencha todos os campos.', 'error')
            return render_template('login.html')
        if not validar_email(email):
            flash('❌ E-mail inválido.', 'error')
            return render_template('login.html')
        try:
            conn = get_db_connection()
            if not conn:
                flash('Erro ao conectar ao banco de dados.', 'error')
                return render_template('login.html')
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT id_cliente, nome, email, senha, ativo FROM clientes WHERE email = %s", (email,))
            usuario = cursor.fetchone()
            if usuario and check_password_hash(usuario['senha'], senha):
                if not usuario['ativo']:
                    flash('⚠️ Sua conta está desativada. Entre em contato com o suporte.', 'warning')
                    return render_template('login.html')
                session['usuario_id'] = usuario['id_cliente']
                session['usuario_nome'] = usuario['nome']
                session['usuario_email'] = usuario['email']
                flash(f'🎉 Bem-vindo de volta, {usuario["nome"]}!', 'success')
                next_page = request.args.get('next')
                if next_page:
                    return redirect(next_page)
                return redirect(url_for('inicio'))
            else:
                flash('❌ E-mail ou senha incorretos.', 'error')
        except mysql.connector.Error as err:
            flash(f'Erro ao fazer login: {err}', 'error')
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()
    return render_template('login.html')

@app.route('/cadastro', methods=['POST'])
def cadastro():
    nome = request.form.get('nome', '').strip()
    email = request.form.get('email', '').strip().lower()
    cpf = request.form.get('cpf', '').strip()
    telefone = request.form.get('telefone', '').strip()
    data_nascimento = request.form.get('data_nascimento')
    genero = request.form.get('genero')
    senha = request.form.get('senha', '')
    confirmar_senha = request.form.get('confirmar_senha', '')
    aceitar_termos = request.form.get('aceitar_termos')
    if not all([nome, email, cpf, senha, confirmar_senha]):
        flash('❌ Por favor, preencha todos os campos obrigatórios.', 'error')
        return redirect(url_for('login'))
    if not aceitar_termos:
        flash('❌ Você precisa aceitar os Termos de Uso e Política de Privacidade.', 'error')
        return redirect(url_for('login'))
    if senha != confirmar_senha:
        flash('❌ As senhas não coincidem.', 'error')
        return redirect(url_for('login'))
    if len(senha) < 6:
        flash('❌ A senha deve ter no mínimo 6 caracteres.', 'error')
        return redirect(url_for('login'))
    if not validar_email(email):
        flash('❌ E-mail inválido.', 'error')
        return redirect(url_for('login'))
    if not validar_cpf(cpf):
        flash('❌ CPF inválido.', 'error')
        return redirect(url_for('login'))
    cpf_formatado = formatar_cpf(cpf)
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erro ao conectar ao banco de dados.', 'error')
            return redirect(url_for('login'))
        cursor = conn.cursor()
        cursor.execute("SELECT id_cliente FROM clientes WHERE email = %s", (email,))
        if cursor.fetchone():
            flash('❌ Este e-mail já está cadastrado.', 'error')
            return redirect(url_for('login'))
        cursor.execute("SELECT id_cliente FROM clientes WHERE cpf = %s", (cpf_formatado,))
        if cursor.fetchone():
            flash('❌ Este CPF já está cadastrado.', 'error')
            return redirect(url_for('login'))
        senha_hash = generate_password_hash(senha)
        cursor.execute("""
            INSERT INTO clientes (nome, email, senha, cpf, telefone, data_nascimento, genero)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (nome, email, senha_hash, cpf_formatado, telefone, data_nascimento if data_nascimento else None, genero if genero else None))
        conn.commit()
        cliente_id = cursor.lastrowid
        cursor.execute("INSERT INTO preferencias (id_cliente, email_notificacoes, ofertas_personalizadas) VALUES (%s, TRUE, TRUE)", (cliente_id,))
        conn.commit()
        session['usuario_id'] = cliente_id
        session['usuario_nome'] = nome
        session['usuario_email'] = email
        flash(f'🎉 Cadastro realizado com sucesso! Bem-vindo, {nome}!', 'success')
        return redirect(url_for('inicio'))
    except mysql.connector.Error as err:
        flash(f'Erro ao cadastrar: {err}', 'error')
        return redirect(url_for('login'))
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/logout')
@login_required
def logout():
    nome = session.get('usuario_nome', 'Usuário')
    session.clear()
    flash(f'👋 Até logo, {nome}! Volte sempre.', 'info')
    return redirect(url_for('inicio'))

@app.route('/recuperar-senha', methods=['GET', 'POST'])
def recuperar_senha():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        if not email:
            flash('❌ Por favor, informe seu e-mail.', 'error')
            return render_template('recuperar_senha.html')
        if not validar_email(email):
            flash('❌ E-mail inválido.', 'error')
            return render_template('recuperar_senha.html')
        try:
            conn = get_db_connection()
            if not conn:
                flash('Erro ao conectar ao banco de dados.', 'error')
                return render_template('recuperar_senha.html')
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT id_cliente, nome, ativo FROM clientes WHERE email = %s", (email,))
            usuario = cursor.fetchone()
            if usuario:
                if not usuario['ativo']:
                    flash('⚠️ Esta conta está desativada. Entre em contato com o suporte.', 'warning')
                    return render_template('recuperar_senha.html')
                flash('✅ Se o e-mail estiver cadastrado, você receberá as instruções de recuperação em breve.', 'success')
                print(f"[RECUPERAÇÃO] Solicitação para: {email} - {usuario['nome']}")
            else:
                flash('✅ Se o e-mail estiver cadastrado, você receberá as instruções de recuperação em breve.', 'success')
            return redirect(url_for('login'))
        except mysql.connector.Error as err:
            flash(f'Erro ao processar solicitação: {err}', 'error')
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()
    return render_template('recuperar_senha.html')

@app.route('/minha-conta')
@login_required
def minha_conta():
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erro ao conectar ao banco de dados.', 'error')
            return redirect(url_for('inicio'))
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT c.*, COUNT(DISTINCT p.id_pedido) as total_pedidos,
            COALESCE(SUM(CASE WHEN p.status != 'cancelado' THEN p.total ELSE 0 END), 0) as total_gasto
            FROM clientes c LEFT JOIN pedidos p ON c.id_cliente = p.id_cliente
            WHERE c.id_cliente = %s GROUP BY c.id_cliente
        """, (session['usuario_id'],))
        cliente = cursor.fetchone()
        if not cliente:
            flash('Erro ao carregar dados do usuário.', 'error')
            return redirect(url_for('inicio'))
        cursor.execute("SELECT * FROM pedidos WHERE id_cliente = %s ORDER BY data_pedido DESC LIMIT 5", (session['usuario_id'],))
        pedidos = cursor.fetchall()
        cursor.execute("SELECT * FROM enderecos WHERE id_cliente = %s ORDER BY principal DESC, data_criacao DESC", (session['usuario_id'],))
        enderecos = cursor.fetchall()
        cursor.execute("SELECT * FROM preferencias WHERE id_cliente = %s", (session['usuario_id'],))
        preferencias = cursor.fetchone()
        return render_template('minha_conta.html', cliente=cliente, usuario=cliente, pedidos=pedidos, enderecos=enderecos, preferencias=preferencias)
    except mysql.connector.Error as err:
        flash(f'Erro ao carregar dados: {err}', 'error')
        return redirect(url_for('inicio'))
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/atualizar_dados', methods=['POST'])
@login_required
def atualizar_dados():
    nome = request.form.get('nome', '').strip()
    telefone = request.form.get('telefone', '').strip()
    data_nascimento = request.form.get('data_nascimento')
    genero = request.form.get('genero')
    if not nome:
        flash('❌ O nome é obrigatório.', 'error')
        return redirect(url_for('minha_conta'))
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erro ao conectar ao banco de dados.', 'error')
            return redirect(url_for('minha_conta'))
        cursor = conn.cursor()
        cursor.execute("UPDATE clientes SET nome = %s, telefone = %s, data_nascimento = %s, genero = %s WHERE id_cliente = %s",
                      (nome, telefone, data_nascimento if data_nascimento else None, genero if genero else None, session['usuario_id']))
        conn.commit()
        session['usuario_nome'] = nome
        flash('✅ Dados atualizados com sucesso!', 'success')
    except mysql.connector.Error as err:
        flash(f'Erro ao atualizar dados: {err}', 'error')
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
    return redirect(url_for('minha_conta'))

@app.route('/alterar_senha', methods=['POST'])
@login_required
def alterar_senha():
    senha_atual = request.form.get('senha_atual', '')
    nova_senha = request.form.get('nova_senha', '')
    confirmar_senha = request.form.get('confirmar_senha', '')
    if not all([senha_atual, nova_senha, confirmar_senha]):
        flash('❌ Preencha todos os campos de senha.', 'error')
        return redirect(url_for('minha_conta'))
    if nova_senha != confirmar_senha:
        flash('❌ A nova senha e a confirmação não coincidem.', 'error')
        return redirect(url_for('minha_conta'))
    if len(nova_senha) < 6:
        flash('❌ A nova senha deve ter no mínimo 6 caracteres.', 'error')
        return redirect(url_for('minha_conta'))
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erro ao conectar ao banco de dados.', 'error')
            return redirect(url_for('minha_conta'))
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT senha FROM clientes WHERE id_cliente = %s", (session['usuario_id'],))
        resultado = cursor.fetchone()
        if not resultado or not check_password_hash(resultado['senha'], senha_atual):
            flash('❌ Senha atual incorreta.', 'error')
            return redirect(url_for('minha_conta'))
        nova_senha_hash = generate_password_hash(nova_senha)
        cursor.execute("UPDATE clientes SET senha = %s WHERE id_cliente = %s", (nova_senha_hash, session['usuario_id']))
        conn.commit()
        flash('🔐 Senha alterada com sucesso!', 'success')
    except mysql.connector.Error as err:
        flash(f'Erro ao alterar senha: {err}', 'error')
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
    return redirect(url_for('minha_conta'))

@app.route('/adicionar_endereco', methods=['POST'])
@login_required
def adicionar_endereco():
    tipo = request.form.get('tipo', 'Casa')
    destinatario = request.form.get('destinatario', '').strip()
    cep = request.form.get('cep', '').strip()
    estado = request.form.get('estado', '').strip().upper()
    cidade = request.form.get('cidade', '').strip()
    bairro = request.form.get('bairro', '').strip()
    rua = request.form.get('rua', '').strip()
    numero = request.form.get('numero', '').strip()
    complemento = request.form.get('complemento', '').strip()
    principal = request.form.get('principal') == 'on'
    if not all([destinatario, cep, estado, cidade, bairro, rua, numero]):
        flash('❌ Preencha todos os campos obrigatórios do endereço.', 'error')
        return redirect(url_for('minha_conta'))
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erro ao conectar ao banco de dados.', 'error')
            return redirect(url_for('minha_conta'))
        cursor = conn.cursor()
        if principal:
            cursor.execute("UPDATE enderecos SET principal = FALSE WHERE id_cliente = %s", (session['usuario_id'],))
        cursor.execute("""
            INSERT INTO enderecos (id_cliente, tipo, destinatario, cep, estado, cidade, bairro, rua, numero, complemento, principal)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (session['usuario_id'], tipo, destinatario, cep, estado, cidade, bairro, rua, numero, complemento if complemento else None, principal))
        conn.commit()
        flash('📍 Endereço adicionado com sucesso!', 'success')
    except mysql.connector.Error as err:
        flash(f'Erro ao adicionar endereço: {err}', 'error')
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
    return redirect(url_for('minha_conta'))

@app.route('/editar_endereco/<int:id_endereco>', methods=['POST'])
@login_required
def editar_endereco(id_endereco):
    tipo = request.form.get('tipo', 'Casa')
    destinatario = request.form.get('destinatario', '').strip()
    cep = request.form.get('cep', '').strip()
    estado = request.form.get('estado', '').strip().upper()
    cidade = request.form.get('cidade', '').strip()
    bairro = request.form.get('bairro', '').strip()
    rua = request.form.get('rua', '').strip()
    numero = request.form.get('numero', '').strip()
    complemento = request.form.get('complemento', '').strip()
    principal = request.form.get('principal') == 'on'
    if not all([destinatario, cep, estado, cidade, bairro, rua, numero]):
        flash('❌ Preencha todos os campos obrigatórios do endereço.', 'error')
        return redirect(url_for('minha_conta'))
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erro ao conectar ao banco de dados.', 'error')
            return redirect(url_for('minha_conta'))
        cursor = conn.cursor()
        cursor.execute("SELECT id_endereco FROM enderecos WHERE id_endereco = %s AND id_cliente = %s", (id_endereco, session['usuario_id']))
        if not cursor.fetchone():
            flash('❌ Endereço não encontrado.', 'error')
            return redirect(url_for('minha_conta'))
        if principal:
            cursor.execute("UPDATE enderecos SET principal = FALSE WHERE id_cliente = %s AND id_endereco != %s", (session['usuario_id'], id_endereco))
        cursor.execute("""
            UPDATE enderecos SET tipo = %s, destinatario = %s, cep = %s, estado = %s, cidade = %s, bairro = %s, 
            rua = %s, numero = %s, complemento = %s, principal = %s WHERE id_endereco = %s AND id_cliente = %s
        """, (tipo, destinatario, cep, estado, cidade, bairro, rua, numero, complemento if complemento else None, principal, id_endereco, session['usuario_id']))
        conn.commit()
        flash('✅ Endereço atualizado com sucesso!', 'success')
    except mysql.connector.Error as err:
        flash(f'Erro ao atualizar endereço: {err}', 'error')
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
    return redirect(url_for('minha_conta'))

@app.route('/excluir-endereco/<int:id_endereco>', methods=['POST'])
@login_required
def excluir_endereco(id_endereco):
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erro ao conectar ao banco de dados.', 'error')
            return redirect(url_for('minha_conta'))
        cursor = conn.cursor()
        cursor.execute("DELETE FROM enderecos WHERE id_endereco = %s AND id_cliente = %s", (id_endereco, session['usuario_id']))
        conn.commit()
        if cursor.rowcount > 0:
            flash('🗑️ Endereço excluído com sucesso!', 'success')
        else:
            flash('❌ Endereço não encontrado.', 'error')
    except mysql.connector.Error as err:
        flash(f'Erro ao excluir endereço: {err}', 'error')
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
    return redirect(url_for('minha_conta'))

@app.route('/definir_endereco_principal/<int:id_endereco>', methods=['POST'])
@login_required
def definir_endereco_principal(id_endereco):
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erro ao conectar ao banco de dados.', 'error')
            return redirect(url_for('minha_conta'))
        cursor = conn.cursor()
        cursor.execute("SELECT id_endereco FROM enderecos WHERE id_endereco = %s AND id_cliente = %s", (id_endereco, session['usuario_id']))
        if not cursor.fetchone():
            flash('❌ Endereço não encontrado.', 'error')
            return redirect(url_for('minha_conta'))
        cursor.execute("UPDATE enderecos SET principal = FALSE WHERE id_cliente = %s", (session['usuario_id'],))
        cursor.execute("UPDATE enderecos SET principal = TRUE WHERE id_endereco = %s AND id_cliente = %s", (id_endereco, session['usuario_id']))
        conn.commit()
        flash('✅ Endereço principal definido com sucesso!', 'success')
    except mysql.connector.Error as err:
        flash(f'Erro ao definir endereço principal: {err}', 'error')
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
    return redirect(url_for('minha_conta'))

@app.route('/atualizar_preferencias', methods=['POST'])
@login_required
def atualizar_preferencias():
    email_notificacoes = request.form.get('email_notificacoes') == 'on'
    ofertas_personalizadas = request.form.get('ofertas_personalizadas') == 'on'
    newsletter = request.form.get('newsletter') == 'on'
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erro ao conectar ao banco de dados.', 'error')
            return redirect(url_for('minha_conta'))
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id_preferencia FROM preferencias WHERE id_cliente = %s", (session['usuario_id'],))
        existe = cursor.fetchone()
        if existe:
            cursor.execute("UPDATE preferencias SET email_notificacoes = %s, ofertas_personalizadas = %s, newsletter = %s WHERE id_cliente = %s",
                          (email_notificacoes, ofertas_personalizadas, newsletter, session['usuario_id']))
        else:
            cursor.execute("INSERT INTO preferencias (id_cliente, email_notificacoes, ofertas_personalizadas, newsletter) VALUES (%s, %s, %s, %s)",
                          (session['usuario_id'], email_notificacoes, ofertas_personalizadas, newsletter))
        conn.commit()
        flash('⚙️ Preferências atualizadas com sucesso!', 'success')
    except mysql.connector.Error as err:
        flash(f'Erro ao atualizar preferências: {err}', 'error')
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
    return redirect(url_for('minha_conta'))

@app.route('/produtos')
def listar_produtos():
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erro ao conectar ao banco de dados.', 'error')
            return render_template('produtos.html', produtos=[], categorias=[], marcas=[])
        
        cursor = conn.cursor(dictionary=True)
        categoria = request.args.get('categoria')
        marca = request.args.get('marca')
        busca = request.args.get('busca')
        
        query = "SELECT * FROM produto WHERE ativo = TRUE"
        params = []
        
        if categoria:
            query += " AND categoria = %s"
            params.append(categoria)
        
        if marca:
            query += " AND marca = %s"
            params.append(marca)
        
        if busca:
            query += " AND (nome LIKE %s OR descricao LIKE %s)"
            params.extend([f"%{busca}%", f"%{busca}%"])
        
        query += " ORDER BY data_cadastro DESC"
        
        cursor.execute(query, params)
        produtos = cursor.fetchall()
        
        # PROCESSAR IMAGENS JSON - IMPORTANTE!
        for produto in produtos:
            if produto.get('imagens'):
                try:
                    produto['imagens'] = json.loads(produto['imagens'])
                except:
                    produto['imagens'] = []
        
        cursor.execute("SELECT DISTINCT categoria FROM produto WHERE ativo = TRUE ORDER BY categoria")
        categorias = [row['categoria'] for row in cursor.fetchall()]
        
        cursor.execute("SELECT DISTINCT marca FROM produto WHERE ativo = TRUE ORDER BY marca")
        marcas = [row['marca'] for row in cursor.fetchall()]
        
        return render_template('produtos.html', produtos=produtos, categorias=categorias, marcas=marcas)
    
    except mysql.connector.Error as err:
        flash(f'Erro ao carregar produtos: {err}', 'error')
        return render_template('produtos.html', produtos=[], categorias=[], marcas=[])
    
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/produto/<int:id_produto>')
def detalhes_produto(id_produto):
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erro ao conectar ao banco de dados.', 'error')
            return redirect(url_for('listar_produtos'))
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM produto WHERE id_produto = %s AND ativo = TRUE", (id_produto,))
        produto = cursor.fetchone()
        
        if not produto:
            flash('❌ Produto não encontrado.', 'error')
            return redirect(url_for('listar_produtos'))
        
        # DEBUG - ADICIONE ESTAS LINHAS:
        print("=" * 50)
        print(f"DEBUG - ID Produto: {id_produto}")
        print(f"DEBUG - Campo imagens (raw): {produto.get('imagens')}")
        print(f"DEBUG - Tipo: {type(produto.get('imagens'))}")
        
        # PROCESSAR IMAGENS JSON
        if produto.get('imagens'):
            try:
                produto['imagens'] = json.loads(produto['imagens'])
                print(f"DEBUG - Imagens processadas: {produto['imagens']}")
                print(f"DEBUG - Tipo após processar: {type(produto['imagens'])}")
            except Exception as e:
                print(f"DEBUG - Erro ao processar: {e}")
                produto['imagens'] = []
        
        print("=" * 50)
        # FIM DEBUG
        
        cursor.execute("""
            SELECT a.*, c.nome as cliente_nome FROM avaliacoes a
            JOIN clientes c ON a.id_cliente = c.id_cliente
            WHERE a.id_produto = %s AND a.aprovado = TRUE ORDER BY a.data_avaliacao DESC
        """, (id_produto,))
        avaliacoes = cursor.fetchall()
        
        return render_template('produto_detalhes.html', produto=produto, avaliacoes=avaliacoes)
    
    except mysql.connector.Error as err:
        flash(f'Erro ao carregar produto: {err}', 'error')
        return redirect(url_for('listar_produtos'))
    
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/carrinho')
def carrinho():
    carrinho_items = session.get('carrinho', [])
    total_itens = sum(item['quantidade'] for item in carrinho_items)
    total_preco = sum(item['preco'] * item['quantidade'] for item in carrinho_items)
    return render_template('carrinho.html', produtos_carrinho=carrinho_items, total_itens=total_itens, total_preco=total_preco, total_geral=total_preco)

@app.route('/adicionar-carrinho/<int:id_produto>', methods=['POST'])
def adicionar_carrinho(id_produto):
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erro ao conectar ao banco de dados.', 'error')
            return redirect(url_for('listar_produtos'))
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM produto WHERE id_produto = %s AND ativo = TRUE", (id_produto,))
        produto = cursor.fetchone()
        if not produto:
            flash('❌ Produto não encontrado.', 'error')
            return redirect(url_for('listar_produtos'))
        if 'carrinho' not in session:
            session['carrinho'] = []
        carrinho = session['carrinho']
        produto_no_carrinho = next((item for item in carrinho if item['id_produto'] == id_produto), None)
        quantidade = int(request.form.get('quantidade', 1))
        if produto_no_carrinho:
            produto_no_carrinho['quantidade'] += quantidade
        else:
            carrinho.append({
                'id_produto': produto['id_produto'],
                'nome': produto['nome'],
                'preco': float(produto['preco']),
                'quantidade': quantidade,
                'imagem': produto['imagem'],
                'categoria': produto['categoria']
            })
        session['carrinho'] = carrinho
        session.modified = True
        flash(f'✅ {produto["nome"]} adicionado ao carrinho!', 'success')
        return redirect(url_for('listar_produtos'))
    except mysql.connector.Error as err:
        flash(f'Erro ao adicionar produto ao carrinho: {err}', 'error')
        return redirect(url_for('listar_produtos'))
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/remover-carrinho/<int:id_produto>', methods=['POST'])
def remover_carrinho(id_produto):
    if 'carrinho' in session:
        carrinho = session['carrinho']
        session['carrinho'] = [item for item in carrinho if item['id_produto'] != id_produto]
        session.modified = True
        flash('🗑️ Produto removido do carrinho!', 'success')
    return redirect(url_for('carrinho'))

@app.route('/atualizar-carrinho', methods=['POST'])
def atualizar_carrinho():
    if 'carrinho' in session:
        carrinho = session['carrinho']
        carrinho_dict = {item['id_produto']: item for item in carrinho}
        carrinho_atualizado = []
        for key, value in request.form.items():
            if key.startswith('quantidade_'):
                try:
                    id_produto = int(key.split('_')[1])
                    nova_quantidade = int(value)
                    if id_produto in carrinho_dict:
                        item = carrinho_dict[id_produto]
                        if nova_quantidade > 0:
                            item['quantidade'] = nova_quantidade
                            carrinho_atualizado.append(item)
                except ValueError:
                    continue
        session['carrinho'] = carrinho_atualizado
        session.modified = True
        flash('✅ Carrinho atualizado!', 'success')
    return redirect(url_for('carrinho'))

@app.route('/limpar-carrinho', methods=['POST'])
def limpar_carrinho():
    session.pop('carrinho', None)
    flash('🗑️ Carrinho limpo!', 'success')
    return redirect(url_for('carrinho'))

@app.route('/finalizar-carrinho', methods=['GET', 'POST'])
def finalizar_carrinho():
    # 🧱 0️⃣ Verifica login antes de qualquer coisa
    if 'usuario_id' not in session:
        flash('⚠️ Faça login para finalizar sua compra.', 'warning')
        return redirect(url_for('login', next=url_for('finalizar_carrinho')))

    produtos_carrinho = session.get('carrinho', [])
    total_geral = sum(item['preco'] * item['quantidade'] for item in produtos_carrinho)

    if request.method == 'POST':
        nome = request.form.get('nome')
        email = request.form.get('email')
        endereco = request.form.get('endereco')
        pagamento = request.form.get('pagamento')

        if not produtos_carrinho:
            flash('⚠️ Seu carrinho está vazio.', 'warning')
            return redirect(url_for('carrinho'))

        try:
            conn = get_db_connection()
            if not conn:
                flash('Erro ao conectar ao banco de dados.', 'error')
                return redirect(url_for('carrinho'))
            cursor = conn.cursor(dictionary=True)

            # 🧱 1️⃣ Verifica estoque
            for item in produtos_carrinho:
                cursor.execute("SELECT nome, estoque FROM produto WHERE id_produto = %s", (item['id_produto'],))
                produto_db = cursor.fetchone()
                if not produto_db:
                    flash(f"❌ Produto '{item['nome']}' não encontrado.", 'error')
                    return redirect(url_for('carrinho'))
                if produto_db['estoque'] <= 0:
                    flash(f"⚠️ O produto '{produto_db['nome']}' está esgotado.", 'warning')
                    return redirect(url_for('carrinho'))
                if item['quantidade'] > produto_db['estoque']:
                    flash(f"⚠️ Quantidade insuficiente de '{produto_db['nome']}' em estoque (disponível: {produto_db['estoque']}).", 'warning')
                    return redirect(url_for('carrinho'))

            # 🧾 2️⃣ Cria o pedido
            cursor.execute("""
                INSERT INTO pedidos (id_cliente, total, forma_pagamento, status, data_pedido)
                VALUES (%s, %s, %s, %s, NOW())
            """, (session['usuario_id'], total_geral, pagamento, 'concluido'))
            pedido_id = cursor.lastrowid

            # 🛒 3️⃣ Adiciona itens e atualiza estoque
            for item in produtos_carrinho:
                cursor.execute("""
                    INSERT INTO itens_pedido (id_pedido, id_produto, quantidade, preco_unitario)
                    VALUES (%s, %s, %s, %s)
                """, (pedido_id, item['id_produto'], item['quantidade'], item['preco']))

                cursor.execute("""
                    UPDATE produto
                    SET estoque = estoque - %s
                    WHERE id_produto = %s
                """, (item['quantidade'], item['id_produto']))

            conn.commit()

            # ✅ Compra finalizada
            session.pop('carrinho', None)
            flash('🎉 Compra finalizada com sucesso!', 'success')
            return redirect(url_for('compra_sucedida'))

        except mysql.connector.Error as err:
            if conn:
                conn.rollback()
            flash(f'❌ Erro ao finalizar compra: {err}', 'error')
            return redirect(url_for('carrinho'))
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()

    # GET → mostra a tela de finalização
    return render_template('finalizar-carrinho.html',
                           produtos_carrinho=produtos_carrinho,
                           total_geral=total_geral)


@app.route('/compra-sucedida')
def compra_sucedida():
    return render_template('compra-sucedida.html')

@app.route('/pix')
def pix():
    return render_template('pix.html')

@app.route('/boleto')
def boleto():
    return render_template('boleto.html')

@app.route('/cartoes')
def cartoes():
    return render_template('cartoes.html')
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        senha = request.form.get('senha', '')
        if not email or not senha:
            flash('❌ Preencha todos os campos.', 'error')
            return render_template('admin/login.html')
        try:
            conn = get_db_connection()
            if not conn:
                flash('Erro ao conectar ao banco de dados.', 'error')
                return render_template('admin/login.html')
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM funcionarios WHERE email = %s AND ativo = TRUE", (email,))
            admin = cursor.fetchone()
            if admin and check_password_hash(admin['senha'], senha):
                session['admin_id'] = admin['id_funcionario']
                session['admin_nome'] = admin['nome']
                session['admin_cargo'] = admin['cargo']
                cursor.execute("UPDATE funcionarios SET ultimo_login = NOW() WHERE id_funcionario = %s", (admin['id_funcionario'],))
                conn.commit()
                flash(f'🎉 Bem-vindo, {admin["nome"]}!', 'success')
                return redirect(url_for('admin_dashboard'))
            else:
                flash('❌ Credenciais inválidas.', 'error')
        except mysql.connector.Error as err:
            flash(f'Erro ao fazer login: {err}', 'error')
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()
    return render_template('admin/login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_id', None)
    session.pop('admin_nome', None)
    session.pop('admin_cargo', None)
    flash('👋 Logout realizado com sucesso!', 'info')
    return redirect(url_for('admin_login'))

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    # Inicializar variáveis com valores padrão
    total_clientes = 0
    total_produtos = 0
    pedidos_hoje = 0
    receita_hoje = 0
    diagnosticos_pendentes = 0
    estoque_baixo = []
    pedidos_recentes = []
    diagnosticos_recentes = []
    
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erro ao conectar ao banco de dados.', 'error')
            return render_template('admin/dashboard.html', 
                                 total_clientes=total_clientes,
                                 total_produtos=total_produtos,
                                 pedidos_hoje=pedidos_hoje,
                                 receita_hoje=receita_hoje,
                                 diagnosticos_pendentes=diagnosticos_pendentes,
                                 estoque_baixo=estoque_baixo,
                                 pedidos_recentes=pedidos_recentes,
                                 diagnosticos_recentes=diagnosticos_recentes)
        
        cursor = conn.cursor(dictionary=True)
        
        # Consulta para total de clientes
        cursor.execute("SELECT COUNT(*) as total FROM clientes WHERE ativo = TRUE")
        total_clientes = cursor.fetchone()['total']
        
        # Consulta para total de produtos
        cursor.execute("SELECT COUNT(*) as total FROM produto WHERE ativo = TRUE")
        total_produtos = cursor.fetchone()['total']
        
        # Consulta para pedidos de hoje
        cursor.execute("SELECT COUNT(*) as total FROM pedidos WHERE DATE(data_pedido) = CURDATE()")
        pedidos_hoje = cursor.fetchone()['total']
        
        # Consulta para receita de hoje
        cursor.execute("SELECT SUM(total) as total FROM pedidos WHERE DATE(data_pedido) = CURDATE() AND status != 'cancelado'")
        receita_result = cursor.fetchone()
        receita_hoje = receita_result['total'] or 0
        
        # Consulta para diagnósticos pendentes
        try:
            cursor.execute("SELECT COUNT(*) as total FROM diagnosticos WHERE status = 'recebido' OR status = 'em_analise'")
            diagnosticos_pendentes = cursor.fetchone()['total']
        except mysql.connector.Error:
            # Se a tabela diagnosticos não existir, usar 0
            diagnosticos_pendentes = 0
        
        # Consulta para estoque baixo
        try:
            cursor.execute("SELECT * FROM produto WHERE estoque <= 5 AND ativo = TRUE ORDER BY estoque ASC LIMIT 5")
            estoque_baixo = cursor.fetchall()
        except mysql.connector.Error:
            estoque_baixo = []
        
        # Consulta para pedidos recentes
        try:
            cursor.execute("SELECT p.*, c.nome as cliente_nome FROM pedidos p JOIN clientes c ON p.id_cliente = c.id_cliente ORDER BY p.data_pedido DESC LIMIT 5")
            pedidos_recentes = cursor.fetchall()
        except mysql.connector.Error:
            pedidos_recentes = []
        
        # Consulta para diagnósticos recentes
        try:
            cursor.execute("SELECT * FROM diagnosticos ORDER BY data_entrada DESC LIMIT 5")
            diagnosticos_recentes = cursor.fetchall()
        except mysql.connector.Error:
            diagnosticos_recentes = []
        
        return render_template('admin/dashboard.html', 
                             total_clientes=total_clientes,
                             total_produtos=total_produtos,
                             pedidos_hoje=pedidos_hoje,
                             receita_hoje=receita_hoje,
                             diagnosticos_pendentes=diagnosticos_pendentes,
                             estoque_baixo=estoque_baixo,
                             pedidos_recentes=pedidos_recentes,
                             diagnosticos_recentes=diagnosticos_recentes)
                             
    except mysql.connector.Error as err:
        flash(f'Erro ao carregar dashboard: {err}', 'error')
        # Retornar com valores padrão em caso de erro
        return render_template('admin/dashboard.html', 
                             total_clientes=total_clientes,
                             total_produtos=total_produtos,
                             pedidos_hoje=pedidos_hoje,
                             receita_hoje=receita_hoje,
                             diagnosticos_pendentes=diagnosticos_pendentes,
                             estoque_baixo=estoque_baixo,
                             pedidos_recentes=pedidos_recentes,
                             diagnosticos_recentes=diagnosticos_recentes)
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()    

@app.route('/admin/produtos')
@admin_required
def admin_produtos():
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erro ao conectar ao banco de dados.', 'error')
            return render_template('admin/produtos.html', produtos=[])
        cursor = conn.cursor(dictionary=True)
        categoria = request.args.get('categoria')
        busca = request.args.get('busca')
        query = "SELECT * FROM produto WHERE 1=1"
        params = []
        if categoria:
            query += " AND categoria = %s"
            params.append(categoria)
        if busca:
            query += " AND (nome LIKE %s OR marca LIKE %s)"
            params.extend([f"%{busca}%", f"%{busca}%"])
        query += " ORDER BY data_cadastro DESC"
        cursor.execute(query, params)
        produtos = cursor.fetchall()
        cursor.execute("SELECT DISTINCT categoria FROM produto ORDER BY categoria")
        categorias = [row['categoria'] for row in cursor.fetchall()]
        return render_template('admin/produtos.html', produtos=produtos, categorias=categorias)
    except mysql.connector.Error as err:
        flash(f'Erro ao carregar produtos: {err}', 'error')
        return render_template('admin/produtos.html', produtos=[])
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/admin/produto/novo', methods=['GET', 'POST'])
@admin_required
def admin_novo_produto():
    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        marca = request.form.get('marca', '').strip()
        preco = request.form.get('preco', '0').replace(',', '.')
        descricao = request.form.get('descricao', '').strip()
        estoque = request.form.get('estoque', '0')
        categoria = request.form.get('categoria', '').strip()
        peso = request.form.get('peso', '0').replace(',', '.')
        dimensoes = request.form.get('dimensoes', '').strip()
        destaque = request.form.get('destaque') == 'on'
        
        if not all([nome, marca, preco, categoria]):
            flash('❌ Preencha todos os campos obrigatórios.', 'error')
            return render_template('admin/produto_form.html')
        
        try:
            conn = get_db_connection()
            if not conn:
                flash('Erro ao conectar ao banco de dados.', 'error')
                return render_template('admin/produto_form.html')
            
            cursor = conn.cursor()
            
            imagens = []
            if 'imagens' in request.files:
                files = request.files.getlist('imagens')
                for file in files:
                    if file and allowed_file(file.filename):
                        filename = secure_filename(file.filename)
                        from uuid import uuid4
                        unique_filename = f"{uuid4().hex}_{filename}"
                        filepath = os.path.join(UPLOAD_FOLDER, unique_filename)
                        os.makedirs(os.path.dirname(filepath), exist_ok=True)
                        file.save(filepath)
                        imagens.append(unique_filename)
            
            cursor.execute("""
                INSERT INTO produto (nome, marca, preco, descricao, estoque, categoria, imagens, peso, dimensoes, destaque)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (nome, marca, float(preco), descricao, int(estoque), categoria, json.dumps(imagens) if imagens else None,
                  float(peso) if peso else 0, dimensoes, destaque))
            
            conn.commit()
            
            # CORRIGIDO: Verificar se admin_id existe antes de inserir log
            if session.get('admin_id'):
                try:
                    cursor.execute("""
                        INSERT INTO logs_sistema (id_funcionario, acao, modulo, descricao)
                        VALUES (%s, 'CADASTRO', 'PRODUTOS', %s)
                    """, (session['admin_id'], f'Produto cadastrado: {nome}'))
                    conn.commit()
                except mysql.connector.Error:
                    pass  # Ignora erro de log se falhar
            
            flash('✅ Produto cadastrado com sucesso!', 'success')
            return redirect(url_for('admin_produtos'))
        
        except mysql.connector.Error as err:
            flash(f'Erro ao cadastrar produto: {err}', 'error')
        
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()
    
    return render_template('admin/produto_form.html')

@app.route('/admin/produto/editar/<int:id_produto>', methods=['GET', 'POST'])
@admin_required
def admin_editar_produto(id_produto):
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erro ao conectar ao banco de dados.', 'error')
            return redirect(url_for('admin_produtos'))
        
        cursor = conn.cursor(dictionary=True)
        
        if request.method == 'POST':
            nome = request.form.get('nome', '').strip()
            marca = request.form.get('marca', '').strip()
            preco = request.form.get('preco', '0').replace(',', '.')
            descricao = request.form.get('descricao', '').strip()
            estoque = request.form.get('estoque', '0')
            categoria = request.form.get('categoria', '').strip()
            peso = request.form.get('peso', '0').replace(',', '.')
            dimensoes = request.form.get('dimensoes', '').strip()
            destaque = request.form.get('destaque') == 'on'
            ativo = request.form.get('ativo') == 'on'
            
            cursor.execute("SELECT imagens FROM produto WHERE id_produto = %s", (id_produto,))
            produto_atual = cursor.fetchone()
            imagens = json.loads(produto_atual['imagens']) if produto_atual['imagens'] else []
            
            if 'imagens' in request.files:
                files = request.files.getlist('imagens')
                for file in files:
                    if file and allowed_file(file.filename):
                        filename = secure_filename(file.filename)
                        from uuid import uuid4
                        unique_filename = f"{uuid4().hex}_{filename}"
                        filepath = os.path.join(UPLOAD_FOLDER, unique_filename)
                        os.makedirs(os.path.dirname(filepath), exist_ok=True)
                        file.save(filepath)
                        imagens.append(unique_filename)
            
            imagens_remover = request.form.getlist('imagens_remover')
            imagens = [img for img in imagens if img not in imagens_remover]
            
            cursor.execute("""
                UPDATE produto SET nome = %s, marca = %s, preco = %s, descricao = %s, estoque = %s, categoria = %s, 
                imagens = %s, peso = %s, dimensoes = %s, destaque = %s, ativo = %s WHERE id_produto = %s
            """, (nome, marca, float(preco), descricao, int(estoque), categoria, json.dumps(imagens) if imagens else None,
                  float(peso) if peso else 0, dimensoes, destaque, ativo, id_produto))
            
            conn.commit()
            
            # CORRIGIDO: Verificar se admin_id existe antes de inserir log
            if session.get('admin_id'):
                try:
                    cursor.execute("""
                        INSERT INTO logs_sistema (id_funcionario, acao, modulo, descricao)
                        VALUES (%s, 'EDICAO', 'PRODUTOS', %s)
                    """, (session['admin_id'], f'Produto editado: {nome} (ID: {id_produto})'))
                    conn.commit()
                except mysql.connector.Error:
                    pass  # Ignora erro de log se falhar
            
            flash('✅ Produto atualizado com sucesso!', 'success')
            return redirect(url_for('admin_produtos'))
        
        else:
            cursor.execute("SELECT * FROM produto WHERE id_produto = %s", (id_produto,))
            produto = cursor.fetchone()
            
            if not produto:
                flash('❌ Produto não encontrado.', 'error')
                return redirect(url_for('admin_produtos'))
            
            # Processar imagens para exibição
            if produto.get('imagens'):
                try:
                    produto['imagens'] = json.loads(produto['imagens'])
                except:
                    produto['imagens'] = []
            
            return render_template('admin/produto_form.html', produto=produto)
    
    except mysql.connector.Error as err:
        flash(f'Erro ao carregar produto: {err}', 'error')
        return redirect(url_for('admin_produtos'))
    
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
            
@app.route('/admin/ofertas')
def admin_ofertas():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT o.id_oferta, o.desconto, o.preco_original, o.preco_com_desconto,
               o.validade, o.ativa, p.nome AS nome_produto
        FROM ofertas o
        JOIN produto p ON o.id_produto = p.id_produto
        ORDER BY o.validade DESC
    """)
    ofertas = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('admin/ofertas.html', ofertas=ofertas)

@app.route('/admin/ofertas/nova', methods=['GET', 'POST'])
def admin_nova_oferta():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Buscar produtos ativos
    cursor.execute("SELECT id_produto, nome, preco FROM produto WHERE ativo = TRUE ORDER BY nome ASC")
    produtos = cursor.fetchall()

    if request.method == 'POST':
        id_produto = request.form.get('id_produto')
        desconto = float(request.form.get('desconto', 0))
        validade = request.form.get('validade')

        # Buscar preço original do produto
        cursor.execute("SELECT preco FROM produto WHERE id_produto = %s", (id_produto,))
        produto = cursor.fetchone()
        if not produto:
            flash('Produto não encontrado.', 'error')
            return redirect(url_for('admin_nova_oferta'))

        preco_original = float(produto['preco'])
        preco_com_desconto = preco_original - (preco_original * (desconto / 100))

        # Inserir oferta
        cursor.execute("""
            INSERT INTO ofertas (id_produto, desconto, preco_original, preco_com_desconto, validade, ativa)
            VALUES (%s, %s, %s, %s, %s, TRUE)
        """, (id_produto, desconto, preco_original, preco_com_desconto, validade))
        conn.commit()

        cursor.close()
        conn.close()
        flash('🎉 Oferta criada com sucesso!', 'success')
        return redirect(url_for('admin_ofertas'))

    cursor.close()
    conn.close()
    return render_template('admin/nova_oferta.html', produtos=produtos)

@app.route('/admin/oferta/editar/<int:id_oferta>', methods=['GET', 'POST'])
@admin_required
def admin_editar_oferta(id_oferta):
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erro ao conectar ao banco de dados.', 'error')
            return redirect(url_for('admin_ofertas'))
        
        cursor = conn.cursor(dictionary=True)
        
        if request.method == 'POST':
            id_produto = request.form.get('id_produto')
            desconto = float(request.form.get('desconto', 0))
            validade = request.form.get('validade')
            ativa = request.form.get('ativa') == 'on'
            
            # Buscar preço original do produto
            cursor.execute("SELECT preco FROM produto WHERE id_produto = %s", (id_produto,))
            produto = cursor.fetchone()
            if not produto:
                flash('Produto não encontrado.', 'error')
                return redirect(url_for('admin_editar_oferta', id_oferta=id_oferta))
            
            preco_original = float(produto['preco'])
            preco_com_desconto = preco_original - (preco_original * (desconto / 100))
            
            # Atualizar oferta
            cursor.execute("""
                UPDATE ofertas 
                SET id_produto = %s, desconto = %s, preco_original = %s, 
                    preco_com_desconto = %s, validade = %s, ativa = %s
                WHERE id_oferta = %s
            """, (id_produto, desconto, preco_original, preco_com_desconto, validade, ativa, id_oferta))
            conn.commit()
            
            # Log
            if session.get('admin_id'):
                try:
                    cursor.execute("""
                        INSERT INTO logs_sistema (id_funcionario, acao, modulo, descricao)
                        VALUES (%s, 'EDICAO', 'OFERTAS', %s)
                    """, (session['admin_id'], f'Oferta editada: ID {id_oferta}'))
                    conn.commit()
                except mysql.connector.Error:
                    pass
            
            flash('✅ Oferta atualizada com sucesso!', 'success')
            return redirect(url_for('admin_ofertas'))
        
        else:
            # GET - carregar dados da oferta
            cursor.execute("""
                SELECT o.*, p.nome as nome_produto 
                FROM ofertas o
                JOIN produto p ON o.id_produto = p.id_produto
                WHERE o.id_oferta = %s
            """, (id_oferta,))
            oferta = cursor.fetchone()
            
            if not oferta:
                flash('❌ Oferta não encontrada.', 'error')
                return redirect(url_for('admin_ofertas'))
            
            # Buscar produtos ativos
            cursor.execute("SELECT id_produto, nome, preco FROM produto WHERE ativo = TRUE ORDER BY nome ASC")
            produtos = cursor.fetchall()
            
            return render_template('admin/editar_oferta.html', oferta=oferta, produtos=produtos)
    
    except mysql.connector.Error as err:
        flash(f'Erro ao editar oferta: {err}', 'error')
        return redirect(url_for('admin_ofertas'))
    
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()


@app.route('/admin/oferta/excluir/<int:id_oferta>', methods=['GET', 'POST'])
@admin_required
def admin_excluir_oferta(id_oferta):
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erro ao conectar ao banco de dados.', 'error')
            return redirect(url_for('admin_ofertas'))
        
        cursor = conn.cursor(dictionary=True)
        
        # Buscar nome do produto para o log
        cursor.execute("""
            SELECT p.nome 
            FROM ofertas o
            JOIN produto p ON o.id_produto = p.id_produto
            WHERE o.id_oferta = %s
        """, (id_oferta,))
        oferta = cursor.fetchone()
        
        if not oferta:
            flash('❌ Oferta não encontrada.', 'error')
            return redirect(url_for('admin_ofertas'))
        
        nome_produto = oferta['nome']
        
        # Excluir oferta
        cursor.execute("DELETE FROM ofertas WHERE id_oferta = %s", (id_oferta,))
        conn.commit()
        
        # Log
        if session.get('admin_id'):
            try:
                cursor.execute("""
                    INSERT INTO logs_sistema (id_funcionario, acao, modulo, descricao)
                    VALUES (%s, 'EXCLUSAO', 'OFERTAS', %s)
                """, (session['admin_id'], f'Oferta excluída: {nome_produto} (ID: {id_oferta})'))
                conn.commit()
            except mysql.connector.Error:
                pass
        
        flash(f'🗑️ Oferta de {nome_produto} excluída com sucesso!', 'success')
    
    except mysql.connector.Error as err:
        flash(f'Erro ao excluir oferta: {err}', 'error')
    
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
    
    return redirect(url_for('admin_ofertas'))

@app.route('/admin/clientes')
@admin_required
def admin_clientes():
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erro ao conectar ao banco de dados.', 'error')
            return render_template('admin/clientes.html', clientes=[])
        cursor = conn.cursor(dictionary=True)
        busca = request.args.get('busca')
        query = "SELECT * FROM clientes WHERE 1=1"
        params = []
        if busca:
            query += " AND (nome LIKE %s OR email LIKE %s OR cpf LIKE %s)"
            params.extend([f"%{busca}%", f"%{busca}%", f"%{busca}%"])
        query += " ORDER BY data_cadastro DESC"
        cursor.execute(query, params)
        clientes = cursor.fetchall()
        return render_template('admin/clientes.html', clientes=clientes)
    except mysql.connector.Error as err:
        flash(f'Erro ao carregar clientes: {err}', 'error')
        return render_template('admin/clientes.html', clientes=[])
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/admin/cliente/<int:id_cliente>')
@admin_required
def admin_detalhes_cliente(id_cliente):
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erro ao conectar ao banco de dados.', 'error')
            return redirect(url_for('admin_clientes'))
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM clientes WHERE id_cliente = %s", (id_cliente,))
        cliente = cursor.fetchone()
        if not cliente:
            flash('❌ Cliente não encontrado.', 'error')
            return redirect(url_for('admin_clientes'))
        cursor.execute("SELECT * FROM pedidos WHERE id_cliente = %s ORDER BY data_pedido DESC", (id_cliente,))
        pedidos = cursor.fetchall()
        cursor.execute("SELECT * FROM enderecos WHERE id_cliente = %s ORDER BY principal DESC", (id_cliente,))
        enderecos = cursor.fetchall()
        return render_template('admin/cliente_detalhes.html', cliente=cliente, pedidos=pedidos, enderecos=enderecos)
    except mysql.connector.Error as err:
        flash(f'Erro ao carregar dados do cliente: {err}', 'error')
        return redirect(url_for('admin_clientes'))
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/admin/funcionarios')
@admin_required
def admin_funcionarios():
    if session['admin_cargo'] != 'admin':
        flash('❌ Acesso restrito para administradores.', 'error')
        return redirect(url_for('admin_dashboard'))
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erro ao conectar ao banco de dados.', 'error')
            return render_template('admin/funcionarios.html', funcionarios=[])
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM funcionarios ORDER BY data_cadastro DESC")
        funcionarios = cursor.fetchall()
        return render_template('admin/funcionarios.html', funcionarios=funcionarios)
    except mysql.connector.Error as err:
        flash(f'Erro ao carregar funcionários: {err}', 'error')
        return render_template('admin/funcionarios.html', funcionarios=[])
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/admin/funcionario/novo', methods=['GET', 'POST'])
@admin_required
def admin_novo_funcionario():
    if session['admin_cargo'] != 'admin':
        flash('❌ Acesso restrito para administradores.', 'error')
        return redirect(url_for('admin_dashboard'))
    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        email = request.form.get('email', '').strip().lower()
        senha = request.form.get('senha', '')
        cargo = request.form.get('cargo', 'vendedor')
        if not all([nome, email, senha]):
            flash('❌ Preencha todos os campos.', 'error')
            return render_template('admin/funcionario_form.html')
        if len(senha) < 6:
            flash('❌ A senha deve ter no mínimo 6 caracteres.', 'error')
            return render_template('admin/funcionario_form.html')
        try:
            conn = get_db_connection()
            if not conn:
                flash('Erro ao conectar ao banco de dados.', 'error')
                return render_template('admin/funcionario_form.html')
            cursor = conn.cursor()
            cursor.execute("SELECT id_funcionario FROM funcionarios WHERE email = %s", (email,))
            if cursor.fetchone():
                flash('❌ Este e-mail já está cadastrado.', 'error')
                return render_template('admin/funcionario_form.html')
            senha_hash = generate_password_hash(senha)
            cursor.execute("INSERT INTO funcionarios (nome, email, senha, cargo) VALUES (%s, %s, %s, %s)", (nome, email, senha_hash, cargo))
            conn.commit()
            cursor.execute("INSERT INTO logs_sistema (id_funcionario, acao, modulo, descricao) VALUES (%s, 'CADASTRO', 'FUNCIONARIOS', %s)",
                          (session['admin_id'], f'Funcionário cadastrado: {nome}'))
            conn.commit()
            flash('✅ Funcionário cadastrado com sucesso!', 'success')
            return redirect(url_for('admin_funcionarios'))
        except mysql.connector.Error as err:
            flash(f'Erro ao cadastrar funcionário: {err}', 'error')
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()
    return render_template('admin/funcionario_form.html')
@app.route('/admin/funcionario/editar/<int:id_funcionario>', methods=['GET', 'POST'])
@admin_required
def admin_editar_funcionario(id_funcionario):
    if session['admin_cargo'] != 'admin':
        flash('❌ Acesso restrito para administradores.', 'error')
        return redirect(url_for('admin_dashboard'))
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erro ao conectar ao banco de dados.', 'error')
            return redirect(url_for('admin_funcionarios'))
        cursor = conn.cursor(dictionary=True)
        if request.method == 'POST':
            nome = request.form.get('nome', '').strip()
            email = request.form.get('email', '').strip().lower()
            cargo = request.form.get('cargo', 'vendedor')
            ativo = request.form.get('ativo') == 'on'
            nova_senha = request.form.get('nova_senha', '').strip()
            if not all([nome, email]):
                flash('❌ Preencha todos os campos obrigatórios.', 'error')
                return redirect(url_for('admin_editar_funcionario', id_funcionario=id_funcionario))
            cursor.execute("SELECT id_funcionario FROM funcionarios WHERE email = %s AND id_funcionario != %s", (email, id_funcionario))
            if cursor.fetchone():
                flash('❌ Este e-mail já está cadastrado em outro funcionário.', 'error')
                return redirect(url_for('admin_editar_funcionario', id_funcionario=id_funcionario))
            if nova_senha:
                if len(nova_senha) < 6:
                    flash('❌ A senha deve ter no mínimo 6 caracteres.', 'error')
                    return redirect(url_for('admin_editar_funcionario', id_funcionario=id_funcionario))
                senha_hash = generate_password_hash(nova_senha)
                cursor.execute("UPDATE funcionarios SET nome = %s, email = %s, cargo = %s, ativo = %s, senha = %s WHERE id_funcionario = %s",
                              (nome, email, cargo, ativo, senha_hash, id_funcionario))
            else:
                cursor.execute("UPDATE funcionarios SET nome = %s, email = %s, cargo = %s, ativo = %s WHERE id_funcionario = %s",
                              (nome, email, cargo, ativo, id_funcionario))
            conn.commit()
            cursor.execute("INSERT INTO logs_sistema (id_funcionario, acao, modulo, descricao) VALUES (%s, 'EDICAO', 'FUNCIONARIOS', %s)",
                          (session['admin_id'], f'Funcionário editado: {nome} (ID: {id_funcionario})'))
            conn.commit()
            flash('✅ Funcionário atualizado com sucesso!', 'success')
            return redirect(url_for('admin_funcionarios'))
        else:
            cursor.execute("SELECT * FROM funcionarios WHERE id_funcionario = %s", (id_funcionario,))
            funcionario = cursor.fetchone()
            if not funcionario:
                flash('❌ Funcionário não encontrado.', 'error')
                return redirect(url_for('admin_funcionarios'))
            return render_template('admin/funcionario_form.html', funcionario=funcionario, editando=True)
    except mysql.connector.Error as err:
        flash(f'Erro ao editar funcionário: {err}', 'error')
        return redirect(url_for('admin_funcionarios'))
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/admin/funcionario/excluir/<int:id_funcionario>', methods=['POST'])
@admin_required
def admin_excluir_funcionario(id_funcionario):
    if session['admin_cargo'] != 'admin':
        flash('❌ Acesso restrito para administradores.', 'error')
        return redirect(url_for('admin_dashboard'))
    if id_funcionario == session['admin_id']:
        flash('❌ Você não pode excluir sua própria conta.', 'error')
        return redirect(url_for('admin_funcionarios'))
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erro ao conectar ao banco de dados.', 'error')
            return redirect(url_for('admin_funcionarios'))
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT nome FROM funcionarios WHERE id_funcionario = %s", (id_funcionario,))
        funcionario = cursor.fetchone()
        if not funcionario:
            flash('❌ Funcionário não encontrado.', 'error')
            return redirect(url_for('admin_funcionarios'))
        nome_funcionario = funcionario['nome']
        cursor.execute("DELETE FROM funcionarios WHERE id_funcionario = %s", (id_funcionario,))
        conn.commit()
        cursor.execute("INSERT INTO logs_sistema (id_funcionario, acao, modulo, descricao) VALUES (%s, 'EXCLUSAO', 'FUNCIONARIOS', %s)",
                      (session['admin_id'], f'Funcionário excluído: {nome_funcionario} (ID: {id_funcionario})'))
        conn.commit()
        flash(f'🗑️ Funcionário {nome_funcionario} excluído com sucesso!', 'success')
    except mysql.connector.Error as err:
        flash(f'Erro ao excluir funcionário: {err}', 'error')
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
    return redirect(url_for('admin_funcionarios'))

@app.route('/admin/funcionario/alternar-status/<int:id_funcionario>', methods=['POST'])
@admin_required
def admin_alternar_status_funcionario(id_funcionario):
    if session['admin_cargo'] != 'admin':
        flash('❌ Acesso restrito para administradores.', 'error')
        return redirect(url_for('admin_dashboard'))
    if id_funcionario == session['admin_id']:
        flash('❌ Você não pode desativar sua própria conta.', 'error')
        return redirect(url_for('admin_funcionarios'))
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erro ao conectar ao banco de dados.', 'error')
            return redirect(url_for('admin_funcionarios'))
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT nome, ativo FROM funcionarios WHERE id_funcionario = %s", (id_funcionario,))
        funcionario = cursor.fetchone()
        if not funcionario:
            flash('❌ Funcionário não encontrado.', 'error')
            return redirect(url_for('admin_funcionarios'))
        novo_status = not funcionario['ativo']
        cursor.execute("UPDATE funcionarios SET ativo = %s WHERE id_funcionario = %s", (novo_status, id_funcionario))
        conn.commit()
        acao = 'ativado' if novo_status else 'desativado'
        cursor.execute("INSERT INTO logs_sistema (id_funcionario, acao, modulo, descricao) VALUES (%s, 'ALTERACAO', 'FUNCIONARIOS', %s)",
                      (session['admin_id'], f'Funcionário {acao}: {funcionario["nome"]} (ID: {id_funcionario})'))
        conn.commit()
        status_msg = '✅ ativado' if novo_status else '🚫 desativado'
        flash(f'Funcionário {funcionario["nome"]} foi {status_msg} com sucesso!', 'success')
    except mysql.connector.Error as err:
        flash(f'Erro ao alterar status: {err}', 'error')
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
    return redirect(url_for('admin_funcionarios'))

@app.route('/admin/concorrentes')
@admin_required
def admin_concorrentes():
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erro ao conectar ao banco de dados.', 'error')
            return render_template('admin/concorrentes.html', concorrentes=[])
        
        cursor = conn.cursor(dictionary=True)
        
        # Buscar concorrentes
        cursor.execute("""
            SELECT * FROM concorrentes 
            ORDER BY data_cadastro DESC
        """)
        concorrentes = cursor.fetchall()
        
        return render_template('admin/concorrentes.html', concorrentes=concorrentes)
        
    except mysql.connector.Error as err:
        flash(f'Erro ao carregar concorrentes: {err}', 'error')
        return render_template('admin/concorrentes.html', concorrentes=[])
    
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/admin/concorrente/novo', methods=['GET', 'POST'])
@admin_required
def admin_novo_concorrente():
    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        email = request.form.get('email', '').strip()
        telefone = request.form.get('telefone', '').strip()
        empresa = request.form.get('empresa', '').strip()
        cargo = request.form.get('cargo', '').strip()
        interesse = request.form.get('interesse', '').strip()
        mensagem = request.form.get('mensagem', '').strip()
        status = request.form.get('status', 'pendente')
        
        if not all([nome, email, empresa]):
            flash('❌ Preencha todos os campos obrigatórios.', 'error')
            return render_template('admin/concorrente_form.html')
        
        try:
            conn = get_db_connection()
            if not conn:
                flash('Erro ao conectar ao banco de dados.', 'error')
                return render_template('admin/concorrente_form.html')
            
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO concorrentes (nome, email, telefone, empresa, cargo, interesse, mensagem, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (nome, email, telefone, empresa, cargo, interesse, mensagem, status))
            
            conn.commit()
            
            # Log da ação
            if session.get('admin_id'):
                try:
                    cursor.execute("""
                        INSERT INTO logs_sistema (id_funcionario, acao, modulo, descricao)
                        VALUES (%s, 'CADASTRO', 'CONCORRENTES', %s)
                    """, (session['admin_id'], f'Concorrente cadastrado: {nome}'))
                    conn.commit()
                except mysql.connector.Error:
                    pass
            
            flash('✅ Concorrente cadastrado com sucesso!', 'success')
            return redirect(url_for('admin_concorrentes'))
        
        except mysql.connector.Error as err:
            flash(f'Erro ao cadastrar concorrente: {err}', 'error')
        
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()
    
    return render_template('admin/concorrente_form.html')

@app.route('/admin/concorrente/editar/<int:id_concorrente>', methods=['GET', 'POST'])
@admin_required
def admin_editar_concorrente(id_concorrente):
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erro ao conectar ao banco de dados.', 'error')
            return redirect(url_for('admin_concorrentes'))
        
        cursor = conn.cursor(dictionary=True)
        
        if request.method == 'POST':
            nome = request.form.get('nome', '').strip()
            email = request.form.get('email', '').strip()
            telefone = request.form.get('telefone', '').strip()
            empresa = request.form.get('empresa', '').strip()
            cargo = request.form.get('cargo', '').strip()
            interesse = request.form.get('interesse', '').strip()
            mensagem = request.form.get('mensagem', '').strip()
            status = request.form.get('status', 'pendente')
            observacoes = request.form.get('observacoes', '').strip()
            
            cursor.execute("""
                UPDATE concorrentes 
                SET nome = %s, email = %s, telefone = %s, empresa = %s, cargo = %s, 
                    interesse = %s, mensagem = %s, status = %s, observacoes = %s
                WHERE id_concorrente = %s
            """, (nome, email, telefone, empresa, cargo, interesse, mensagem, status, observacoes, id_concorrente))
            
            conn.commit()
            
            # Log da ação
            if session.get('admin_id'):
                try:
                    cursor.execute("""
                        INSERT INTO logs_sistema (id_funcionario, acao, modulo, descricao)
                        VALUES (%s, 'EDICAO', 'CONCORRENTES', %s)
                    """, (session['admin_id'], f'Concorrente editado: {nome} (ID: {id_concorrente})'))
                    conn.commit()
                except mysql.connector.Error:
                    pass
            
            flash('✅ Concorrente atualizado com sucesso!', 'success')
            return redirect(url_for('admin_concorrentes'))
        
        else:
            cursor.execute("SELECT * FROM concorrentes WHERE id_concorrente = %s", (id_concorrente,))
            concorrente = cursor.fetchone()
            
            if not concorrente:
                flash('❌ Concorrente não encontrado.', 'error')
                return redirect(url_for('admin_concorrentes'))
            
            return render_template('admin/concorrente_form.html', concorrente=concorrente)
    
    except mysql.connector.Error as err:
        flash(f'Erro ao editar concorrente: {err}', 'error')
        return redirect(url_for('admin_concorrentes'))
    
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/admin/concorrente/excluir/<int:id_concorrente>', methods=['POST'])
@admin_required
def admin_excluir_concorrente(id_concorrente):
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erro ao conectar ao banco de dados.', 'error')
            return redirect(url_for('admin_concorrentes'))
        
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT nome FROM concorrentes WHERE id_concorrente = %s", (id_concorrente,))
        concorrente = cursor.fetchone()
        
        if not concorrente:
            flash('❌ Concorrente não encontrado.', 'error')
            return redirect(url_for('admin_concorrentes'))
        
        cursor.execute("DELETE FROM concorrentes WHERE id_concorrente = %s", (id_concorrente,))
        conn.commit()
        
        # Log da ação
        if session.get('admin_id'):
            try:
                cursor.execute("""
                    INSERT INTO logs_sistema (id_funcionario, acao, modulo, descricao)
                    VALUES (%s, 'EXCLUSAO', 'CONCORRENTES', %s)
                """, (session['admin_id'], f'Concorrente excluído: {concorrente["nome"]} (ID: {id_concorrente})'))
                conn.commit()
            except mysql.connector.Error:
                pass
        
        flash(f'🗑️ Concorrente {concorrente["nome"]} excluído com sucesso!', 'success')
    
    except mysql.connector.Error as err:
        flash(f'Erro ao excluir concorrente: {err}', 'error')
    
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
    
    return redirect(url_for('admin_concorrentes'))

@app.route('/admin/relatorios')
@admin_required
def admin_relatorios():
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erro ao conectar ao banco de dados.', 'error')
            return render_template('admin/relatorios.html')
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM view_relatorios_mensais LIMIT 12")
        relatorios_mensais = cursor.fetchall()
        cursor.execute("SELECT * FROM view_produtos_mais_vendidos LIMIT 10")
        produtos_mais_vendidos = cursor.fetchall()
        cursor.execute("SELECT * FROM view_clientes_ativos LIMIT 10")
        clientes_ativos = cursor.fetchall()
        cursor.execute("SELECT * FROM view_estoque_critico")
        estoque_critico = cursor.fetchall()
        return render_template('admin/relatorios.html', relatorios_mensais=relatorios_mensais,
                             produtos_mais_vendidos=produtos_mais_vendidos, clientes_ativos=clientes_ativos, estoque_critico=estoque_critico)
    except mysql.connector.Error as err:
        flash(f'Erro ao carregar relatórios: {err}', 'error')
        return render_template('admin/relatorios.html')
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/admin/contatos')
@admin_required
def admin_contatos():
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erro ao conectar ao banco de dados.', 'error')
            return render_template('admin/contatos.html', contatos=[])
        
        cursor = conn.cursor(dictionary=True)
        
        # Buscar contatos da tabela suporte
        cursor.execute("""
            SELECT * FROM suporte 
            ORDER BY data_envio DESC
        """)
        contatos = cursor.fetchall()
        
        return render_template('admin/contatos.html', contatos=contatos)
        
    except mysql.connector.Error as err:
        flash(f'Erro ao carregar contatos: {err}', 'error')
        return render_template('admin/contatos.html', contatos=[])
    
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/admin/contato/<int:id_suporte>', methods=['GET', 'POST'])
@admin_required
def admin_detalhes_contato(id_suporte):
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erro ao conectar ao banco de dados.', 'error')
            return redirect(url_for('admin_contatos'))
        
        cursor = conn.cursor(dictionary=True)
        
        if request.method == 'POST':
            status = request.form.get('status', 'pendente')
            observacoes = request.form.get('observacoes', '').strip()
            
            cursor.execute("""
                UPDATE suporte 
                SET status = %s, observacoes = %s
                WHERE id_suporte = %s
            """, (status, observacoes, id_suporte))
            
            conn.commit()
            
            flash('✅ Contato atualizado com sucesso!', 'success')
            return redirect(url_for('admin_contatos'))
        
        else:
            cursor.execute("SELECT * FROM suporte WHERE id_suporte = %s", (id_suporte,))
            contato = cursor.fetchone()
            
            if not contato:
                flash('❌ Contato não encontrado.', 'error')
                return redirect(url_for('admin_contatos'))
            
            return render_template('admin/contato_detalhes.html', contato=contato)
    
    except mysql.connector.Error as err:
        flash(f'Erro ao carregar contato: {err}', 'error')
        return redirect(url_for('admin_contatos'))
    
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/admin/contato/excluir/<int:id_suporte>', methods=['POST'])
@admin_required
def admin_excluir_contato(id_suporte):
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erro ao conectar ao banco de dados.', 'error')
            return redirect(url_for('admin_contatos'))
        
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT nome FROM suporte WHERE id_suporte = %s", (id_suporte,))
        contato = cursor.fetchone()
        
        if not contato:
            flash('❌ Contato não encontrado.', 'error')
            return redirect(url_for('admin_contatos'))
        
        cursor.execute("DELETE FROM suporte WHERE id_suporte = %s", (id_suporte,))
        conn.commit()
        
        flash(f'🗑️ Contato de {contato["nome"]} excluído com sucesso!', 'success')
    
    except mysql.connector.Error as err:
        flash(f'Erro ao excluir contato: {err}', 'error')
    
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
    
    return redirect(url_for('admin_contatos'))

@app.route('/admin/diagnosticos')
@admin_required
def admin_diagnosticos():
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erro ao conectar ao banco de dados.', 'error')
            return render_template('admin/diagnosticos.html', diagnosticos=[])
        cursor = conn.cursor(dictionary=True)
        status = request.args.get('status')
        query = "SELECT d.*, f.nome as tecnico_nome FROM diagnosticos d LEFT JOIN funcionarios f ON d.tecnico_responsavel = f.id_funcionario WHERE 1=1"
        params = []
        if status:
            query += " AND d.status = %s"
            params.append(status)
        query += " ORDER BY d.data_entrada DESC"
        cursor.execute(query, params)
        diagnosticos = cursor.fetchall()
        return render_template('admin/diagnosticos.html', diagnosticos=diagnosticos)
    except mysql.connector.Error as err:
        flash(f'Erro ao carregar diagnósticos: {err}', 'error')
        return render_template('admin/diagnosticos.html', diagnosticos=[])
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/admin/diagnostico/<int:id_diagnostico>', methods=['GET', 'POST'])
@admin_required
def admin_detalhes_diagnostico(id_diagnostico):
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erro ao conectar ao banco de dados.', 'error')
            return redirect(url_for('admin_diagnosticos'))
        cursor = conn.cursor(dictionary=True)
        if request.method == 'POST':
            status = request.form.get('status')
            relatorio_final = request.form.get('relatorio_final', '').strip()
            pecas_defeito = request.form.get('pecas_defeito', '').strip()
            orcamento = request.form.get('orcamento', '0').replace(',', '.')
            observacoes = request.form.get('observacoes', '').strip()
            cursor.execute("""
                UPDATE diagnosticos SET status = %s, relatorio_final = %s, pecas_defeito = %s, 
                orcamento = %s, observacoes = %s, tecnico_responsavel = %s WHERE id_diagnostico = %s
            """, (status, relatorio_final, pecas_defeito, float(orcamento) if orcamento else 0, observacoes, session['admin_id'], id_diagnostico))
            if status == 'concluido':
                cursor.execute("UPDATE diagnosticos SET data_conclusao = NOW() WHERE id_diagnostico = %s", (id_diagnostico,))
            conn.commit()
            flash('✅ Diagnóstico atualizado com sucesso!', 'success')
            return redirect(url_for('admin_diagnosticos'))
        else:
            cursor.execute("""
                SELECT d.*, f.nome as tecnico_nome FROM diagnosticos d 
                LEFT JOIN funcionarios f ON d.tecnico_responsavel = f.id_funcionario WHERE d.id_diagnostico = %s
            """, (id_diagnostico,))
            diagnostico = cursor.fetchone()
            if not diagnostico:
                flash('❌ Diagnóstico não encontrado.', 'error')
                return redirect(url_for('admin_diagnosticos'))
            return render_template('admin/diagnostico_detalhes.html', diagnostico=diagnostico)
    except mysql.connector.Error as err:
        flash(f'Erro ao carregar diagnóstico: {err}', 'error')
        return redirect(url_for('admin_diagnosticos'))
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/diagnostico', methods=['GET', 'POST'])
def diagnostico():
    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        email = request.form.get('email', '').strip().lower()
        telefone = request.form.get('telefone', '').strip()
        tipo_equipamento = request.form.get('tipo_equipamento', '').strip()
        marca = request.form.get('marca', '').strip()
        modelo = request.form.get('modelo', '').strip()
        problema = request.form.get('problema', '').strip()
        sintomas = request.form.get('sintomas', '').strip()
        if not all([nome, email, tipo_equipamento, problema]):
            flash('❌ Preencha todos os campos obrigatórios.', 'error')
            return render_template('diagnostico.html')
        try:
            conn = get_db_connection()
            if not conn:
                flash('Erro ao conectar ao banco de dados.', 'error')
                return render_template('diagnostico.html')
            cursor = conn.cursor()
            id_cliente = None
            if session.get('usuario_id'):
                cursor.execute("SELECT id_cliente FROM clientes WHERE id_cliente = %s", (session['usuario_id'],))
                if cursor.fetchone():
                    id_cliente = session['usuario_id']
            cursor.execute("""
                INSERT INTO diagnosticos (id_cliente, nome_cliente, email, telefone, tipo_equipamento, marca, modelo, problema, sintomas)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (id_cliente, nome, email, telefone, tipo_equipamento, marca, modelo, problema, sintomas))
            conn.commit()
            flash('✅ Diagnóstico solicitado com sucesso! Entraremos em contato em breve.', 'success')
            return redirect(url_for('inicio'))
        except mysql.connector.Error as err:
            flash(f'Erro ao solicitar diagnóstico: {err}', 'error')
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()
    return render_template('diagnostico.html')

@app.route('/api/relatorio-diagnostico/<int:id_diagnostico>')
@admin_required
def api_relatorio_diagnostico(id_diagnostico):
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Erro de conexão'}), 500
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT d.*, f.nome as tecnico_nome FROM diagnosticos d 
            LEFT JOIN funcionarios f ON d.tecnico_responsavel = f.id_funcionario WHERE d.id_diagnostico = %s
        """, (id_diagnostico,))
        diagnostico = cursor.fetchone()
        if not diagnostico:
            return jsonify({'error': 'Diagnóstico não encontrado'}), 404
        relatorio = {
            'id_diagnostico': diagnostico['id_diagnostico'],
            'cliente': diagnostico['nome_cliente'],
            'equipamento': f"{diagnostico['marca']} {diagnostico['modelo']}",
            'tipo': diagnostico['tipo_equipamento'],
            'data_entrada': diagnostico['data_entrada'].strftime('%d/%m/%Y'),
            'tecnico': diagnostico['tecnico_nome'] or 'Não atribuído',
            'problema_relatado': diagnostico['problema'],
            'sintomas': diagnostico['sintomas'],
            'diagnostico_final': diagnostico['relatorio_final'],
            'pecas_defeito': diagnostico['pecas_defeito'],
            'orcamento': f"R$ {diagnostico['orcamento']:.2f}",
            'status': diagnostico['status'],
            'observacoes': diagnostico['observacoes']
        }
        return jsonify(relatorio)
    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.route("/suporte", methods=["GET", "POST"])
def suporte():
    if request.method == "POST":
        nome = request.form.get("nome")
        email = request.form.get("email")
        mensagem = request.form.get("mensagem")
        if not (nome and email and mensagem):
            flash("Preencha todos os campos corretamente.", "warning")
            return render_template("suporte.html", titulo="Suporte")
        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            if conn is None:
                flash("Não foi possível conectar ao banco de dados.", "danger")
                return render_template("suporte.html", titulo="Suporte")
            cursor = conn.cursor()
            sql = "INSERT INTO suporte (nome, email, mensagem) VALUES (%s, %s, %s)"
            cursor.execute(sql, (nome, email, mensagem))
            conn.commit()
            flash("Mensagem enviada com sucesso!", "success")
            return redirect(url_for("suporte_sucesso"))
        except mysql.connector.Error as err:
            print(f"[ERRO MySQL] Falha ao inserir dados de suporte: {err}")
            if conn:
                conn.rollback()
            flash("Ocorreu um erro ao enviar sua mensagem. Tente novamente.", "danger")
            return render_template("suporte.html", titulo="Suporte")
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()
    return render_template("suporte.html", titulo="Suporte")

@app.route("/msg-suporte")
def suporte_sucesso():
    return render_template("msg-suporte.html", titulo="Mensagem Enviada")

@app.route('/msg-suporte')
def mensagem_suporte():
    return render_template('msg-suporte.html')

@app.route('/central-garantia')
def garantia():
    return render_template('central-garantia.html', titulo="Central de Garantia")

@app.route('/sobre')
def sobre_nos():
    return render_template('sobre.html')

@app.route('/contato', methods=['GET', 'POST'])
def contato():
    if request.method == 'POST':
        # Pegar os dados do formulário
        nome = request.form.get('nome', '').strip()
        email = request.form.get('email', '').strip()
        telefone = request.form.get('telefone', '').strip()
        assunto = request.form.get('assunto', '').strip()
        mensagem = request.form.get('mensagem', '').strip()
        
        # Validar campos obrigatórios
        if not all([nome, email, assunto, mensagem]):
            flash('❌ Por favor, preencha todos os campos obrigatórios.', 'error')
            return render_template('contato.html')
        
        try:
            conn = get_db_connection()
            if not conn:
                flash('Erro ao conectar ao banco de dados.', 'error')
                return render_template('contato.html')
            
            cursor = conn.cursor()
            
            # Inserir na tabela suporte (que já existe)
            cursor.execute("""
                INSERT INTO suporte (nome, email, mensagem, status)
                VALUES (%s, %s, %s, %s)
            """, (nome, email, f"ASSUNTO: {assunto}\nTELEFONE: {telefone}\nMENSAGEM: {mensagem}", "pendente"))
            
            conn.commit()
            
            flash('✅ Mensagem enviada com sucesso! Entraremos em contato em breve.', 'success')
            return redirect(url_for('contato_sucesso'))
            
        except mysql.connector.Error as err:
            flash(f'❌ Erro ao enviar mensagem: {err}', 'error')
            return render_template('contato.html')
        
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()

    return render_template('contato.html')

@app.route('/contato-sucesso')
def contato_sucesso():
    return render_template('contato_sucesso.html')

@app.route('/trabalhe-conosco', methods=['GET', 'POST'])
def trabalhe_conosco():
    if request.method == 'POST':
        # 1. Pegar os dados do formulário
        nome = request.form.get('nome', '').strip()
        email = request.form.get('email', '').strip()
        telefone = request.form.get('telefone', '').strip()
        formacao = request.form.get('formacao', '').strip()
        conhecimento = request.form.get('conhecimento', '').strip()
        ingles = request.form.get('ingles', '').strip()
        seguranca = request.form.get('seguranca', '').strip()
        
        # Validar campos obrigatórios
        if not all([nome, email, formacao, conhecimento, ingles, seguranca]):
            flash('❌ Por favor, preencha todos os campos obrigatórios.', 'error')
            return render_template('trabalhe_conosco.html')
        
        try:
            conn = get_db_connection()
            if not conn:
                flash('Erro ao conectar ao banco de dados.', 'error')
                return render_template('trabalhe_conosco.html')
            
            cursor = conn.cursor()
            
            # Criar mensagem com todos os dados do formulário
            mensagem_completa = f"""
            FORMAÇÃO: {formacao}
            CONHECIMENTO PRÁTICO: {conhecimento}
            INGLÊS: {ingles}
            SEGURANÇA DA INFORMAÇÃO: {seguranca}
            TELEFONE: {telefone if telefone else 'Não informado'}
            """
            
            # Inserir na tabela concorrentes
            cursor.execute("""
                INSERT INTO concorrentes (nome, email, telefone, empresa, cargo, interesse, mensagem, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (nome, email, telefone, "Candidato GHCP", "Candidato", "Trabalhe Conosco", mensagem_completa, "pendente"))
            
            conn.commit()
            
            flash('✅ Seus dados foram enviados com sucesso! Entraremos em contato em breve.', 'success')
            return redirect(url_for('trabalhe_conosco_sucesso'))
            
        except mysql.connector.Error as err:
            flash(f'❌ Erro ao enviar dados: {err}', 'error')
            return render_template('trabalhe_conosco.html')
        
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()

    # Se for um GET, apenas renderiza a página do formulário
    return render_template('trabalhe_conosco.html')

@app.route('/trabalhe-conosco-sucesso')
def trabalhe_conosco_sucesso():
    return render_template('trabalhe_conosco_sucesso.html')

@app.route('/faq')
def faq():
    return render_template('faq.html')

@app.route('/rastreio')
def rastreio():
    return render_template('rastreio.html')

@app.route('/trocas')
def trocas():
    return render_template('trocas.html')

@app.route('/termos')
def termos():
    return render_template('termos.html')

@app.route('/privacidade')
def privacidade():
    return render_template('privacidade.html')

@app.route('/cookies')
def cookies():
    return render_template('cookies.html')

@app.route('/prazos')
def prazos():
    return render_template('prazos.html')

@app.route('/formas-pagamento')
def formas_pagamento():
    return render_template('formas_pagamento.html')
@app.route('/marcas')
def marcas():
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erro ao conectar ao banco de dados.', 'error')
            return render_template('marcas.html', marcas=[])
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT marca, COUNT(*) as total_produtos, MIN(preco) as preco_minimo, MAX(preco) as preco_maximo
            FROM produto WHERE ativo = TRUE GROUP BY marca ORDER BY marca
        """)
        marcas_lista = cursor.fetchall()
        return render_template('marcas.html', marcas=marcas_lista)
    except mysql.connector.Error as err:
        flash(f'Erro ao carregar marcas: {err}', 'error')
        return render_template('marcas.html', marcas=[])
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/categorias')
def categorias():
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erro ao conectar ao banco de dados.', 'error')
            return render_template('categorias.html', categorias=[])
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT categoria, COUNT(*) as total_produtos FROM produto 
            WHERE ativo = TRUE GROUP BY categoria ORDER BY categoria
        """)
        categorias_lista = cursor.fetchall()
        return render_template('categorias.html', categorias=categorias_lista)
    except mysql.connector.Error as err:
        flash(f'Erro ao carregar categorias: {err}', 'error')
        return render_template('categorias.html', categorias=[])
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/ofertas')
def ofertas():
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erro ao conectar ao banco de dados.', 'error')
            return render_template('ofertas.html', produtos=[])
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM produto WHERE ativo = TRUE ORDER BY preco ASC LIMIT 20")
        produtos = cursor.fetchall()
        return render_template('ofertas.html', produtos=produtos)
    except mysql.connector.Error as err:
        flash(f'Erro ao carregar ofertas: {err}', 'error')
        return render_template('ofertas.html', produtos=[])
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/lancamentos')
def lancamentos():
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erro ao conectar ao banco de dados.', 'error')
            return render_template('lancamentos.html', produtos=[])
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM produto WHERE ativo = TRUE ORDER BY data_cadastro DESC LIMIT 20")
        produtos = cursor.fetchall()
        return render_template('lancamentos.html', produtos=produtos)
    except mysql.connector.Error as err:
        flash(f'Erro ao carregar lançamentos: {err}', 'error')
        return render_template('lancamentos.html', produtos=[])
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/condicoes')
def condicoes():
    return render_template('condicoes.html')

@app.route('/monte-seu-pc')
def monte_seu_pc():
    return render_template('monte_seu_pc.html')

@app.route('/assistencia')
def assistencia():
    return render_template('assistencia.html')

@app.route('/blog')
def blog():
    return render_template('blog.html')

@app.route('/newsletter')
def newsletter():
    return render_template('newsletter.html')

def criar_admin_padrao():
    try:
        conn = get_db_connection()
        if not conn:
            print("❌ Erro ao conectar ao banco para criar admin padrão")
            return
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id_funcionario FROM funcionarios WHERE email = 'admin@ghcp.com'")
        admin_existe = cursor.fetchone()
        if not admin_existe:
            senha_hash = generate_password_hash('admin123')
            cursor.execute("""
                INSERT INTO funcionarios (nome, email, senha, cargo, ativo)
                VALUES (%s, %s, %s, %s, %s)
            """, ('Administrador', 'admin@ghcp.com', senha_hash, 'admin', True))
            conn.commit()
            print("✅ Admin padrão criado com sucesso!")
            print("📧 Email: admin@ghcp.com")
            print("🔑 Senha: admin123")
        else:
            print("ℹ️ Admin padrão já existe no banco")
        cursor.close()
        conn.close()
    except mysql.connector.Error as err:
        print(f"❌ Erro ao criar admin padrão: {err}")

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 Loja GHCP - Sistema de E-commerce + Admin")
    print("=" * 60)
    criar_admin_padrao()
    print("✅ Servidor Flask iniciado com sucesso!")
    print(f"🌐 Site: http://localhost:5000")
    print(f"🛡️ Admin: http://localhost:5000/admin/login")
    print("=" * 60)
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.run(debug=True, host='0.0.0.0', port=5000)