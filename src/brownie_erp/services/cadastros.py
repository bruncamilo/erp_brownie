"""Cadastros: insumos, fornecedores, produtos e ficha técnica."""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..errors import RegraDeNegocio
from ..models import UNIDADES, FichaItem, Fornecedor, Insumo, MovimentoEstoque, Produto
from ..money import D


def _nome_valido(session: Session, classe, nome: str, ignorar_id: int | None = None) -> str:
    nome = (nome or "").strip()
    if not nome:
        raise RegraDeNegocio("Informe o nome.")
    stmt = select(classe.id).where(func.lower(classe.nome) == nome.lower())
    existente = session.scalar(stmt)
    if existente is not None and existente != ignorar_id:
        raise RegraDeNegocio(f"Já existe um cadastro chamado \"{nome}\".")
    return nome


# --- Insumos -----------------------------------------------------------------
def criar_insumo(session: Session, nome: str, unidade: str, estoque_minimo=0) -> Insumo:
    if unidade not in UNIDADES:
        raise RegraDeNegocio("Unidade inválida.")
    if D(estoque_minimo) < 0:
        raise RegraDeNegocio("O estoque mínimo não pode ser negativo.")
    insumo = Insumo(nome=_nome_valido(session, Insumo, nome), unidade=unidade, estoque_minimo=D(estoque_minimo))
    session.add(insumo)
    session.flush()
    return insumo


def atualizar_insumo(session: Session, insumo_id: int, nome: str, unidade: str, estoque_minimo=0) -> Insumo:
    insumo = session.get(Insumo, insumo_id)
    if unidade != insumo.unidade:
        movimentos = session.scalar(select(func.count()).where(MovimentoEstoque.insumo_id == insumo_id))
        if movimentos:
            raise RegraDeNegocio("A unidade não pode mudar depois que o insumo teve movimentação.")
        if unidade not in UNIDADES:
            raise RegraDeNegocio("Unidade inválida.")
        insumo.unidade = unidade
    if D(estoque_minimo) < 0:
        raise RegraDeNegocio("O estoque mínimo não pode ser negativo.")
    insumo.nome = _nome_valido(session, Insumo, nome, insumo_id)
    insumo.estoque_minimo = D(estoque_minimo)
    return insumo


def definir_insumo_ativo(session: Session, insumo_id: int, ativo: bool) -> None:
    insumo = session.get(Insumo, insumo_id)
    if not ativo:
        usado_em = session.scalars(
            select(Produto.nome).join(FichaItem).where(FichaItem.insumo_id == insumo_id, Produto.ativo.is_(True))
        ).all()
        if usado_em:
            raise RegraDeNegocio(
                "Este insumo faz parte da ficha técnica de: " + ", ".join(usado_em)
                + ". Tire-o das fichas antes de inativar."
            )
    insumo.ativo = ativo


# --- Fornecedores ------------------------------------------------------------
def criar_fornecedor(session: Session, nome: str, telefone: str = "", observacao: str = "") -> Fornecedor:
    f = Fornecedor(nome=_nome_valido(session, Fornecedor, nome), telefone=telefone.strip(), observacao=observacao.strip())
    session.add(f)
    session.flush()
    return f


def atualizar_fornecedor(session: Session, fornecedor_id: int, nome: str, telefone: str = "", observacao: str = "") -> Fornecedor:
    f = session.get(Fornecedor, fornecedor_id)
    f.nome = _nome_valido(session, Fornecedor, nome, fornecedor_id)
    f.telefone = telefone.strip()
    f.observacao = observacao.strip()
    return f


def definir_fornecedor_ativo(session: Session, fornecedor_id: int, ativo: bool) -> None:
    session.get(Fornecedor, fornecedor_id).ativo = ativo


# --- Produtos ----------------------------------------------------------------
def _validar_produto(preco_venda, rendimento, estoque_minimo) -> None:
    if D(preco_venda) < 0:
        raise RegraDeNegocio("O preço de venda não pode ser negativo.")
    if D(rendimento) <= 0:
        raise RegraDeNegocio("O rendimento por lote deve ser maior que zero.")
    if D(estoque_minimo) < 0:
        raise RegraDeNegocio("O estoque mínimo não pode ser negativo.")


def criar_produto(session: Session, nome: str, preco_venda, rendimento=1, categoria: str = "", estoque_minimo=0) -> Produto:
    _validar_produto(preco_venda, rendimento, estoque_minimo)
    p = Produto(
        nome=_nome_valido(session, Produto, nome), categoria=categoria.strip(),
        preco_venda=D(preco_venda), rendimento=D(rendimento), estoque_minimo=D(estoque_minimo),
    )
    session.add(p)
    session.flush()
    return p


def atualizar_produto(session: Session, produto_id: int, nome: str, preco_venda, rendimento=1,
                      categoria: str = "", estoque_minimo=0) -> Produto:
    _validar_produto(preco_venda, rendimento, estoque_minimo)
    p = session.get(Produto, produto_id)
    p.nome = _nome_valido(session, Produto, nome, produto_id)
    p.categoria = categoria.strip()
    p.preco_venda = D(preco_venda)
    p.rendimento = D(rendimento)
    p.estoque_minimo = D(estoque_minimo)
    return p


def definir_produto_ativo(session: Session, produto_id: int, ativo: bool) -> None:
    p = session.get(Produto, produto_id)
    if not ativo and p.estoque_atual > 0:
        raise RegraDeNegocio("Não é possível inativar um produto com estoque. Venda ou registre a perda antes.")
    p.ativo = ativo


def salvar_ficha(session: Session, produto_id: int, itens: list[dict]) -> Produto:
    """Substitui a ficha técnica. itens: [{"insumo_id": int, "quantidade": Decimal}] (por lote)."""
    p = session.get(Produto, produto_id)
    vistos: set[int] = set()
    novos: list[FichaItem] = []
    for it in itens:
        insumo = session.get(Insumo, it["insumo_id"])
        qtd = D(it["quantidade"])
        if insumo is None or not insumo.ativo:
            raise RegraDeNegocio("A ficha usa um insumo inexistente ou inativo.")
        if qtd <= 0:
            raise RegraDeNegocio(f"Informe a quantidade de {insumo.nome}.")
        if insumo.id in vistos:
            raise RegraDeNegocio(f"{insumo.nome} aparece duas vezes na ficha.")
        vistos.add(insumo.id)
        novos.append(FichaItem(insumo_id=insumo.id, quantidade=qtd))
    p.ficha.clear()
    session.flush()
    p.ficha.extend(novos)
    session.flush()
    return p
