"""Início (visão do mês) e Resultado (relatório por período)."""
from __future__ import annotations

from datetime import date

from PySide6.QtCore import QDate
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QScrollArea, QVBoxLayout, QWidget

from ... import db
from ...money import brl, num, pct
from ...services import relatorios
from .. import widgets as w


def _mes_atual(hoje: date) -> tuple[date, date]:
    ini = hoje.replace(day=1)
    prox = date(hoje.year + (hoje.month == 12), hoje.month % 12 + 1, 1)
    return ini, date.fromordinal(prox.toordinal() - 1)


def _painel(titulo: str, conteudo: QWidget, dica: str = "") -> QFrame:
    quadro = QFrame()
    quadro.setObjectName("Painel")
    lay = QVBoxLayout(quadro)
    lay.setContentsMargins(16, 14, 16, 14)
    lay.addWidget(w.rotulo(titulo, "SecaoTitulo"))
    if dica:
        lay.addWidget(w.rotulo(dica, "Suave"))
    lay.addWidget(conteudo, 1)
    return quadro


def _tom_resultado(valor) -> str | None:
    return "ok" if valor > 0 else ("alerta" if valor < 0 else None)


class InicioPage(QWidget):
    def __init__(self, ir_para, parent=None):
        super().__init__(parent)
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(28, 24, 28, 24)
        raiz.setSpacing(16)

        topo = QHBoxLayout()
        titulos = QVBoxLayout()
        titulos.setSpacing(2)
        titulos.addWidget(w.rotulo("Início", "TituloPagina"))
        self.mes = w.rotulo("", "Subtitulo")
        titulos.addWidget(self.mes)
        topo.addLayout(titulos, 1)
        topo.addWidget(w.botao("Nova venda", lambda: ir_para("vendas"), primario=True))
        topo.addWidget(w.botao("Nova produção", lambda: ir_para("producao")))
        topo.addWidget(w.botao("Nova compra", lambda: ir_para("compras")))
        raiz.addLayout(topo)

        self.faixa = w.Faixa(["Receita", "Lucro bruto", "Despesas", "Resultado do mês"])
        raiz.addWidget(self.faixa)

        meio = QHBoxLayout()
        meio.setSpacing(16)
        self.grafico = w.GraficoBarras("Receita", "Custos e despesas")
        meio.addWidget(_painel("Últimos 6 meses", self.grafico), 3)
        self.alertas = w.make_table(["Item", "Saldo", "Mínimo"])
        self.alertas.setMinimumHeight(190)
        meio.addWidget(_painel("Precisa de atenção", self.alertas, "Itens no estoque mínimo ou abaixo dele."), 2)
        raiz.addLayout(meio, 3)

        self.top = w.make_table(["Produto", "Vendidos", "Receita", "Lucro"])
        self.top.setMinimumHeight(130)
        raiz.addWidget(_painel("Mais vendidos no mês", self.top), 1)

    def refresh(self) -> None:
        hoje = date.today()
        ini, fim = _mes_atual(hoje)
        self.mes.setText(f"{w.MESES[hoje.month - 1].capitalize()} de {hoje.year}")
        with db.session_scope() as s:
            r = relatorios.resumo_periodo(s, ini, fim)
            serie = relatorios.serie_mensal(s, 6, hoje)
            baixos = relatorios.estoque_baixo(s)
            top = relatorios.top_produtos(s, ini, fim, 5)
        self.faixa.definir("Receita", brl(r.receita))
        self.faixa.definir("Lucro bruto", brl(r.lucro_bruto))
        self.faixa.definir("Despesas", brl(r.despesas))
        self.faixa.definir("Resultado do mês", brl(r.resultado), _tom_resultado(r.resultado))
        self.grafico.definir([(w.MESES_CURTOS[m["mes"] - 1], float(m["receita"]), float(m["custos"])) for m in serie])
        w.fill_table(self.alertas, [(None, [b["nome"], f"{num(b['atual'])} {b['unidade']}", num(b["minimo"])], "alerta")
                                    for b in baixos], (1, 2))
        w.fill_table(self.top, [(None, [t["produto"], num(t["quantidade"]), brl(t["receita"]), brl(t["lucro"])], None)
                                for t in top], (1, 2, 3))


class ResultadoPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(28, 24, 28, 24)
        raiz.setSpacing(14)
        raiz.addWidget(w.rotulo("Resultado", "TituloPagina"))
        raiz.addWidget(w.rotulo("Receita menos o custo dos produtos vendidos e menos as despesas do período.", "Subtitulo"))

        barra = QHBoxLayout()
        ini, fim = _mes_atual(date.today())
        self.de, self.ate = w.date_edit(ini), w.date_edit(date.today())
        barra.addWidget(w.rotulo("De"))
        barra.addWidget(self.de)
        barra.addWidget(w.rotulo("até"))
        barra.addWidget(self.ate)
        barra.addWidget(w.botao("Este mês", self.este_mes))
        barra.addWidget(w.botao("Mês passado", self.mes_passado))
        barra.addStretch(1)
        raiz.addLayout(barra)
        self.de.dateChanged.connect(self.refresh)
        self.ate.dateChanged.connect(self.refresh)

        self.faixa = w.Faixa(["Receita", "Custo dos produtos vendidos", "Lucro bruto", "Despesas", "Resultado"])
        raiz.addWidget(self.faixa)
        self.nota = w.rotulo("", "Suave")
        raiz.addWidget(self.nota)

        grade = QGridLayout()
        grade.setSpacing(16)
        self.t_prod = w.make_table(["Produto", "Qtd.", "Receita", "Lucro"])
        self.t_pag = w.make_table(["Forma", "Total"])
        self.t_desp = w.make_table(["Categoria", "Total"])
        grade.addWidget(_painel("Produtos", self.t_prod), 0, 0, 2, 1)
        grade.addWidget(_painel("Formas de pagamento", self.t_pag), 0, 1)
        grade.addWidget(_painel("Despesas por categoria", self.t_desp), 1, 1)
        grade.setColumnStretch(0, 3)
        grade.setColumnStretch(1, 2)
        raiz.addLayout(grade, 1)

    def _definir(self, ini: date, fim: date) -> None:
        self.de.blockSignals(True)
        self.ate.blockSignals(True)
        self.de.setDate(QDate(ini.year, ini.month, ini.day))
        self.ate.setDate(QDate(fim.year, fim.month, fim.day))
        self.de.blockSignals(False)
        self.ate.blockSignals(False)
        self.refresh()

    def este_mes(self) -> None:
        ini, _ = _mes_atual(date.today())
        self._definir(ini, date.today())

    def mes_passado(self) -> None:
        primeiro = date.today().replace(day=1)
        ultimo = date.fromordinal(primeiro.toordinal() - 1)
        self._definir(ultimo.replace(day=1), ultimo)

    def refresh(self, *_) -> None:
        ini, fim = w.to_date(self.de), w.to_date(self.ate)
        with db.session_scope() as s:
            r = relatorios.resumo_periodo(s, ini, fim)
            top = relatorios.top_produtos(s, ini, fim, 20)
            pag = relatorios.vendas_por_forma_pagamento(s, ini, fim)
            desp = relatorios.despesas_por_categoria(s, ini, fim)
            em_insumos, em_produtos = relatorios.valor_em_estoque(s)
        self.faixa.definir("Receita", brl(r.receita))
        self.faixa.definir("Custo dos produtos vendidos", brl(r.cmv))
        self.faixa.definir("Lucro bruto", brl(r.lucro_bruto))
        self.faixa.definir("Despesas", brl(r.despesas))
        self.faixa.definir("Resultado", brl(r.resultado), _tom_resultado(r.resultado))
        self.nota.setText(
            f"{r.num_vendas} vendas, ticket médio {brl(r.ticket_medio)}, margem bruta {pct(r.margem_bruta_pct)}.   "
            f"Compras de insumos no período: {brl(r.compras_insumos)} (o custo só entra no resultado quando o produto é vendido).   "
            f"Estoque hoje: {brl(em_insumos)} em insumos e {brl(em_produtos)} em produtos prontos.")
        w.fill_table(self.t_prod, [(None, [t["produto"], num(t["quantidade"]), brl(t["receita"]), brl(t["lucro"])], None)
                                   for t in top], (1, 2, 3))
        w.fill_table(self.t_pag, [(None, [f, brl(v)], None) for f, v in pag], (1,))
        w.fill_table(self.t_desp, [(None, [c, brl(v)], None) for c, v in desp], (1,))
