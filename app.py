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

# ============================================
# CONFIGURAÇÃO DO BANCO DE DADOS
# ============================================

DB_CONFIG = {
    'host': 'localhost',
    'port': '3306',
    'user': 'root',
    'password': '',  # ⚠️ Coloque sua senha do MySQL aqui
    'database': 'loja_informatica'
}

# Configurações de upload
UPLOAD_FOLDER = 'static/uploads/produtos'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db_connection():
    """Cria e retorna uma conexão com o banco de dados"""
    try:
        return mysql.connector.connect(**DB_CONFIG)
    except mysql.connector.Error as err:
        print(f"Erro ao conectar ao banco de dados: {err}")
        return None

# ============================================
# DECORATORS E FUNÇÕES AUXILIARES
# ============================================

def login_required(f):
    """Decorator para proteger rotas que precisam de autenticação"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            flash('⚠️ Por favor, faça login para acessar esta página.', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator para verificar se é admin"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            flash('⚠️ Acesso restrito para administradores.', 'warning')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

def validar_cpf(cpf):
    """Valida formato do CPF"""
    cpf = re.sub(r'\D', '', cpf)
    if len(cpf) != 11:
        return False
    
    # Verificar se todos os dígitos são iguais
    if cpf == cpf[0] * 11:
        return False
    
    # Validação do primeiro dígito verificador
    soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
    digito1 = (soma * 10 % 11) % 10
    
    if digito1 != int(cpf[9]):
        return False
    
    # Validação do segundo dígito verificador
    soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
    digito2 = (soma * 10 % 11) % 10
    
    return digito2 == int(cpf[10])

def validar_email(email):
    """Valida formato de email"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def formatar_cpf(cpf):
    """Formata CPF para o padrão XXX.XXX.XXX-XX"""
    cpf = re.sub(r'\D', '', cpf)
    return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"

def formatar_telefone(telefone):
    """Formata telefone para o padrão (XX) XXXXX-XXXX"""
    telefone = re.sub(r'\D', '', telefone)
    if len(telefone) == 11:
        return f"({telefone[:2]}) {telefone[2:7]}-{telefone[7:]}"
    elif len(telefone) == 10:
        return f"({telefone[:2]}) {telefone[2:6]}-{telefone[6:]}"
    return telefone

# ============================================
# ROTAS DE AUTENTICAÇÃO
# ============================================

@app.route('/')
def inicio():
    """Página inicial"""
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erro ao conectar ao banco de dados.', 'error')
            return render_template('index.html', produtos=[])
        
        cursor = conn.cursor(dictionary=True)
        
        # Buscar produtos em destaque
        cursor.execute("""
            SELECT * FROM produto 
            WHERE ativo = TRUE 
            ORDER BY data_cadastro DESC 
            LIMIT 8
        """)
        
        produtos = cursor.fetchall()
        
        return render_template('index.html', produtos=produtos)
    
    except mysql.connector.Error as err:
        flash(f'Erro ao carregar produtos: {err}', 'error')
        return render_template('index.html', produtos=[])
    
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Página e processamento de login"""
    # Se já estiver logado, redireciona
    if 'usuario_id' in session:
        return redirect(url_for('inicio'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        senha = request.form.get('senha', '')
        
        # Validações básicas
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
            
            # Buscar usuário pelo email
            cursor.execute("""
                SELECT id_cliente, nome, email, senha, ativo 
                FROM clientes 
                WHERE email = %s
            """, (email,))
            
            usuario = cursor.fetchone()
            
            if usuario and check_password_hash(usuario['senha'], senha):
                if not usuario['ativo']:
                    flash('⚠️ Sua conta está desativada. Entre em contato com o suporte.', 'warning')
                    return render_template('login.html')
                
                # Login bem-sucedido
                session['usuario_id'] = usuario['id_cliente']
                session['usuario_nome'] = usuario['nome']
                session['usuario_email'] = usuario['email']
                
                flash(f'🎉 Bem-vindo de volta, {usuario["nome"]}!', 'success')
                
                # Redirecionar para página anterior ou início
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
    """Processamento de cadastro"""
    # Coletar dados do formulário
    nome = request.form.get('nome', '').strip()
    email = request.form.get('email', '').strip().lower()
    cpf = request.form.get('cpf', '').strip()
    telefone = request.form.get('telefone', '').strip()
    data_nascimento = request.form.get('data_nascimento')
    genero = request.form.get('genero')
    senha = request.form.get('senha', '')
    confirmar_senha = request.form.get('confirmar_senha', '')
    aceitar_termos = request.form.get('aceitar_termos')
    
    # Validações
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
    
    # Formatar CPF
    cpf_formatado = formatar_cpf(cpf)
    
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erro ao conectar ao banco de dados.', 'error')
            return redirect(url_for('login'))
        
        cursor = conn.cursor()
        
        # Verificar se email já existe
        cursor.execute("SELECT id_cliente FROM clientes WHERE email = %s", (email,))
        if cursor.fetchone():
            flash('❌ Este e-mail já está cadastrado.', 'error')
            return redirect(url_for('login'))
        
        # Verificar se CPF já existe
        cursor.execute("SELECT id_cliente FROM clientes WHERE cpf = %s", (cpf_formatado,))
        if cursor.fetchone():
            flash('❌ Este CPF já está cadastrado.', 'error')
            return redirect(url_for('login'))
        
        # Hash da senha
        senha_hash = generate_password_hash(senha)
        
        # Inserir novo cliente
        cursor.execute("""
            INSERT INTO clientes (nome, email, senha, cpf, telefone, data_nascimento, genero)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (nome, email, senha_hash, cpf_formatado, telefone, 
              data_nascimento if data_nascimento else None, 
              genero if genero else None))
        
        conn.commit()
        cliente_id = cursor.lastrowid
        
        # Criar preferências padrão
        cursor.execute("""
            INSERT INTO preferencias (id_cliente, email_notificacoes, ofertas_personalizadas)
            VALUES (%s, TRUE, TRUE)
        """, (cliente_id,))
        
        conn.commit()
        
        # Login automático após cadastro
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
    """Fazer logout do sistema"""
    nome = session.get('usuario_nome', 'Usuário')
    session.clear()
    flash(f'👋 Até logo, {nome}! Volte sempre.', 'info')
    return redirect(url_for('inicio'))

@app.route('/recuperar-senha', methods=['GET', 'POST'])
def recuperar_senha():
    """Página de recuperação de senha"""
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
                
                # Aqui você implementaria o envio de email com token
                # Por enquanto, vamos apenas registrar a solicitação no banco
                
                # IMPORTANTE: Em produção, você deve:
                # 1. Gerar um token único
                # 2. Salvar o token no banco com prazo de validade
                # 3. Enviar email com link contendo o token
                # 4. Criar rota para resetar senha com o token
                
                flash('✅ Se o e-mail estiver cadastrado, você receberá as instruções de recuperação em breve.', 'success')
                
                # Log da tentativa (opcional)
                print(f"[RECUPERAÇÃO] Solicitação para: {email} - {usuario['nome']}")
            else:
                # Por segurança, não informar se o email existe ou não
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
    """Página da conta do usuário"""
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erro ao conectar ao banco de dados.', 'error')
            return redirect(url_for('inicio'))
        
        cursor = conn.cursor(dictionary=True)
        
        # Buscar dados do cliente
        cursor.execute("""
            SELECT c.*, 
                   COUNT(DISTINCT p.id_pedido) as total_pedidos,
                   COALESCE(SUM(CASE WHEN p.status != 'cancelado' THEN p.total ELSE 0 END), 0) as total_gasto
            FROM clientes c
            LEFT JOIN pedidos p ON c.id_cliente = p.id_cliente
            WHERE c.id_cliente = %s
            GROUP BY c.id_cliente
        """, (session['usuario_id'],))
        
        cliente = cursor.fetchone()
        
        if not cliente:
            flash('Erro ao carregar dados do usuário.', 'error')
            return redirect(url_for('inicio'))
        
        # Buscar pedidos recentes
        cursor.execute("""
            SELECT * FROM pedidos 
            WHERE id_cliente = %s 
            ORDER BY data_pedido DESC 
            LIMIT 5
        """, (session['usuario_id'],))
        
        pedidos = cursor.fetchall()
        
        # Buscar endereços
        cursor.execute("""
            SELECT * FROM enderecos 
            WHERE id_cliente = %s 
            ORDER BY principal DESC, data_criacao DESC
        """, (session['usuario_id'],))
        
        enderecos = cursor.fetchall()
        
        # Buscar preferências
        cursor.execute("""
            SELECT * FROM preferencias 
            WHERE id_cliente = %s
        """, (session['usuario_id'],))
        
        preferencias = cursor.fetchone()
        
        return render_template('minha_conta.html', 
                             cliente=cliente, 
                             pedidos=pedidos,
                             enderecos=enderecos,
                             preferencias=preferencias)
    
    except mysql.connector.Error as err:
        flash(f'Erro ao carregar dados: {err}', 'error')
        return redirect(url_for('inicio'))
    
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/atualizar-perfil', methods=['POST'])
@login_required
def atualizar_perfil():
    """Atualizar dados do perfil"""
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
        
        cursor.execute("""
            UPDATE clientes 
            SET nome = %s, telefone = %s, data_nascimento = %s, genero = %s
            WHERE id_cliente = %s
        """, (nome, telefone, data_nascimento if data_nascimento else None, 
              genero if genero else None, session['usuario_id']))
        
        conn.commit()
        
        # Atualizar sessão
        session['usuario_nome'] = nome
        
        flash('✅ Perfil atualizado com sucesso!', 'success')
    
    except mysql.connector.Error as err:
        flash(f'Erro ao atualizar perfil: {err}', 'error')
    
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
    
    return redirect(url_for('minha_conta'))

@app.route('/alterar-senha', methods=['POST'])
@login_required
def alterar_senha():
    """Alterar senha do usuário"""
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
        
        # Verificar senha atual
        cursor.execute("SELECT senha FROM clientes WHERE id_cliente = %s", (session['usuario_id'],))
        resultado = cursor.fetchone()
        
        if not resultado or not check_password_hash(resultado['senha'], senha_atual):
            flash('❌ Senha atual incorreta.', 'error')
            return redirect(url_for('minha_conta'))
        
        # Atualizar senha (o trigger vai registrar no histórico automaticamente)
        nova_senha_hash = generate_password_hash(nova_senha)
        cursor.execute("""
            UPDATE clientes 
            SET senha = %s 
            WHERE id_cliente = %s
        """, (nova_senha_hash, session['usuario_id']))
        
        conn.commit()
        
        flash('🔒 Senha alterada com sucesso!', 'success')
    
    except mysql.connector.Error as err:
        flash(f'Erro ao alterar senha: {err}', 'error')
    
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
    
    return redirect(url_for('minha_conta'))

@app.route('/adicionar-endereco', methods=['POST'])
@login_required
def adicionar_endereco():
    """Adicionar novo endereço"""
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
        
        cursor.execute("""
            INSERT INTO enderecos 
            (id_cliente, tipo, destinatario, cep, estado, cidade, bairro, rua, numero, complemento, principal)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (session['usuario_id'], tipo, destinatario, cep, estado, cidade, 
              bairro, rua, numero, complemento if complemento else None, principal))
        
        conn.commit()
        
        flash('📍 Endereço adicionado com sucesso!', 'success')
    
    except mysql.connector.Error as err:
        flash(f'Erro ao adicionar endereço: {err}', 'error')
    
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
    
    return redirect(url_for('minha_conta'))

@app.route('/excluir-endereco/<int:id_endereco>', methods=['POST'])
@login_required
def excluir_endereco(id_endereco):
    """Excluir endereço"""
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erro ao conectar ao banco de dados.', 'error')
            return redirect(url_for('minha_conta'))
        
        cursor = conn.cursor()
        
        # Verificar se o endereço pertence ao usuário
        cursor.execute("""
            DELETE FROM enderecos 
            WHERE id_endereco = %s AND id_cliente = %s
        """, (id_endereco, session['usuario_id']))
        
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

# ============================================
# ROTAS DE PRODUTOS E CARRINHO
# ============================================

@app.route('/produtos')
def listar_produtos():
    """Listar produtos"""
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erro ao conectar ao banco de dados.', 'error')
            return render_template('produtos.html', produtos=[])
        
        cursor = conn.cursor(dictionary=True)
        
        # Filtros
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
        
        # Buscar categorias e marcas para filtros
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
    """Detalhes de um produto específico"""
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
        
        # Buscar avaliações do produto
        cursor.execute("""
            SELECT a.*, c.nome as cliente_nome 
            FROM avaliacoes a
            JOIN clientes c ON a.id_cliente = c.id_cliente
            WHERE a.id_produto = %s AND a.aprovado = TRUE
            ORDER BY a.data_avaliacao DESC
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
    """Página do carrinho"""
    # Carrinho será gerenciado via sessão
    carrinho_items = session.get('carrinho', [])
    
    # Calcular totais
    total_itens = sum(item['quantidade'] for item in carrinho_items)
    total_preco = sum(item['preco'] * item['quantidade'] for item in carrinho_items)
    
    return render_template('carrinho.html', produtos_carrinho=carrinho_items, total_itens=total_itens, total_preco=total_preco,total_geral=total_preco)

@app.route('/adicionar-carrinho/<int:id_produto>', methods=['POST'])
def adicionar_carrinho(id_produto):
    """Adicionar produto ao carrinho"""
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erro ao conectar ao banco de dados.', 'error')
            return redirect(url_for('listar_produtos'))
        
        cursor = conn.cursor(dictionary=True)
        
        # Buscar informações do produto
        cursor.execute("SELECT * FROM produto WHERE id_produto = %s AND ativo = TRUE", (id_produto,))
        produto = cursor.fetchone()
        
        if not produto:
            flash('❌ Produto não encontrado.', 'error')
            return redirect(url_for('listar_produtos'))
        
        # Inicializar carrinho na sessão se não existir
        if 'carrinho' not in session:
            session['carrinho'] = []
        
        # Verificar se o produto já está no carrinho
        carrinho = session['carrinho']
        produto_no_carrinho = next((item for item in carrinho if item['id_produto'] == id_produto), None)
        
        quantidade = int(request.form.get('quantidade', 1))
        
        if produto_no_carrinho:
            # Atualizar quantidade se já estiver no carrinho
            produto_no_carrinho['quantidade'] += quantidade
        else:
            # Adicionar novo item ao carrinho
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
    """Remover produto do carrinho"""
    if 'carrinho' in session:
        carrinho = session['carrinho']
        # Filtrar itens, removendo o produto especificado
        session['carrinho'] = [item for item in carrinho if item['id_produto'] != id_produto]
        session.modified = True
        flash('🗑️ Produto removido do carrinho!', 'success')
    
    return redirect(url_for('carrinho'))

@app.route('/atualizar-carrinho', methods=['POST'])
def atualizar_carrinho():
    """Atualizar quantidade de produtos no carrinho lendo todos os campos do formulário."""
    if 'carrinho' in session:
        carrinho = session['carrinho']
        
        # Cria um dicionário de IDs para acesso rápido (simplifica a atualização)
        carrinho_dict = {item['id_produto']: item for item in carrinho}
        
        # Lista temporária para reconstruir o carrinho após as mudanças
        carrinho_atualizado = []
        
        # Itera sobre os dados enviados pelo formulário
        for key, value in request.form.items():
            if key.startswith('quantidade_'):
                try:
                    # Extrai o ID do produto do nome do campo (ex: 'quantidade_123' -> 123)
                    id_produto = int(key.split('_')[1])
                    nova_quantidade = int(value)
                    
                    if id_produto in carrinho_dict:
                        item = carrinho_dict[id_produto]
                        
                        if nova_quantidade > 0:
                            # Se a quantidade for válida, atualiza
                            item['quantidade'] = nova_quantidade
                            # Adiciona à lista atualizada (se não for removido)
                            carrinho_atualizado.append(item) 
                        # Se nova_quantidade <= 0, o item é removido implicitamente por não ser adicionado à lista atualizada

                except ValueError:
                    # Ignora campos que não são números
                    continue
            
            # Garante que itens não presentes no form (ex: se você tivesse outro campo não quantidade) 
            # não seriam perdidos, mas com a lógica acima ele deve funcionar.
            # No seu caso, o carrinho atualizado é a lista de itens válidos do carrinho_dict.

        # O novo carrinho são os itens que sobreviveram ao loop.
        session['carrinho'] = carrinho_atualizado
        session.modified = True
        
        flash('✅ Carrinho atualizado!', 'success')
    
    return redirect(url_for('carrinho'))

@app.route('/limpar-carrinho', methods=['POST'])
def limpar_carrinho():
    """Limpar todo o carrinho"""
    session.pop('carrinho', None)
    flash('🗑️ Carrinho limpo!', 'success')
    return redirect(url_for('carrinho'))

@app.route('/pix')
def pix():
    return render_template('pix.html')

@app.route('/boleto')
def boleto():
    return render_template('boleto.html')

@app.route('/cartoes-credito')
def cartoes():
    return render_template('cartoes-credito.html')

# ============================================
# ROTAS DO PAINEL ADMINISTRATIVO
# ============================================

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Login do administrador"""
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
            
            cursor.execute("""
                SELECT * FROM funcionarios 
                WHERE email = %s AND ativo = TRUE
            """, (email,))
            
            admin = cursor.fetchone()
            
            if admin and check_password_hash(admin['senha'], senha):
                # Login bem-sucedido
                session['admin_id'] = admin['id_funcionario']
                session['admin_nome'] = admin['nome']
                session['admin_cargo'] = admin['cargo']
                
                # Atualizar último login
                cursor.execute("""
                    UPDATE funcionarios 
                    SET ultimo_login = NOW() 
                    WHERE id_funcionario = %s
                """, (admin['id_funcionario'],))
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
    """Logout do admin"""
    session.pop('admin_id', None)
    session.pop('admin_nome', None)
    session.pop('admin_cargo', None)
    flash('👋 Logout realizado com sucesso!', 'info')
    return redirect(url_for('admin_login'))

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    """Dashboard administrativo"""
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erro ao conectar ao banco de dados.', 'error')
            return render_template('admin/dashboard.html')
        
        cursor = conn.cursor(dictionary=True)
        
        # Estatísticas gerais
        cursor.execute("SELECT COUNT(*) as total FROM clientes WHERE ativo = TRUE")
        total_clientes = cursor.fetchone()['total']
        
        cursor.execute("SELECT COUNT(*) as total FROM produto WHERE ativo = TRUE")
        total_produtos = cursor.fetchone()['total']
        
        cursor.execute("""
            SELECT COUNT(*) as total 
            FROM pedidos 
            WHERE DATE(data_pedido) = CURDATE()
        """)
        pedidos_hoje = cursor.fetchone()['total']
        
        cursor.execute("""
            SELECT SUM(total) as total 
            FROM pedidos 
            WHERE DATE(data_pedido) = CURDATE() AND status != 'cancelado'
        """)
        receita_hoje = cursor.fetchone()['total'] or 0
        
        cursor.execute("""
            SELECT COUNT(*) as total 
            FROM diagnosticos 
            WHERE status = 'recebido' OR status = 'em_analise'
        """)
        diagnosticos_pendentes = cursor.fetchone()['total']
        
        # Produtos com estoque baixo
        cursor.execute("""
            SELECT * FROM produto 
            WHERE estoque <= 5 AND ativo = TRUE 
            ORDER BY estoque ASC 
            LIMIT 5
        """)
        estoque_baixo = cursor.fetchall()
        
        # Pedidos recentes
        cursor.execute("""
            SELECT p.*, c.nome as cliente_nome 
            FROM pedidos p
            JOIN clientes c ON p.id_cliente = c.id_cliente
            ORDER BY p.data_pedido DESC 
            LIMIT 5
        """)
        pedidos_recentes = cursor.fetchall()
        
        # Diagnosticos recentes
        cursor.execute("""
            SELECT * FROM diagnosticos 
            ORDER BY data_entrada DESC 
            LIMIT 5
        """)
        diagnosticos_recentes = cursor.fetchall()
        
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
        return render_template('admin/dashboard.html')
    
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/admin/produtos')
@admin_required
def admin_produtos():
    """Gerenciamento de produtos"""
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erro ao conectar ao banco de dados.', 'error')
            return render_template('admin/produtos.html', produtos=[])
        
        cursor = conn.cursor(dictionary=True)
        
        # Filtros
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
        
        # Buscar categorias para filtro
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
    """Adicionar novo produto"""
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
            
            # Processar upload de imagens
            imagens = []
            if 'imagens' in request.files:
                files = request.files.getlist('imagens')
                for file in files:
                    if file and allowed_file(file.filename):
                        filename = secure_filename(file.filename)
                        # Criar nome único
                        from uuid import uuid4
                        unique_filename = f"{uuid4().hex}_{filename}"
                        filepath = os.path.join(UPLOAD_FOLDER, unique_filename)
                        
                        # Criar diretório se não existir
                        os.makedirs(os.path.dirname(filepath), exist_ok=True)
                        file.save(filepath)
                        
                        imagens.append(unique_filename)
            
            # Inserir produto
            cursor.execute("""
                INSERT INTO produto 
                (nome, marca, preco, descricao, estoque, categoria, imagens, peso, dimensoes, destaque)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (nome, marca, float(preco), descricao, int(estoque), categoria,
                  json.dumps(imagens) if imagens else None, 
                  float(peso) if peso else 0, 
                  dimensoes, destaque))
            
            conn.commit()
            
            # Registrar log
            cursor.execute("""
                INSERT INTO logs_sistema (id_funcionario, acao, modulo, descricao)
                VALUES (%s, 'CADASTRO', 'PRODUTOS', %s)
            """, (session['admin_id'], f'Produto cadastrado: {nome}'))
            conn.commit()
            
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
    """Editar produto existente"""
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
            
            # Buscar imagens atuais
            cursor.execute("SELECT imagens FROM produto WHERE id_produto = %s", (id_produto,))
            produto_atual = cursor.fetchone()
            imagens = json.loads(produto_atual['imagens']) if produto_atual['imagens'] else []
            
            # Processar novas imagens
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
            
            # Remover imagens selecionadas
            imagens_remover = request.form.getlist('imagens_remover')
            imagens = [img for img in imagens if img not in imagens_remover]
            
            # Atualizar produto
            cursor.execute("""
                UPDATE produto 
                SET nome = %s, marca = %s, preco = %s, descricao = %s, 
                    estoque = %s, categoria = %s, imagens = %s, peso = %s, 
                    dimensoes = %s, destaque = %s, ativo = %s
                WHERE id_produto = %s
            """, (nome, marca, float(preco), descricao, int(estoque), categoria,
                  json.dumps(imagens) if imagens else None,
                  float(peso) if peso else 0, dimensoes, destaque, ativo, id_produto))
            
            conn.commit()
            
            # Registrar log
            cursor.execute("""
                INSERT INTO logs_sistema (id_funcionario, acao, modulo, descricao)
                VALUES (%s, 'EDICAO', 'PRODUTOS', %s)
            """, (session['admin_id'], f'Produto editado: {nome} (ID: {id_produto})'))
            conn.commit()
            
            flash('✅ Produto atualizado com sucesso!', 'success')
            return redirect(url_for('admin_produtos'))
        
        else:
            # Carregar dados do produto
            cursor.execute("SELECT * FROM produto WHERE id_produto = %s", (id_produto,))
            produto = cursor.fetchone()
            
            if not produto:
                flash('❌ Produto não encontrado.', 'error')
                return redirect(url_for('admin_produtos'))
            
            # Converter imagens JSON para lista
            if produto['imagens']:
                produto['imagens'] = json.loads(produto['imagens'])
            else:
                produto['imagens'] = []
            
            return render_template('admin/produto_form.html', produto=produto)
    
    except mysql.connector.Error as err:
        flash(f'Erro ao carregar produto: {err}', 'error')
        return redirect(url_for('admin_produtos'))
    
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/admin/clientes')
@admin_required
def admin_clientes():
    """Gerenciamento de clientes"""
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erro ao conectar ao banco de dados.', 'error')
            return render_template('admin/clientes.html', clientes=[])
        
        cursor = conn.cursor(dictionary=True)
        
        # Filtros
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
    """Detalhes do cliente"""
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erro ao conectar ao banco de dados.', 'error')
            return redirect(url_for('admin_clientes'))
        
        cursor = conn.cursor(dictionary=True)
        
        # Dados do cliente
        cursor.execute("SELECT * FROM clientes WHERE id_cliente = %s", (id_cliente,))
        cliente = cursor.fetchone()
        
        if not cliente:
            flash('❌ Cliente não encontrado.', 'error')
            return redirect(url_for('admin_clientes'))
        
        # Pedidos do cliente
        cursor.execute("""
            SELECT * FROM pedidos 
            WHERE id_cliente = %s 
            ORDER BY data_pedido DESC
        """, (id_cliente,))
        pedidos = cursor.fetchall()
        
        # Endereços
        cursor.execute("""
            SELECT * FROM enderecos 
            WHERE id_cliente = %s 
            ORDER BY principal DESC
        """, (id_cliente,))
        enderecos = cursor.fetchall()
        
        return render_template('admin/cliente_detalhes.html', 
                             cliente=cliente, 
                             pedidos=pedidos, 
                             enderecos=enderecos)
    
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
    """Gerenciamento de funcionários"""
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
    """Adicionar novo funcionário"""
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
            
            # Verificar se email já existe
            cursor.execute("SELECT id_funcionario FROM funcionarios WHERE email = %s", (email,))
            if cursor.fetchone():
                flash('❌ Este e-mail já está cadastrado.', 'error')
                return render_template('admin/funcionario_form.html')
            
            # Hash da senha
            senha_hash = generate_password_hash(senha)
            
            cursor.execute("""
                INSERT INTO funcionarios (nome, email, senha, cargo)
                VALUES (%s, %s, %s, %s)
            """, (nome, email, senha_hash, cargo))
            
            conn.commit()
            
            # Registrar log
            cursor.execute("""
                INSERT INTO logs_sistema (id_funcionario, acao, modulo, descricao)
                VALUES (%s, 'CADASTRO', 'FUNCIONARIOS', %s)
            """, (session['admin_id'], f'Funcionário cadastrado: {nome}'))
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

@app.route('/admin/relatorios')
@admin_required
def admin_relatorios():
    """Relatórios e estatísticas"""
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erro ao conectar ao banco de dados.', 'error')
            return render_template('admin/relatorios.html')
        
        cursor = conn.cursor(dictionary=True)
        
        # Relatório mensal
        cursor.execute("SELECT * FROM view_relatorios_mensais LIMIT 12")
        relatorios_mensais = cursor.fetchall()
        
        # Produtos mais vendidos
        cursor.execute("SELECT * FROM view_produtos_mais_vendidos LIMIT 10")
        produtos_mais_vendidos = cursor.fetchall()
        
        # Clientes mais ativos
        cursor.execute("SELECT * FROM view_clientes_ativos LIMIT 10")
        clientes_ativos = cursor.fetchall()
        
        # Estoque crítico
        cursor.execute("SELECT * FROM view_estoque_critico")
        estoque_critico = cursor.fetchall()
        
        return render_template('admin/relatorios.html',
                             relatorios_mensais=relatorios_mensais,
                             produtos_mais_vendidos=produtos_mais_vendidos,
                             clientes_ativos=clientes_ativos,
                             estoque_critico=estoque_critico)
    
    except mysql.connector.Error as err:
        flash(f'Erro ao carregar relatórios: {err}', 'error')
        return render_template('admin/relatorios.html')
    
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/admin/diagnosticos')
@admin_required
def admin_diagnosticos():
    """Gerenciamento de diagnósticos"""
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erro ao conectar ao banco de dados.', 'error')
            return render_template('admin/diagnosticos.html', diagnosticos=[])
        
        cursor = conn.cursor(dictionary=True)
        
        # Filtros
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
    """Detalhes e atualização de diagnóstico"""
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
                UPDATE diagnosticos 
                SET status = %s, relatorio_final = %s, pecas_defeito = %s, 
                    orcamento = %s, observacoes = %s, tecnico_responsavel = %s
                WHERE id_diagnostico = %s
            """, (status, relatorio_final, pecas_defeito, 
                  float(orcamento) if orcamento else 0, 
                  observacoes, session['admin_id'], id_diagnostico))
            
            # Se status for concluído, registrar data
            if status == 'concluido':
                cursor.execute("""
                    UPDATE diagnosticos 
                    SET data_conclusao = NOW() 
                    WHERE id_diagnostico = %s
                """, (id_diagnostico,))
            
            conn.commit()
            
            flash('✅ Diagnóstico atualizado com sucesso!', 'success')
            return redirect(url_for('admin_diagnosticos'))
        
        else:
            # Carregar dados do diagnóstico
            cursor.execute("""
                SELECT d.*, f.nome as tecnico_nome 
                FROM diagnosticos d 
                LEFT JOIN funcionarios f ON d.tecnico_responsavel = f.id_funcionario
                WHERE d.id_diagnostico = %s
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

# ============================================
# ROTAS PÚBLICAS PARA DIAGNÓSTICO
# ============================================

@app.route('/diagnostico', methods=['GET', 'POST'])
def diagnostico():
    """Página pública para solicitar diagnóstico"""
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
            
            # Verificar se é cliente
            id_cliente = None
            if session.get('usuario_id'):
                cursor.execute("SELECT id_cliente FROM clientes WHERE id_cliente = %s", (session['usuario_id'],))
                if cursor.fetchone():
                    id_cliente = session['usuario_id']
            
            cursor.execute("""
                INSERT INTO diagnosticos 
                (id_cliente, nome_cliente, email, telefone, tipo_equipamento, marca, modelo, problema, sintomas)
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
    """API para gerar relatório de diagnóstico em PDF/JSON"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Erro de conexão'}), 500
        
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT d.*, f.nome as tecnico_nome 
            FROM diagnosticos d 
            LEFT JOIN funcionarios f ON d.tecnico_responsavel = f.id_funcionario
            WHERE d.id_diagnostico = %s
        """, (id_diagnostico,))
        
        diagnostico = cursor.fetchone()
        
        if not diagnostico:
            return jsonify({'error': 'Diagnóstico não encontrado'}), 404
        
        # Formatar relatório
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

# ============================================
# ROTAS INSTITUCIONAIS E INFORMATIVAS
# ============================================

@app.route('/sobre')
def sobre():
    """Página Sobre a GHCP"""
    return render_template('sobre.html')

@app.route('/contato')
def contato():
    """Página de Contato"""
    return render_template('contato.html')

@app.route('/trabalhe-conosco')
def trabalhe_conosco():
    """Página Trabalhe Conosco"""
    return render_template('trabalhe_conosco.html')

@app.route('/faq')
def faq():
    """Página de Perguntas Frequentes"""
    return render_template('faq.html')

@app.route('/rastreio')
def rastreio():
    """Página de Rastreamento de Pedido"""
    return render_template('rastreio.html')

@app.route('/trocas')
def trocas():
    """Página de Trocas e Devoluções"""
    return render_template('trocas.html')

@app.route('/termos')
def termos():
    """Página de Termos de Uso"""
    return render_template('termos.html')

@app.route('/privacidade')
def privacidade():
    """Página de Política de Privacidade"""
    return render_template('privacidade.html')

@app.route('/cookies')
def cookies():
    """Página de Política de Cookies"""
    return render_template('cookies.html')

@app.route('/prazos')
def prazos():
    """Página de Prazos de Entrega"""
    return render_template('prazos.html')

@app.route('/formas-pagamento')
def formas_pagamento():
    """Página de Formas de Pagamento"""
    return render_template('formas_pagamento.html')

@app.route('/garantia')
def garantia():
    """Página de Garantia"""
    return render_template('garantia.html')

@app.route('/marcas')
def marcas():
    """Página de Marcas Parceiras"""
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erro ao conectar ao banco de dados.', 'error')
            return render_template('marcas.html', marcas=[])
        
        cursor = conn.cursor(dictionary=True)
        
        # Buscar todas as marcas distintas
        cursor.execute("""
            SELECT marca, COUNT(*) as total_produtos, 
                   MIN(preco) as preco_minimo, 
                   MAX(preco) as preco_maximo
            FROM produto 
            WHERE ativo = TRUE 
            GROUP BY marca 
            ORDER BY marca
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
    """Página de Categorias"""
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erro ao conectar ao banco de dados.', 'error')
            return render_template('categorias.html', categorias=[])
        
        cursor = conn.cursor(dictionary=True)
        
        # Buscar todas as categorias distintas
        cursor.execute("""
            SELECT categoria, COUNT(*) as total_produtos
            FROM produto 
            WHERE ativo = TRUE 
            GROUP BY categoria 
            ORDER BY categoria
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
    """Página de Ofertas Especiais"""
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erro ao conectar ao banco de dados.', 'error')
            return render_template('ofertas.html', produtos=[])
        
        cursor = conn.cursor(dictionary=True)
        
        # Buscar produtos em oferta (você pode adicionar um campo 'em_oferta' na tabela)
        cursor.execute("""
            SELECT * FROM produto 
            WHERE ativo = TRUE 
            ORDER BY preco ASC
            LIMIT 20
        """)
        
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
    """Página de Lançamentos"""
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erro ao conectar ao banco de dados.', 'error')
            return render_template('lancamentos.html', produtos=[])
        
        cursor = conn.cursor(dictionary=True)
        
        # Buscar produtos mais recentes
        cursor.execute("""
            SELECT * FROM produto 
            WHERE ativo = TRUE 
            ORDER BY data_cadastro DESC
            LIMIT 20
        """)
        
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
    """Página de Condições Comerciais"""
    return render_template('condicoes.html')

@app.route('/monte-seu-pc')
def monte_seu_pc():
    """Página Monte Seu PC"""
    return render_template('monte_seu_pc.html')

@app.route('/assistencia')
def assistencia():
    """Página de Assistência Técnica"""
    return render_template('assistencia.html')

@app.route('/blog')
def blog():
    """Página do Blog"""
    return render_template('blog.html')

@app.route('/newsletter')
def newsletter():
    """Página de Newsletter"""
    return render_template('newsletter.html')

# ============================================
# TRATAMENTO DE ERROS
# ============================================

@app.errorhandler(404)
def page_not_found(e):
    """Página não encontrada"""
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    """Erro interno do servidor"""
    return render_template('500.html'), 500

# ============================================
# EXECUTAR APLICAÇÃO
# ============================================

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 Loja GHCP - Sistema de E-commerce + Admin")
    print("=" * 60)
    print("✅ Servidor Flask iniciado com sucesso!")
    print(f"🌐 Site: http://localhost:5000")
    print(f"🔐 Login Cliente: http://localhost:5000/login")
    print(f"👑 Admin: http://localhost:5000/admin/login")
    print(f"👤 Minha Conta: http://localhost:5000/minha-conta")
    print(f"🛒 Carrinho: http://localhost:5000/carrinho")
    print(f"🔧 Diagnóstico: http://localhost:5000/diagnostico")
    print("=" * 60)
    print("👑 Credenciais Admin:")
    print("📧 Email: admin@ghcp.com")
    print("🔑 Senha: admin123")
    print("=" * 60)
    
    # Criar diretório de uploads se não existir
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    
    app.run(debug=True, host='0.0.0.0', port=5000)