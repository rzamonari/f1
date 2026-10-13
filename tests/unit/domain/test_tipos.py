from decimal import Decimal

import pytest

from f1.domain.tipos import GAP_LIDER, Gap


def test_gap_lider_tem_zero_segundos():
    assert GAP_LIDER.eh_lider
    assert GAP_LIDER.segundos == Decimal(0)


@pytest.mark.parametrize(
    "gap", [Gap(segundos=Decimal("0.1")), Gap(voltas=1)], ids=["segundos", "voltas"]
)
def test_gap_que_nao_e_zero_nao_e_lider(gap):
    assert not gap.eh_lider


@pytest.mark.parametrize(
    "argumentos", [{}, {"segundos": Decimal(1), "voltas": 1}], ids=["nenhum", "ambos"]
)
def test_gap_exige_exatamente_uma_medida(argumentos):
    with pytest.raises(ValueError, match="exatamente um"):
        Gap(**argumentos)
