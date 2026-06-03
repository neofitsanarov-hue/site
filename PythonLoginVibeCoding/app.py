from flask import Flask, render_template, request, redirect, session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "CHAVE_SUPER_FORTE"


# ==========================
# CONEXÃO BANCO
# ==========================

def conectar():
    return sqlite3.connect("sistema.db")


# ==========================
# CRIAR BANCO
# ==========================

def criar_banco():

    conn = conectar()
    cursor = conn.cursor()

    # USUÁRIOS
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            email TEXT UNIQUE,
            senha TEXT
        )
    """)

    # PRODUTOS
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            codigo TEXT UNIQUE,
            categoria TEXT,
            fornecedor TEXT,
            preco_compra REAL,
            preco_venda REAL,
            quantidade INTEGER,
            estoque_minimo INTEGER,
            data TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # FORNECEDORES
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fornecedores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            cnpj TEXT UNIQUE,
            telefone TEXT,
            email TEXT,
            endereco TEXT,
            cidade TEXT,
            estado TEXT
        )
    """)

    # ESTOQUE
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS movimentacoes_estoque (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            produto_id INTEGER,
            tipo TEXT,
            quantidade INTEGER,
            data TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


# ==========================
# CADASTRO
# ==========================

@app.route("/")
def cadastro():
    return render_template("cadastro.html")


@app.route("/cadastrar", methods=["POST"])
def cadastrar():

    nome = request.form["nome"]
    email = request.form["email"]
    senha = generate_password_hash(request.form["senha"])

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO usuarios (nome,email,senha)
        VALUES (?,?,?)
    """, (nome, email, senha))

    conn.commit()
    conn.close()

    return redirect("/login")


# ==========================
# LOGIN
# ==========================

@app.route("/login")
def login():
    return render_template("login.html")


@app.route("/entrar", methods=["POST"])
def entrar():

    email = request.form["email"]
    senha = request.form["senha"]

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM usuarios WHERE email=?", (email,))
    user = cursor.fetchone()

    conn.close()

    if user and check_password_hash(user[3], senha):

        session["user_id"] = user[0]
        session["user_nome"] = user[1]

        return redirect("/painel")

    return "Login inválido"


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/painel")
def painel():

    if "user_id" not in session:
        return redirect("/login")

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM produtos")
    total_produtos = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(preco_compra * quantidade) FROM produtos")
    valor_estoque = cursor.fetchone()[0] or 0

    cursor.execute("SELECT COUNT(*) FROM produtos WHERE quantidade <= estoque_minimo")
    estoque_baixo = cursor.fetchone()[0]

    cursor.execute("SELECT nome FROM produtos ORDER BY id DESC LIMIT 1")
    ultimo = cursor.fetchone()
    ultimo_produto = ultimo[0] if ultimo else "Nenhum"

    conn.close()

    return render_template(
        "painel.html",
        nome=session["user_nome"],
        total_produtos=total_produtos,
        valor_estoque=valor_estoque,
        estoque_baixo=estoque_baixo,
        ultimo_produto=ultimo_produto
    )


# ==========================
# PRODUTOS
# ==========================

@app.route("/produtos")
def produtos():

    if "user_id" not in session:
        return redirect("/login")

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM produtos ORDER BY id DESC")
    data = cursor.fetchall()

    conn.close()

    return render_template("produtos.html", produtos=data)


@app.route("/cadastrar_produto", methods=["POST"])
def cadastrar_produto():

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO produtos (
            nome,codigo,categoria,fornecedor,
            preco_compra,preco_venda,
            quantidade,estoque_minimo
        )
        VALUES (?,?,?,?,?,?,?,?)
    """, (
        request.form["nome"],
        request.form["codigo"],
        request.form["categoria"],
        request.form["fornecedor"],
        request.form["preco_compra"],
        request.form["preco_venda"],
        request.form["quantidade"],
        request.form["estoque_minimo"]
    ))

    conn.commit()
    conn.close()

    return redirect("/produtos")


@app.route("/fornecedores")
def fornecedores():

    if "user_id" not in session:
        return redirect("/login")

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM fornecedores ORDER BY id DESC")
    data = cursor.fetchall()

    conn.close()

    return render_template("fornecedores.html", fornecedores=data)

@app.route("/estoque")
def estoque():

    if "user_id" not in session:
        return redirect("/login")

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT m.id, p.nome, m.tipo, m.quantidade, m.data
        FROM movimentacoes_estoque m
        JOIN produtos p ON p.id = m.produto_id
        ORDER BY m.id DESC
    """)

    movimentacoes = cursor.fetchall()

    cursor.execute("SELECT id,nome FROM produtos")
    produtos = cursor.fetchall()

    conn.close()

    return render_template(
        "estoque.html",
        movimentacoes=movimentacoes,
        produtos=produtos
    )


@app.route("/entrada_estoque", methods=["POST"])
def entrada_estoque():

    conn = conectar()
    cursor = conn.cursor()

    produto_id = request.form["produto_id"]
    qtd = int(request.form["quantidade"])

    cursor.execute("""
        INSERT INTO movimentacoes_estoque (produto_id,tipo,quantidade)
        VALUES (?, 'ENTRADA', ?)
    """, (produto_id, qtd))

    cursor.execute("""
        UPDATE produtos SET quantidade = quantidade + ?
        WHERE id = ?
    """, (qtd, produto_id))

    conn.commit()
    conn.close()

    return redirect("/estoque")


@app.route("/saida_estoque", methods=["POST"])
def saida_estoque():

    conn = conectar()
    cursor = conn.cursor()

    produto_id = request.form["produto_id"]
    qtd = int(request.form["quantidade"])

    cursor.execute("""
        INSERT INTO movimentacoes_estoque (produto_id,tipo,quantidade)
        VALUES (?, 'SAIDA', ?)
    """, (produto_id, qtd))

    cursor.execute("""
        UPDATE produtos SET quantidade = quantidade - ?
        WHERE id = ?
    """, (qtd, produto_id))

    conn.commit()
    conn.close()

    return redirect("/estoque")


# ==========================
# START
# ==========================

if __name__ == "__main__":
    criar_banco()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
