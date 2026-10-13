from pathlib import Path

import duckdb
import pytest

from f1.repositories import duckdb_base
from f1.repositories.duckdb_base import conexao_sob_demanda


class ConexaoFalsa:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None


def test_conexao_sob_demanda_repete_enquanto_o_banco_esta_bloqueado(monkeypatch):
    respostas = iter([duckdb.IOException("em uso"), duckdb.IOException("em uso"), ConexaoFalsa()])

    def conectar(caminho):
        resposta = next(respostas)
        if isinstance(resposta, Exception):
            raise resposta
        return resposta

    monkeypatch.setattr(duckdb_base.duckdb, "connect", conectar)
    esperas: list[float] = []

    conexao = conexao_sob_demanda(Path("f1.duckdb"), espera_s=0.5, dormir=esperas.append)()

    assert isinstance(conexao, ConexaoFalsa)
    assert esperas == [0.5, 0.5]


def test_conexao_sob_demanda_desiste_apos_as_tentativas(monkeypatch):
    def conectar(caminho):
        raise duckdb.IOException("em uso")

    monkeypatch.setattr(duckdb_base.duckdb, "connect", conectar)

    with pytest.raises(duckdb.IOException):
        conexao_sob_demanda(Path("f1.duckdb"), tentativas=3, dormir=lambda _: None)()
