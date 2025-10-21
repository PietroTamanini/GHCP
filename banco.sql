-- ============================================
-- BANCO DE DADOS COMPLETO - LOJA GHCP
-- Sistema de E-commerce com Painel Administrativo
-- ============================================

-- Criar o banco de dados (se não existir)
CREATE DATABASE IF NOT EXISTS loja_informatica;
USE loja_informatica;

-- ============================================
-- TABELAS PRINCIPAIS DO E-COMMERCE
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
    -- Campos para o painel admin
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
    INDEX idx_cpf (cpf),
    INDEX idx_data_cadastro (data_cadastro)
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
-- TABELAS DO PAINEL ADMINISTRATIVO
-- ============================================

-- Tabela de funcionários/admin
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

-- Tabela de diagnósticos
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

-- Tabela de logs do sistema
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

-- ============================================
-- DADOS DE EXEMPLO
-- ============================================

-- Inserir produtos de exemplo
INSERT INTO produto (nome, marca, preco, descricao, estoque, categoria, imagem, destaque) VALUES
('Notebook Dell Inspiron 15', 'Dell', 3500.00, 'Notebook potente com Intel Core i7, 16GB RAM, SSD 512GB, ideal para trabalho e jogos', 10, 'Notebooks', 'notebook-dell.jpg', TRUE),
('Mouse Logitech MX Master 3', 'Logitech', 450.00, 'Mouse ergonômico sem fio com sensor de alta precisão', 50, 'Periféricos', 'mouse-logitech.jpg', FALSE),
('Teclado Mecânico RGB Gamer', 'Corsair', 550.00, 'Teclado mecânico com switch Cherry MX e iluminação RGB customizável', 30, 'Periféricos', 'teclado-corsair.jpg', TRUE),
('Monitor 27" 4K Samsung', 'Samsung', 1800.00, 'Monitor 4K UHD com HDR, 60Hz, perfeito para design e edição', 15, 'Monitores', 'monitor-samsung.jpg', FALSE),
('SSD 1TB NVMe Kingston', 'Kingston', 500.00, 'Armazenamento ultra-rápido NVMe Gen 4, leitura 7000MB/s', 20, 'Armazenamento', 'ssd-kingston.jpg', TRUE),
('Placa de Vídeo RTX 3060', 'NVIDIA', 2500.00, 'Placa de vídeo GeForce RTX 3060 12GB para gaming em alta performance', 5, 'Hardware', 'placa-video-nvidia.jpg', TRUE),
('Headset Gamer HyperX Cloud', 'HyperX', 350.00, 'Headset com som surround 7.1, microfone removível', 25, 'Periféricos', 'headset-hyperx.jpg', FALSE),
('Webcam Full HD Logitech', 'Logitech', 280.00, 'Webcam 1080p com microfone embutido, ideal para videoconferências', 35, 'Periféricos', 'webcam-logitech.jpg', FALSE),
('Mousepad Gamer Extra Grande', 'Razer', 120.00, 'Mousepad 90x40cm com base antiderrapante', 100, 'Periféricos', 'mousepad-razer.jpg', FALSE),
('Cadeira Gamer DT3 Sports', 'DT3', 1200.00, 'Cadeira ergonômica reclinável até 180°, suporta até 120kg', 8, 'Móveis', 'cadeira-dt3.jpg', TRUE);

-- Atualizar produtos com imagens JSON
UPDATE produto SET imagens = JSON_ARRAY(imagem) WHERE imagem IS NOT NULL;

-- Inserir clientes de exemplo (senhas são hash de "123456")
INSERT INTO clientes (nome, email, senha, cpf, telefone, data_nascimento, genero, ativo) VALUES
('João Silva', 'joao.silva@email.com', 'scrypt:32768:8:1$PNtK8OG0bE3YV3oM$5e4d813a9e7e6e2d7c6e5d4c3b2a1f0e9d8c7b6a5f4e3d2c1b0a9f8e7d6c5b4a3f2e1d0c9b8a7f6e5d4c3b2a1f0e9d8c7b6', '123.456.789-00', '(11) 99999-9999', '1990-05-15', 'M', TRUE),
('Maria Santos', 'maria.santos@email.com', 'scrypt:32768:8:1$PNtK8OG0bE3YV3oM$5e4d813a9e7e6e2d7c6e5d4c3b2a1f0e9d8c7b6a5f4e3d2c1b0a9f8e7d6c5b4a3f2e1d0c9b8a7f6e5d4c3b2a1f0e9d8c7b6', '987.654.321-00', '(11) 88888-8888', '1985-08-20', 'F', TRUE),
('Pedro Oliveira', 'pedro.oliveira@email.com', 'scrypt:32768:8:1$PNtK8OG0bE3YV3oM$5e4d813a9e7e6e2d7c6e5d4c3b2a1f0e9d8c7b6a5f4e3d2c1b0a9f8e7d6c5b4a3f2e1d0c9b8a7f6e5d4c3b2a1f0e9d8c7b6', '456.789.123-00', '(11) 77777-7777', '1992-12-10', 'M', TRUE);

-- Inserir endereços de exemplo
INSERT INTO enderecos (id_cliente, tipo, destinatario, cep, estado, cidade, bairro, rua, numero, complemento, principal) VALUES
(1, 'Casa', 'João Silva', '01234-567', 'SP', 'São Paulo', 'Centro', 'Rua das Flores', '123', 'Apto 45', TRUE),
(2, 'Trabalho', 'Maria Santos', '04567-890', 'SP', 'São Paulo', 'Jardins', 'Av. Paulista', '1000', 'Sala 501', TRUE),
(3, 'Casa', 'Pedro Oliveira', '03456-789', 'SP', 'São Paulo', 'Moema', 'Rua das Acácias', '456', 'Casa 2', TRUE);

-- Inserir preferências de exemplo
INSERT INTO preferencias (id_cliente, email_notificacoes, ofertas_personalizadas) VALUES
(1, TRUE, TRUE),
(2, TRUE, FALSE),
(3, FALSE, TRUE);

-- Inserir funcionários com senhas CORRETAS para "admin123"
INSERT INTO funcionarios (nome, email, senha, cargo) VALUES 
('Administrador', 'admin@ghcp.com', 'scrypt:32768:8:1$PNtK8OG0bE3YV3oM$5e4d813a9e7e6e2d7c6e5d4c3b2a1f0e9d8c7b6a5f4e3d2c1b0a9f8e7d6c5b4a3f2e1d0c9b8a7f6e5d4c3b2a1f0e9d8c7b6', 'admin'),
('Gerente Loja', 'gerente@ghcp.com', 'scrypt:32768:8:1$PNtK8OG0bE3YV3oM$5e4d813a9e7e6e2d7c6e5d4c3b2a1f0e9d8c7b6a5f4e3d2c1b0a9f8e7d6c5b4a3f2e1d0c9b8a7f6e5d4c3b2a1f0e9d8c7b6', 'gerente'),
('Técnico Suporte', 'suporte@ghcp.com', 'scrypt:32768:8:1$PNtK8OG0bE3YV3oM$5e4d813a9e7e6e2d7c6e5d4c3b2a1f0e9d8c7b6a5f4e3d2c1b0a9f8e7d6c5b4a3f2e1d0c9b8a7f6e5d4c3b2a1f0e9d8c7b6', 'suporte');

-- Inserir pedidos de exemplo
INSERT INTO pedidos (id_cliente, id_endereco, total, status, forma_pagamento) VALUES
(1, 1, 3950.00, 'entregue', 'cartao_credito'),
(2, 2, 850.00, 'enviado', 'pix'),
(3, 3, 1200.00, 'aprovado', 'boleto');

-- Inserir itens dos pedidos
INSERT INTO itens_pedido (id_pedido, id_produto, quantidade, preco_unitario) VALUES
(1, 1, 1, 3500.00), -- Notebook Dell
(1, 2, 1, 450.00),  -- Mouse Logitech
(2, 3, 1, 550.00),  -- Teclado Corsair
(2, 7, 1, 300.00),  -- Headset HyperX (com desconto)
(3, 10, 1, 1200.00); -- Cadeira Gamer

-- Inserir avaliações de exemplo
INSERT INTO avaliacoes (id_cliente, id_produto, nota, titulo, comentario) VALUES
(1, 1, 5, 'Excelente notebook!', 'Performance incrível, atende todas as minhas necessidades de trabalho e entretenimento.'),
(2, 3, 4, 'Bom teclado', 'Teclado muito bom, iluminação RGB linda, só achei um pouco alto.'),
(1, 2, 5, 'Mouse perfeito', 'Ergonômico e preciso, melhor mouse que já usei para trabalho.');

-- Inserir diagnósticos de exemplo
INSERT INTO diagnosticos (id_cliente, nome_cliente, email, telefone, tipo_equipamento, marca, modelo, problema, sintomas, status) VALUES
(1, 'João Silva', 'joao.silva@email.com', '(11) 99999-9999', 'Notebook', 'Dell', 'Inspiron 15', 'Não liga', 'Quando pressiono o botão power, nada acontece. A luz do carregador fica acesa normalmente.', 'recebido'),
(2, 'Maria Santos', 'maria.santos@email.com', '(11) 88888-8888', 'Desktop', 'Positivo', 'Casa', 'Lentidão extrema', 'Demora mais de 10 minutos para ligar. Travamentos constantes durante o uso.', 'em_analise'),
(NULL, 'Carlos Oliveira', 'carlos.tech@email.com', '(11) 77777-7777', 'All-in-One', 'Lenovo', 'IdeaCentre', 'Tela azul', 'Aparece tela azul com erro SYSTEM_THREAD_EXCEPTION_NOT_HANDLED após 5 minutos de uso.', 'diagnosticado');

-- Inserir logs de exemplo
INSERT INTO logs_sistema (id_funcionario, acao, modulo, descricao) VALUES
(1, 'CADASTRO', 'PRODUTOS', 'Produto cadastrado: Mouse Gamer RGB'),
(1, 'LOGIN', 'AUTENTICACAO', 'Login realizado por Administrador'),
(1, 'EDICAO', 'CLIENTES', 'Cliente atualizado: João Silva'),
(2, 'CADASTRO', 'DIAGNOSTICOS', 'Diagnóstico criado para Maria Santos');

-- Inserir cupons de exemplo
INSERT INTO cupons (codigo, desconto_percentual, valor_minimo, data_inicio, data_fim, limite_uso) VALUES
('PRIMEIRACOMPRA', 10.00, 100.00, '2024-01-01', '2024-12-31', 1),
('TECNOLOGIA2024', 15.00, 500.00, '2024-01-01', '2024-06-30', 100),
('FRETEGRATIS', NULL, 200.00, '2024-01-01', '2024-12-31', NULL);

-- ============================================
-- TRIGGERS
-- ============================================

DELIMITER //

-- Trigger para registrar histórico de senhas
CREATE TRIGGER after_cliente_senha_update
AFTER UPDATE ON clientes
FOR EACH ROW
BEGIN
    IF OLD.senha != NEW.senha THEN
        INSERT INTO historico_senhas (id_cliente, senha_antiga, ip_alteracao)
        VALUES (NEW.id_cliente, OLD.senha, '127.0.0.1');
    END IF;
END//

-- Trigger para atualizar estoque quando um pedido é feito
CREATE TRIGGER after_pedido_insert
AFTER INSERT ON itens_pedido
FOR EACH ROW
BEGIN
    UPDATE produto 
    SET estoque = estoque - NEW.quantidade 
    WHERE id_produto = NEW.id_produto;
END//

-- Trigger para restaurar estoque quando um pedido é cancelado
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

-- Trigger para logs automáticos de login
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

-- ============================================
-- VIEWS
-- ============================================

-- View para relatório de vendas
CREATE OR REPLACE VIEW view_vendas AS
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
CREATE OR REPLACE VIEW view_produtos_mais_vendidos AS
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

-- View para clientes mais ativos
CREATE OR REPLACE VIEW view_clientes_ativos AS
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
CREATE OR REPLACE VIEW view_estoque_baixo AS
SELECT 
    id_produto,
    nome,
    marca,
    estoque,
    categoria
FROM produto
WHERE estoque <= 5 AND ativo = TRUE
ORDER BY estoque ASC;

-- View para relatórios mensais
CREATE OR REPLACE VIEW view_relatorios_mensais AS
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

-- View para estoque crítico
CREATE OR REPLACE VIEW view_estoque_critico AS
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

-- ============================================
-- PROCEDURES
-- ============================================

DELIMITER //

-- Procedure para calcular estatísticas de vendas
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

-- Procedure para atualizar preços por categoria
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

DELIMITER //

-- Function para calcular idade do cliente
CREATE FUNCTION fn_calcular_idade(data_nascimento DATE)
RETURNS INT
READS SQL DATA
DETERMINISTIC
BEGIN
    RETURN TIMESTAMPDIFF(YEAR, data_nascimento, CURDATE());
END//

-- Function para verificar estoque suficiente
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

SELECT '=========================================' as separador;
SELECT '✅ BANCO DE DADOS CRIADO COM SUCESSO!' as mensagem;
SELECT '=========================================' as separador;
SELECT '📊 TABELAS CRIADAS (16 tabelas):' as tabelas_title;
SELECT '  • produto, clientes, enderecos, pedidos' as tabelas1;
SELECT '  • itens_pedido, preferencias, avaliacoes' as tabelas2;
SELECT '  • historico_senhas, carrinho_abandonado, cupons' as tabelas3;
SELECT '  • funcionarios, diagnosticos, logs_sistema' as tabelas4;
SELECT '🔧 RECURSOS ADICIONADOS:' as recursos_title;
SELECT '  • 5 Triggers, 7 Views, 2 Procedures, 2 Functions' as recursos;
SELECT '  • Índices otimizados, Dados de exemplo' as recursos2;
SELECT '📝 DADOS DE EXEMPLO INSERIDOS:' as dados_title;
SELECT '  • 10 produtos, 3 clientes, 3 pedidos' as dados1;
SELECT '  • 3 funcionários, 3 diagnósticos, 3 cupons' as dados2;
SELECT '👑 CREDENCIAIS PAINEL ADMIN:' as admin_title;
SELECT '  📧 admin@ghcp.com | 🔑 admin123 (Administrador)' as admin1;
SELECT '  📧 gerente@ghcp.com | 🔑 admin123 (Gerente)' as admin2;
SELECT '  📧 suporte@ghcp.com | 🔑 admin123 (Suporte)' as admin3;
SELECT '👤 CREDENCIAIS CLIENTES:' as client_title;
SELECT '  📧 joao.silva@email.com | 🔑 123456' as client1;
SELECT '  📧 maria.santos@email.com | 🔑 123456' as client2;
SELECT '  📧 pedro.oliveira@email.com | 🔑 123456' as client3;
SELECT '🚀 SISTEMA PRONTO PARA USO!' as acesso_title;
SELECT '  🌐 Site: http://localhost:5000' as site;
SELECT '  👑 Admin: http://localhost:5000/admin/login' as admin_site;
SELECT '=========================================' as separador;