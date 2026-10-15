from brownie_erp.demo import banco_vazio, carregar_exemplo
from brownie_erp.models import MovimentoEstoque, Insumo, Produto


def test_dados_de_exemplo_mantem_estoque_consistente(session):
    assert banco_vazio(session)
    carregar_exemplo(session)
    assert not banco_vazio(session)
    # nenhum saldo negativo e o saldo de cada insumo bate com a soma dos movimentos (kardex)
    for classe, coluna in ((Insumo, MovimentoEstoque.insumo_id), (Produto, MovimentoEstoque.produto_id)):
        for item in session.query(classe):
            assert item.estoque_atual >= 0
            soma = sum(m.quantidade for m in session.query(MovimentoEstoque).filter(coluna == item.id))
            assert soma == item.estoque_atual, item.nome
