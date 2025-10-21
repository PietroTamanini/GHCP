from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import os
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
import json

# Configurações de upload
UPLOAD_FOLDER = 'static/uploads/produtos'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Decorator para verificar se é admin
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            flash('⚠️ Acesso restrito para administradores.', 'warning')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# Rotas do Admin
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