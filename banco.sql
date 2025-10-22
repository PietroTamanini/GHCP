CREATE DATABASE IF NOT EXISTS loja_informatica;
USE loja_informatica;

DROP TABLE IF EXISTS produto;
CREATE TABLE produto (
    id_produto INT PRIMARY KEY AUTO_INCREMENT,
    nome VARCHAR(255) NOT NULL,
    marca VARCHAR(255) NOT NULL,
    preco DECIMAL(10, 2) NOT NULL,
    descricao TEXT,
    estoque INT DEFAULT 0,
    imagem VARCHAR(500),
    categoria VARCHAR(100),
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    imagens JSON,
    destaque BOOLEAN DEFAULT FALSE,
    peso DECIMAL(8,2) DEFAULT 0,
    dimensoes VARCHAR(50),
    INDEX idx_nome (nome),
    INDEX idx_marca (marca),
    INDEX idx_categoria (categoria),
    INDEX idx_ativo (ativo),
    INDEX idx_preco (preco),
    INDEX idx_estoque (estoque)
);

DROP TABLE IF EXISTS clientes;
CREATE TABLE clientes (
    id_cliente INT PRIMARY KEY AUTO_INCREMENT,
    nome VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    senha VARCHAR(255) NOT NULL,
    cpf VARCHAR(14) NOT NULL UNIQUE,
    telefone VARCHAR(20),
    endereco TEXT,
    data_nascimento DATE,
    genero ENUM('M', 'F', 'O') DEFAULT NULL,
    data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ultima_alteracao TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    ativo BOOLEAN DEFAULT TRUE,
    INDEX idx_nome (nome),
    INDEX idx_email (email),
    INDEX idx_cpf (cpf),
    INDEX idx_data_cadastro (data_cadastro)
);

DROP TABLE IF EXISTS enderecos;
CREATE TABLE enderecos (
    id_endereco INT PRIMARY KEY AUTO_INCREMENT,
    id_cliente INT NOT NULL,
    tipo VARCHAR(50) NOT NULL DEFAULT 'Casa',
    destinatario VARCHAR(255) NOT NULL,
    cep VARCHAR(10) NOT NULL,
    estado VARCHAR(2) NOT NULL,
    cidade VARCHAR(100) NOT NULL,
    bairro VARCHAR(100) NOT NULL,
    rua VARCHAR(255) NOT NULL,
    numero VARCHAR(20) NOT NULL,
    complemento VARCHAR(255),
    principal BOOLEAN DEFAULT FALSE,
    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_cliente) REFERENCES clientes(id_cliente) ON DELETE CASCADE,
    INDEX idx_cliente (id_cliente),
    INDEX idx_principal (id_cliente, principal)
);

DROP TABLE IF EXISTS pedidos;
CREATE TABLE pedidos (
    id_pedido INT PRIMARY KEY AUTO_INCREMENT,
    id_cliente INT NOT NULL,
    id_endereco INT,
    data_pedido TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total DECIMAL(10, 2) NOT NULL,
    status ENUM('pendente', 'aprovado', 'enviado', 'entregue', 'cancelado') DEFAULT 'pendente',
    forma_pagamento VARCHAR(50),
    codigo_rastreio VARCHAR(100),
    observacoes TEXT,
    FOREIGN KEY (id_cliente) REFERENCES clientes(id_cliente) ON DELETE CASCADE,
    FOREIGN KEY (id_endereco) REFERENCES enderecos(id_endereco) ON DELETE SET NULL,
    INDEX idx_cliente (id_cliente),
    INDEX idx_status (status),
    INDEX idx_data (data_pedido)
);

DROP TABLE IF EXISTS itens_pedido;
CREATE TABLE itens_pedido (
    id_item INT PRIMARY KEY AUTO_INCREMENT,
    id_pedido INT NOT NULL,
    id_produto INT NOT NULL,
    quantidade INT NOT NULL,
    preco_unitario DECIMAL(10, 2) NOT NULL,
    desconto DECIMAL(10, 2) DEFAULT 0,
    FOREIGN KEY (id_pedido) REFERENCES pedidos(id_pedido) ON DELETE CASCADE,
    FOREIGN KEY (id_produto) REFERENCES produto(id_produto) ON DELETE CASCADE,
    INDEX idx_pedido (id_pedido),
    INDEX idx_produto (id_produto)
);

DROP TABLE IF EXISTS preferencias;
CREATE TABLE preferencias (
    id_preferencia INT PRIMARY KEY AUTO_INCREMENT,
    id_cliente INT NOT NULL UNIQUE,
    email_notificacoes BOOLEAN DEFAULT TRUE,
    sms_notificacoes BOOLEAN DEFAULT FALSE,
    ofertas_personalizadas BOOLEAN DEFAULT TRUE,
    tema_escuro BOOLEAN DEFAULT FALSE,
    idioma VARCHAR(10) DEFAULT 'pt-BR',
    data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (id_cliente) REFERENCES clientes(id_cliente) ON DELETE CASCADE
);

DROP TABLE IF EXISTS avaliacoes;
CREATE TABLE avaliacoes (
    id_avaliacao INT PRIMARY KEY AUTO_INCREMENT,
    id_cliente INT NOT NULL,
    id_produto INT NOT NULL,
    nota INT CHECK (nota BETWEEN 1 AND 5),
    titulo VARCHAR(200),
    comentario TEXT,
    data_avaliacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    aprovado BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (id_cliente) REFERENCES clientes(id_cliente) ON DELETE CASCADE,
    FOREIGN KEY (id_produto) REFERENCES produto(id_produto) ON DELETE CASCADE,
    UNIQUE KEY unique_avaliacao (id_cliente, id_produto),
    INDEX idx_produto (id_produto),
    INDEX idx_nota (nota)
);

DROP TABLE IF EXISTS historico_senhas;
CREATE TABLE historico_senhas (
    id_historico INT PRIMARY KEY AUTO_INCREMENT,
    id_cliente INT NOT NULL,
    senha_antiga VARCHAR(255) NOT NULL,
    data_alteracao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_alteracao VARCHAR(45),
    FOREIGN KEY (id_cliente) REFERENCES clientes(id_cliente) ON DELETE CASCADE,
    INDEX idx_cliente (id_cliente)
);

DROP TABLE IF EXISTS carrinho_abandonado;
CREATE TABLE carrinho_abandonado (
    id_carrinho INT PRIMARY KEY AUTO_INCREMENT,
    id_cliente INT NOT NULL,
    id_produto INT NOT NULL,
    quantidade INT NOT NULL,
    data_adicao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_cliente) REFERENCES clientes(id_cliente) ON DELETE CASCADE,
    FOREIGN KEY (id_produto) REFERENCES produto(id_produto) ON DELETE CASCADE
);

DROP TABLE IF EXISTS cupons;
CREATE TABLE cupons (
    id_cupom INT PRIMARY KEY AUTO_INCREMENT,
    codigo VARCHAR(50) NOT NULL UNIQUE,
    desconto_percentual DECIMAL(5, 2),
    desconto_valor DECIMAL(10, 2),
    valor_minimo DECIMAL(10, 2) DEFAULT 0,
    data_inicio DATE,
    data_fim DATE,
    limite_uso INT DEFAULT NULL,
    vezes_usado INT DEFAULT 0,
    ativo BOOLEAN DEFAULT TRUE,
    INDEX idx_codigo (codigo)
);

DROP TABLE IF EXISTS funcionarios;
CREATE TABLE funcionarios (
    id_funcionario INT PRIMARY KEY AUTO_INCREMENT,
    nome VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    senha VARCHAR(255) NOT NULL,
    cargo ENUM('admin', 'gerente', 'vendedor', 'suporte') DEFAULT 'vendedor',
    ativo BOOLEAN DEFAULT TRUE,
    data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ultimo_login TIMESTAMP NULL,
    INDEX idx_email (email),
    INDEX idx_cargo (cargo)
);

DROP TABLE IF EXISTS diagnosticos;
CREATE TABLE diagnosticos (
    id_diagnostico INT PRIMARY KEY AUTO_INCREMENT,
    id_cliente INT,
    nome_cliente VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    telefone VARCHAR(20),
    tipo_equipamento VARCHAR(100) NOT NULL,
    marca VARCHAR(100),
    modelo VARCHAR(100),
    problema TEXT NOT NULL,
    sintomas TEXT,
    data_entrada TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status ENUM('recebido', 'em_analise', 'diagnosticado', 'orcamento', 'aprovado', 'reparacao', 'concluido', 'entregue') DEFAULT 'recebido',
    relatorio_final TEXT,
    pecas_defeito TEXT,
    orcamento DECIMAL(10, 2) DEFAULT 0,
    observacoes TEXT,
    tecnico_responsavel INT,
    data_conclusao TIMESTAMP NULL,
    FOREIGN KEY (tecnico_responsavel) REFERENCES funcionarios(id_funcionario) ON DELETE SET NULL,
    INDEX idx_status (status),
    INDEX idx_data (data_entrada)
);

DROP TABLE IF EXISTS logs_sistema;
CREATE TABLE logs_sistema (
    id_log INT PRIMARY KEY AUTO_INCREMENT,
    id_funcionario INT,
    acao VARCHAR(255) NOT NULL,
    modulo VARCHAR(100) NOT NULL,
    descricao TEXT,
    ip VARCHAR(45),
    data_log TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_funcionario) REFERENCES funcionarios(id_funcionario) ON DELETE SET NULL,
    INDEX idx_modulo (modulo),
    INDEX idx_data (data_log)
);

DROP VIEW IF EXISTS view_vendas;
CREATE VIEW view_vendas AS
SELECT 
    p.id_pedido,
    c.nome as cliente_nome,
    p.data_pedido,
    p.total,
    p.status,
    COUNT(ip.id_item) as total_itens
FROM pedidos p
JOIN clientes c ON p.id_cliente = c.id_cliente
JOIN itens_pedido ip ON p.id_pedido = ip.id_pedido
GROUP BY p.id_pedido;

DROP VIEW IF EXISTS view_produtos_mais_vendidos;
CREATE VIEW view_produtos_mais_vendidos AS
SELECT 
    p.id_produto,
    p.nome,
    p.marca,
    p.categoria,
    COALESCE(SUM(ip.quantidade), 0) as total_vendido,
    COALESCE(SUM(ip.quantidade * ip.preco_unitario), 0) as receita_total
FROM produto p
LEFT JOIN itens_pedido ip ON p.id_produto = ip.id_produto
LEFT JOIN pedidos ped ON ip.id_pedido = ped.id_pedido AND ped.status != 'cancelado'
GROUP BY p.id_produto
ORDER BY total_vendido DESC;

DROP VIEW IF EXISTS view_clientes_ativos;
CREATE VIEW view_clientes_ativos AS
SELECT 
    c.id_cliente,
    c.nome,
    c.email,
    COUNT(p.id_pedido) as total_pedidos,
    COALESCE(SUM(p.total), 0) as total_gasto,
    MAX(p.data_pedido) as ultima_compra
FROM clientes c
LEFT JOIN pedidos p ON c.id_cliente = p.id_cliente AND p.status != 'cancelado'
GROUP BY c.id_cliente
ORDER BY total_gasto DESC;

DROP VIEW IF EXISTS view_estoque_baixo;
CREATE VIEW view_estoque_baixo AS
SELECT 
    id_produto,
    nome,
    marca,
    estoque,
    categoria
FROM produto
WHERE estoque <= 5 AND ativo = TRUE
ORDER BY estoque ASC;

DROP VIEW IF EXISTS view_relatorios_mensais;
CREATE VIEW view_relatorios_mensais AS
SELECT 
    YEAR(data_pedido) as ano,
    MONTH(data_pedido) as mes,
    COUNT(*) as total_pedidos,
    COALESCE(SUM(total), 0) as receita_total,
    COALESCE(AVG(total), 0) as ticket_medio,
    COUNT(DISTINCT id_cliente) as clientes_unicos,
    SUM(CASE WHEN status = 'cancelado' THEN 1 ELSE 0 END) as pedidos_cancelados
FROM pedidos
WHERE data_pedido IS NOT NULL
GROUP BY YEAR(data_pedido), MONTH(data_pedido)
ORDER BY ano DESC, mes DESC;

DROP VIEW IF EXISTS view_estoque_critico;
CREATE VIEW view_estoque_critico AS
SELECT 
    p.id_produto,
    p.nome,
    p.marca,
    p.categoria,
    p.estoque,
    p.preco,
    COALESCE(SUM(ip.quantidade), 0) as vendas_mes
FROM produto p
LEFT JOIN itens_pedido ip ON p.id_produto = ip.id_produto
LEFT JOIN pedidos ped ON ip.id_pedido = ped.id_pedido 
    AND ped.data_pedido >= DATE_SUB(CURRENT_DATE, INTERVAL 30 DAY)
    AND ped.status != 'cancelado'
WHERE p.estoque <= 10 AND p.ativo = TRUE
GROUP BY p.id_produto
ORDER BY p.estoque ASC;

DELIMITER //

DROP TRIGGER IF EXISTS after_cliente_senha_update;
CREATE TRIGGER after_cliente_senha_update
AFTER UPDATE ON clientes
FOR EACH ROW
BEGIN
    IF OLD.senha != NEW.senha THEN
        INSERT INTO historico_senhas (id_cliente, senha_antiga, ip_alteracao)
        VALUES (NEW.id_cliente, OLD.senha, '127.0.0.1');
    END IF;
END//

DROP TRIGGER IF EXISTS after_pedido_insert;
CREATE TRIGGER after_pedido_insert
AFTER INSERT ON itens_pedido
FOR EACH ROW
BEGIN
    UPDATE produto 
    SET estoque = estoque - NEW.quantidade 
    WHERE id_produto = NEW.id_produto;
END//

DROP TRIGGER IF EXISTS after_pedido_cancel;
CREATE TRIGGER after_pedido_cancel
AFTER UPDATE ON pedidos
FOR EACH ROW
BEGIN
    IF NEW.status = 'cancelado' AND OLD.status != 'cancelado' THEN
        UPDATE produto p
        JOIN itens_pedido ip ON p.id_produto = ip.id_produto
        SET p.estoque = p.estoque + ip.quantidade
        WHERE ip.id_pedido = NEW.id_pedido;
    END IF;
END//

DROP TRIGGER IF EXISTS after_funcionario_login;
CREATE TRIGGER after_funcionario_login
AFTER UPDATE ON funcionarios
FOR EACH ROW
BEGIN
    IF NEW.ultimo_login IS NOT NULL AND (OLD.ultimo_login IS NULL OR NEW.ultimo_login != OLD.ultimo_login) THEN
        INSERT INTO logs_sistema (id_funcionario, acao, modulo, descricao)
        VALUES (NEW.id_funcionario, 'LOGIN', 'AUTENTICACAO', CONCAT('Login realizado por ', NEW.nome));
    END IF;
END//

DELIMITER ;

DELIMITER //

DROP PROCEDURE IF EXISTS sp_estatisticas_vendas;
CREATE PROCEDURE sp_estatisticas_vendas(IN data_inicio DATE, IN data_fim DATE)
BEGIN
    SELECT 
        COUNT(*) as total_pedidos,
        SUM(total) as receita_total,
        AVG(total) as ticket_medio,
        COUNT(DISTINCT id_cliente) as clientes_unicos
    FROM pedidos
    WHERE DATE(data_pedido) BETWEEN data_inicio AND data_fim
    AND status != 'cancelado';
END//

DROP PROCEDURE IF EXISTS sp_aumento_preco_categoria;
CREATE PROCEDURE sp_aumento_preco_categoria(IN categoria_nome VARCHAR(100), IN percentual DECIMAL(5,2))
BEGIN
    UPDATE produto 
    SET preco = preco * (1 + percentual/100)
    WHERE categoria = categoria_nome AND ativo = TRUE;
END//

DELIMITER ;

DELIMITER //

DROP FUNCTION IF EXISTS fn_calcular_idade;
CREATE FUNCTION fn_calcular_idade(data_nascimento DATE)
RETURNS INT
READS SQL DATA
DETERMINISTIC
BEGIN
    RETURN TIMESTAMPDIFF(YEAR, data_nascimento, CURDATE());
END//

DROP FUNCTION IF EXISTS fn_verificar_estoque;
CREATE FUNCTION fn_verificar_estoque(id_prod INT, qtd INT)
RETURNS BOOLEAN
READS SQL DATA
DETERMINISTIC
BEGIN
    DECLARE estoque_atual INT;
    SELECT estoque INTO estoque_atual FROM produto WHERE id_produto = id_prod;
    RETURN estoque_atual >= qtd;
END//

DELIMITER ;

CREATE INDEX IF NOT EXISTS idx_produto_preco ON produto(preco);
CREATE INDEX IF NOT EXISTS idx_produto_estoque ON produto(estoque);
CREATE INDEX IF NOT EXISTS idx_pedidos_data_status ON pedidos(data_pedido, status);
CREATE INDEX IF NOT EXISTS idx_clientes_data_cadastro ON clientes(data_cadastro);
CREATE INDEX IF NOT EXISTS idx_itens_pedido_preco ON itens_pedido(preco_unitario)

DROP TABLE IF EXISTS suporte;
CREATE TABLE suporte (
    id_suporte INT PRIMARY KEY AUTO_INCREMENT,
    nome VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    mensagem TEXT NOT NULL,
    data_envio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status ENUM('pendente', 'respondido', 'fechado') DEFAULT 'pendente',
    INDEX idx_email (email),
    INDEX idx_status (status)
);