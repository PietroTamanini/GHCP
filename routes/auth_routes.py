from flask import render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from models.database import get_db_connection
from models.validators import validar_email, validar_cpf, validar_cnpj, formatar_cpf, formatar_cnpj
from utils.decorators import login_required
import mysql.connector

def configure_auth_routes(app):
    
    @app.route('/escolher-tipo-cadastro')
    def escolher_tipo_cadastro():
        return render_template('escolher_tipo_cadastro.html')

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        tipo = request.args.get('tipo', 'cliente')
        
        if request.method == 'POST':
            email = request.form.get('email', '').strip().lower()
            senha = request.form.get('senha', '')
            tipo_login = request.form.get('tipo_login', 'cliente')
            
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
                
                if tipo_login == 'empresa':
                    cursor.execute("SELECT id_empresa, razao_social, nome_fantasia, email, senha, ativo, tipo_empresa FROM empresas WHERE email = %s", (email,))
                    usuario = cursor.fetchone()
                    
                    if usuario and check_password_hash(usuario['senha'], senha):
                        if not usuario['ativo']:
                            flash('⚠️ Sua empresa está desativada. Entre em contato com o suporte.', 'warning')
                            return render_template('login.html')
                        
                        session['empresa_id'] = usuario['id_empresa']
                        session['empresa_nome'] = usuario['nome_fantasia'] or usuario['razao_social']
                        session['empresa_email'] = usuario['email']
                        session['empresa_tipo'] = usuario['tipo_empresa']
                        
                        flash(f'🎉 Bem-vindo, {session["empresa_nome"]}!', 'success')
                        return redirect(url_for('painel_empresa'))
                    else:
                        flash('❌ E-mail ou senha incorretos.', 'error')
                else:
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

    @app.route('/login_empresa', methods=['GET', 'POST'])
    def login_empresa():
        if request.method == 'POST':
            email = request.form.get('email', '').strip().lower()
            senha = request.form.get('senha', '')
            
            if not email or not senha:
                flash('❌ Por favor, preencha todos os campos.', 'error')
                return render_template('login_empresa.html', form_type='login')
            
            if not validar_email(email):
                flash('❌ E-mail inválido.', 'error')
                return render_template('login_empresa.html', form_type='login')
            
            try:
                conn = get_db_connection()
                if not conn:
                    flash('Erro ao conectar ao banco de dados.', 'error')
                    return render_template('login_empresa.html', form_type='login')
                
                cursor = conn.cursor(dictionary=True)
                
                cursor.execute("SELECT id_empresa, razao_social, nome_fantasia, email, senha, ativo, tipo_empresa FROM empresas WHERE email = %s", (email,))
                usuario = cursor.fetchone()
                
                if usuario and check_password_hash(usuario['senha'], senha):
                    if not usuario['ativo']:
                        flash('⚠️ Sua empresa está desativada. Entre em contato com o suporte.', 'warning')
                        return render_template('login_empresa.html', form_type='login')
                    
                    session['empresa_id'] = usuario['id_empresa']
                    session['empresa_nome'] = usuario['nome_fantasia'] or usuario['razao_social']
                    session['empresa_email'] = usuario['email']
                    session['empresa_tipo'] = usuario['tipo_empresa']
                    
                    flash(f'🎉 Bem-vindo, {session["empresa_nome"]}!', 'success')
                    return redirect(url_for('painel_empresa'))
                else:
                    flash('❌ E-mail ou senha incorretos.', 'error')
            
            except mysql.connector.Error as err:
                flash(f'Erro ao fazer login: {err}', 'error')
            finally:
                if conn and conn.is_connected():
                    cursor.close()
                    conn.close()
        
        return render_template('login_empresa.html', form_type='login')

    @app.route('/cadastro_empresa', methods=['GET', 'POST'])
    def cadastro_empresa():
        if request.method == 'POST':
            razao_social = request.form.get('razao_social', '').strip()
            nome_fantasia = request.form.get('nome_fantasia', '').strip()
            cnpj = request.form.get('cnpj', '').strip()
            email = request.form.get('email', '').strip().lower()
            telefone = request.form.get('telefone', '').strip()
            tipo_empresa = request.form.get('tipo_empresa', 'comprador')
            endereco = request.form.get('endereco', '').strip()
            senha = request.form.get('senha', '')
            confirmar_senha = request.form.get('confirmar_senha', '')
            aceitar_termos = request.form.get('aceitar_termos')
            
            if not all([razao_social, cnpj, email, senha, confirmar_senha, tipo_empresa]):
                flash('❌ Por favor, preencha todos os campos obrigatórios.', 'error')
                return render_template('login_empresa.html', form_type='cadastro')
            
            if not aceitar_termos:
                flash('❌ Você precisa aceitar os Termos de Uso e Política de Privacidade.', 'error')
                return render_template('login_empresa.html', form_type='cadastro')
            
            if senha != confirmar_senha:
                flash('❌ As senhas não coincidem.', 'error')
                return render_template('login_empresa.html', form_type='cadastro')
            
            if len(senha) < 6:
                flash('❌ A senha deve ter no mínimo 6 caracteres.', 'error')
                return render_template('login_empresa.html', form_type='cadastro')
            
            if not validar_email(email):
                flash('❌ E-mail inválido.', 'error')
                return render_template('login_empresa.html', form_type='cadastro')
            
            if not validar_cnpj(cnpj):
                flash('❌ CNPJ inválido.', 'error')
                return render_template('login_empresa.html', form_type='cadastro')
            
            cnpj_formatado = formatar_cnpj(cnpj)
            
            try:
                conn = get_db_connection()
                if not conn:
                    flash('Erro ao conectar ao banco de dados.', 'error')
                    return render_template('login_empresa.html', form_type='cadastro')
                
                cursor = conn.cursor()
                
                cursor.execute("SELECT id_empresa FROM empresas WHERE email = %s", (email,))
                if cursor.fetchone():
                    flash('❌ Este e-mail já está cadastrado.', 'error')
                    return render_template('login_empresa.html', form_type='cadastro')
                
                cursor.execute("SELECT id_empresa FROM empresas WHERE cnpj = %s", (cnpj_formatado,))
                if cursor.fetchone():
                    flash('❌ Este CNPJ já está cadastrado.', 'error')
                    return render_template('login_empresa.html', form_type='cadastro')
                
                senha_hash = generate_password_hash(senha)
                
                cursor.execute("""
                    INSERT INTO empresas (razao_social, nome_fantasia, cnpj, email, senha, telefone, tipo_empresa, endereco)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (razao_social, nome_fantasia, cnpj_formatado, email, senha_hash, telefone, tipo_empresa, endereco))
                
                conn.commit()
                empresa_id = cursor.lastrowid
                
                session['empresa_id'] = empresa_id
                session['empresa_nome'] = nome_fantasia or razao_social
                session['empresa_email'] = email
                session['empresa_tipo'] = tipo_empresa
                
                flash(f'🎉 Cadastro realizado com sucesso! Bem-vindo, {session["empresa_nome"]}!', 'success')
                return redirect(url_for('painel_empresa'))
            
            except mysql.connector.Error as err:
                flash(f'Erro ao cadastrar empresa: {err}', 'error')
                return render_template('login_empresa.html', form_type='cadastro')
            finally:
                if conn and conn.is_connected():
                    cursor.close()
                    conn.close()
        
        return render_template('login_empresa.html', form_type='cadastro')

    @app.route('/logout')
    @login_required
    def logout():
        nome = session.get('usuario_nome') or session.get('empresa_nome', 'Usuário')
        session.clear()
        flash(f'👋 Até logo, {nome}! Volte sempre.', 'info')
        return redirect(url_for('inicio'))
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