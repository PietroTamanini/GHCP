-- ============================================
-- BANCO DE DADOS COMPLETO - LOJA GHCP
-- Sistema de E-commerce com Minha Conta
-- ============================================

-- Criar o banco de dados (se não existir)
CREATE DATABASE IF NOT EXISTS loja_informatica;
USE loja_informatica;

-- ============================================
-- TABELAS PRINCIPAIS
-- ============================================

-- Tabela de produtos
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
    INDEX idx_nome (nome),
    INDEX idx_marca (marca),
    INDEX idx_categoria (categoria),
    INDEX idx_ativo (ativo)
);

-- Tabela de clientes
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
    INDEX idx_cpf (cpf)
);

-- Tabela de endereços
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

-- Tabela de pedidos
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

-- Itens do pedido
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

-- Tabela de preferências
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

-- Avaliações
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

-- Histórico de senhas
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

-- Carrinho abandonado
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

-- Cupons
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

-- ============================================
-- DADOS DE EXEMPLO
-- ============================================

INSERT INTO produto (nome, marca, preco, descricao, estoque, categoria, ativo) VALUES
('Notebook Dell Inspiron 15', 'Dell', 3500.00, 'Notebook potente com Intel Core i7, 16GB RAM, SSD 512GB, ideal para trabalho e jogos', 10, 'Notebooks', TRUE),
('Mouse Logitech MX Master 3', 'Logitech', 450.00, 'Mouse ergonômico sem fio com sensor de alta precisão', 50, 'Periféricos', TRUE),
('Teclado Mecânico RGB Gamer', 'Corsair', 550.00, 'Teclado mecânico com switch Cherry MX e iluminação RGB customizável', 30, 'Periféricos', TRUE),
('Monitor 27" 4K Samsung', 'Samsung', 1800.00, 'Monitor 4K UHD com HDR, 60Hz, perfeito para design e edição', 15, 'Monitores', TRUE),
('SSD 1TB NVMe Kingston', 'Kingston', 500.00, 'Armazenamento ultra-rápido NVMe Gen 4, leitura 7000MB/s', 20, 'Armazenamento', TRUE),
('Placa de Vídeo RTX 3060', 'NVIDIA', 2500.00, 'Placa de vídeo GeForce RTX 3060 12GB para gaming em alta performance', 5, 'Hardware', TRUE),
('Headset Gamer HyperX Cloud', 'HyperX', 350.00, 'Headset com som surround 7.1, microfone removível', 25, 'Periféricos', TRUE),
('Webcam Full HD Logitech', 'Logitech', 280.00, 'Webcam 1080p com microfone embutido, ideal para videoconferências', 35, 'Periféricos', TRUE),
('Mousepad Gamer Extra Grande', 'Razer', 120.00, 'Mousepad 90x40cm com base antiderrapante', 100, 'Periféricos', TRUE),
('Cadeira Gamer DT3 Sports', 'DT3', 1200.00, 'Cadeira ergonômica reclinável até 180°, suporta até 120kg', 8, 'Móveis', TRUE);

-- Inserir alguns clientes de exemplo (senhas são hash de "123456")
INSERT INTO clientes (nome, email, senha, cpf, telefone, data_nascimento, genero, ativo) VALUES
('João Silva', 'joao.silva@email.com', '$2b$12$LQv3c1yqBzwZ0Jn6aUhW.uRgOEkZG/gC6Zgv.7pBw5O8nL2pYzJQa', '123.456.789-00', '(11) 99999-9999', '1990-05-15', 'M', TRUE),
('Maria Santos', 'maria.santos@email.com', '$2b$12$LQv3c1yqBzwZ0Jn6aUhW.uRgOEkZG/gC6Zgv.7pBw5O8nL2pYzJQa', '987.654.321-00', '(11) 88888-8888', '1985-08-20', 'F', TRUE);

-- Inserir endereços de exemplo
INSERT INTO enderecos (id_cliente, tipo, destinatario, cep, estado, cidade, bairro, rua, numero, complemento, principal) VALUES
(1, 'Casa', 'João Silva', '01234-567', 'SP', 'São Paulo', 'Centro', 'Rua das Flores', '123', 'Apto 45', TRUE),
(2, 'Trabalho', 'Maria Santos', '04567-890', 'SP', 'São Paulo', 'Jardins', 'Av. Paulista', '1000', 'Sala 501', TRUE);

-- Inserir preferências de exemplo
INSERT INTO preferencias (id_cliente, email_notificacoes, ofertas_personalizadas) VALUES
(1, TRUE, TRUE),
(2, TRUE, FALSE);

-- ============================================
-- TRIGGERS
-- ============================================

-- Trigger para registrar histórico de senhas
DELIMITER //
CREATE TRIGGER after_cliente_senha_update
AFTER UPDATE ON clientes
FOR EACH ROW
BEGIN
    IF OLD.senha != NEW.senha THEN
        INSERT INTO historico_senhas (id_cliente, senha_antiga, ip_alteracao)
        VALUES (NEW.id_cliente, OLD.senha, '127.0.0.1');
    END IF;
END//
DELIMITER ;

-- Trigger para atualizar estoque quando um pedido é feito
DELIMITER //
CREATE TRIGGER after_pedido_insert
AFTER INSERT ON itens_pedido
FOR EACH ROW
BEGIN
    UPDATE produto 
    SET estoque = estoque - NEW.quantidade 
    WHERE id_produto = NEW.id_produto;
END//
DELIMITER ;

-- Trigger para restaurar estoque quando um pedido é cancelado
DELIMITER //
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
DELIMITER ;

-- ============================================
-- VIEWS
-- ============================================

-- View para relatório de vendas
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

-- View para produtos mais vendidos
CREATE VIEW view_produtos_mais_vendidos AS
SELECT 
    p.id_produto,
    p.nome,
    p.marca,
    p.categoria,
    SUM(ip.quantidade) as total_vendido,
    SUM(ip.quantidade * ip.preco_unitario) as receita_total
FROM produto p
JOIN itens_pedido ip ON p.id_produto = ip.id_produto
JOIN pedidos ped ON ip.id_pedido = ped.id_pedido
WHERE ped.status != 'cancelado'
GROUP BY p.id_produto
ORDER BY total_vendido DESC;

-- View para clientes mais ativos
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

-- View para estoque baixo
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

-- ============================================
-- PROCEDURES
-- ============================================

-- Procedure para calcular estatísticas de vendas
DELIMITER //
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
DELIMITER ;

-- Procedure para atualizar preços por categoria
DELIMITER //
CREATE PROCEDURE sp_aumento_preco_categoria(IN categoria_nome VARCHAR(100), IN percentual DECIMAL(5,2))
BEGIN
    UPDATE produto 
    SET preco = preco * (1 + percentual/100)
    WHERE categoria = categoria_nome AND ativo = TRUE;
END//
DELIMITER ;

-- ============================================
-- FUNCTIONS
-- ============================================

-- Function para calcular idade do cliente
DELIMITER //
CREATE FUNCTION fn_calcular_idade(data_nascimento DATE)
RETURNS INT
READS SQL DATA
DETERMINISTIC
BEGIN
    RETURN TIMESTAMPDIFF(YEAR, data_nascimento, CURDATE());
END//
DELIMITER ;

-- Function para verificar estoque suficiente
DELIMITER //
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

-- ============================================
-- ÍNDICES ADICIONAIS
-- ============================================

-- Índices para melhor performance
CREATE INDEX idx_produto_preco ON produto(preco);
CREATE INDEX idx_produto_estoque ON produto(estoque);
CREATE INDEX idx_pedidos_data_status ON pedidos(data_pedido, status);
CREATE INDEX idx_clientes_data_cadastro ON clientes(data_cadastro);
CREATE INDEX idx_itens_pedido_preco ON itens_pedido(preco_unitario);

-- ============================================
-- MENSAGEM DE SUCESSO
-- ============================================

SELECT '✅ Banco de dados criado com sucesso!' as mensagem;
SELECT '📊 Tabelas criadas: produto, clientes, enderecos, pedidos, itens_pedido, preferencias, avaliacoes, historico_senhas, carrinho_abandonado, cupons' as tabelas;
SELECT '🔧 Recursos adicionados: Triggers, Views, Procedures, Functions e Índices' as recursos;
SELECT '📝 Dados de exemplo inseridos: 10 produtos, 2 clientes, 2 endereços' as dados_exemplo;

use loja_informatica;
ALTER TABLE clientes
ADD COLUMN data_nascimento DATE,
ADD COLUMN genero ENUM('M', 'F', 'O') DEFAULT NULL,
ADD COLUMN ultima_alteracao TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
ADD COLUMN ativo BOOLEAN DEFAULT TRUE
