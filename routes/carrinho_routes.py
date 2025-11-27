from flask import render_template, request, flash, redirect, url_for, session
from models.database import get_db_connection
from utils.decorators import login_required
from utils.qrcode_generator import gerar_qrcode_pix
import mysql.connector
import json

def configure_carrinho_routes(app):
    
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
            
            # 🔥 CORREÇÃO: Processar imagens corretamente
            imagens_produto = []
            if produto.get('imagens'):
                try:
                    imagens_produto = json.loads(produto['imagens'])
                except:
                    # Se não for JSON, usa como array vazio
                    imagens_produto = []
            # Se não tiver imagens mas tiver imagem singular, usa ela
            elif produto.get('imagem'):
                imagens_produto = [produto['imagem']]
            
            if produto_no_carrinho:
                produto_no_carrinho['quantidade'] += quantidade
            else:
                carrinho.append({
                    'id_produto': produto['id_produto'],
                    'nome': produto['nome'],
                    'preco': float(produto['preco']),
                    'quantidade': quantidade,
                    'imagens': imagens_produto,  # ← MUDOU para 'imagens' (plural)
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

    @app.route('/gerar-pix/<float:valor>')
    def gerar_pix(valor):
        qr_base64, copia_cola = gerar_qrcode_pix(valor)
        return render_template('gerar_pix.html', valor=valor, qr_base64=qr_base64, copia_cola=copia_cola)

    @app.route('/finalizar-carrinho', methods=['GET', 'POST'])
    def finalizar_carrinho():
        if 'usuario_id' not in session:
            flash('⚠️ Faça login para finalizar sua compra.', 'warning')
            return redirect(url_for('login', next=url_for('finalizar_carrinho')))

        produtos_carrinho = session.get('carrinho', [])
        
        # 🔥 CORREÇÃO: Garantir que todos os produtos tenham 'imagens' como array
        for produto in produtos_carrinho:
            # Se o produto tiver 'imagem' mas não 'imagens', migrar
            if 'imagem' in produto and ('imagens' not in produto or not produto['imagens']):
                produto['imagens'] = [produto['imagem']]
            # Garantir que 'imagens' sempre seja um array
            if 'imagens' not in produto:
                produto['imagens'] = []
        
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
                cursor = conn.cursor(dictionary=True)

                # Verificar estoque
                for item in produtos_carrinho:
                    cursor.execute("SELECT nome, estoque FROM produto WHERE id_produto = %s", (item['id_produto'],))
                    produto_db = cursor.fetchone()
                    if not produto_db:
                        flash(f"❌ Produto '{item['nome']}' não encontrado.", 'error')
                        return redirect(url_for('carrinho'))
                    if produto_db['estoque'] < item['quantidade']:
                        flash(f"⚠️ Estoque insuficiente de '{produto_db['nome']}'.", 'warning')
                        return redirect(url_for('carrinho'))

                # Criar pedido
                cursor.execute("""
                    INSERT INTO pedidos (id_cliente, total, forma_pagamento, status, data_pedido)
                    VALUES (%s, %s, %s, %s, NOW())
                """, (session['usuario_id'], total_geral, pagamento, 'pendente'))
                pedido_id = cursor.lastrowid

                # Adicionar itens e atualizar estoque
                for item in produtos_carrinho:
                    cursor.execute("""
                        INSERT INTO itens_pedido (id_pedido, id_produto, quantidade, preco_unitario)
                        VALUES (%s, %s, %s, %s)
                    """, (pedido_id, item['id_produto'], item['quantidade'], item['preco']))
                    cursor.execute("""
                        UPDATE produto SET estoque = estoque - %s WHERE id_produto = %s
                    """, (item['quantidade'], item['id_produto']))

                # Registrar pagamento
                cursor.execute("""
                    INSERT INTO pagamentos (nome, email, endereco, metodo, valor)
                    VALUES (%s, %s, %s, %s, %s)
                """, (nome, email, endereco, pagamento, total_geral))

                conn.commit()

                # Gera PIX se for o método escolhido
                if pagamento == 'pix':
                    qr_base64, copia_cola = gerar_qrcode_pix(total_geral)
                    session.pop('carrinho', None)
                    flash('🎉 Compra finalizada com sucesso! Escaneie o QR Code para pagar via PIX.', 'success')
                    return render_template(
                        'compra-sucedida.html',
                        valor=total_geral,
                        qr_base64=qr_base64,
                        copia_cola=copia_cola,
                        pedido_id=pedido_id
                    )
                else:
                    flash('💳 Pagamento por cartão/boleto ainda não implementado.', 'info')
                    return redirect(url_for('main.inicio'))

            except mysql.connector.Error as err:
                conn.rollback()
                flash(f'❌ Erro ao finalizar compra: {err}', 'error')
                return redirect(url_for('carrinho'))
            finally:
                if conn and conn.is_connected():
                    cursor.close()
                    conn.close()

        return render_template('finalizar-carrinho.html',
                            produtos_carrinho=produtos_carrinho,
                            total_geral=total_geral)

    @app.route('/compra-sucedida')
    def compra_sucedida():
        return render_template('compra-sucedida.html')