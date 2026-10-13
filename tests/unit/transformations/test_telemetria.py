from datetime import UTC, datetime, timedelta
from decimal import Decimal

from f1.domain.modelos import DadosCarro
from f1.transformations.telemetria import (
    IntervaloVolta,
    agregar_por_volta,
    intervalos_das_voltas,
)

BASE = datetime(2024, 4, 21, 7, 0, tzinfo=UTC)


def amostra(segundos: float, speed=300, throttle=100, brake=0, drs=0, piloto=1):
    return DadosCarro(
        session_key=9673,
        meeting_key=1233,
        date=BASE + timedelta(seconds=segundos),
        driver_number=piloto,
        speed=speed,
        rpm=11000,
        n_gear=8,
        throttle=throttle,
        brake=brake,
        drs=drs,
    )


def test_intervalos_das_voltas_contiguos_e_ultima_pela_duracao(fabrica_volta):
    voltas = [
        fabrica_volta(
            lap_number=2, date_start=BASE + timedelta(seconds=100), lap_duration=Decimal("95.5")
        ),
        fabrica_volta(lap_number=1, date_start=BASE, lap_duration=Decimal("100")),
    ]

    assert intervalos_das_voltas(voltas) == [
        IntervaloVolta(1, BASE, BASE + timedelta(seconds=100)),
        IntervaloVolta(2, BASE + timedelta(seconds=100), BASE + timedelta(seconds=195.5)),
    ]


def test_intervalos_das_voltas_descarta_ultima_sem_duracao_e_voltas_sem_inicio(fabrica_volta):
    voltas = [
        fabrica_volta(lap_number=1, date_start=None),
        fabrica_volta(lap_number=2, date_start=BASE, lap_duration=None),
    ]

    assert intervalos_das_voltas(voltas) == []


def test_agregar_por_volta_calcula_metricas_e_ignora_amostras_fora_das_voltas(fabrica_volta):
    voltas = [
        fabrica_volta(lap_number=1, date_start=BASE, lap_duration=Decimal("10")),
        fabrica_volta(
            lap_number=2, date_start=BASE + timedelta(seconds=10), lap_duration=Decimal("10")
        ),
    ]
    amostras = [
        amostra(-1),  # antes da largada
        amostra(1, speed=300, throttle=100, drs=12),
        amostra(2, speed=200, throttle=50, brake=100),
        amostra(3, speed=None, throttle=None, drs=8),
        amostra(11, speed=310, throttle=100),
        amostra(20),  # depois da bandeirada
        amostra(5, piloto=44),  # outro piloto
    ]

    resultado = agregar_por_volta(9673, 1, amostras, voltas)

    assert len(resultado) == 2
    primeira, segunda = resultado
    assert primeira.lap_number == 1
    assert primeira.amostras == 3
    assert primeira.velocidade_maxima == 300
    assert primeira.velocidade_media == 250.0
    assert primeira.acelerador_medio_pct == 75.0
    assert primeira.acelerador_pleno_pct == 33.33
    assert primeira.freio_acionado_pct == 33.33
    assert primeira.drs_aberto_pct == 33.33
    assert segunda.amostras == 1
    assert segunda.velocidade_maxima == 310


def test_agregar_por_volta_sem_voltas_retorna_vazio():
    assert agregar_por_volta(9673, 1, [amostra(1)], []) == []


def test_agregar_por_volta_amostras_sem_velocidade(fabrica_volta):
    voltas = [fabrica_volta(lap_number=1, date_start=BASE, lap_duration=Decimal("10"))]

    resultado = agregar_por_volta(9673, 1, [amostra(1, speed=None, throttle=None)], voltas)

    assert resultado[0].velocidade_maxima is None
    assert resultado[0].velocidade_media is None
    assert resultado[0].acelerador_medio_pct is None
    assert resultado[0].acelerador_pleno_pct == 0.0
