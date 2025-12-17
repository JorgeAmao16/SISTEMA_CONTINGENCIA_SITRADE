"""
Servicio de consulta de DAM.
Busca en diccionario interno con registros de ejemplo.
Devuelve régimen, año, aduana, fechas y datos del exportador.
"""

from datetime import date
import calendar


def _add_one_month(d: date) -> date:
    """Suma un mes a una fecha, ajustando fin de mes si es necesario."""
    year = d.year
    month = d.month + 1
    if month > 12:
        month = 1
        year += 1
    last_day = calendar.monthrange(year, month)[1]
    day = min(d.day, last_day)
    return date(year, month, day)


DAM_REGISTROS = {
    "084228": {
        "regimen": "40 - Exportación Definitiva",
        "anio_dam": 2025,
        "aduana_num": "235 - AEROPUERTO INTL JORGE CHÁVEZ",
        "fecha_numeracion": date(2025, 11, 12),
        "exportador": "INCA TOPS S.A.",
        "agencia_aduanas": "PALACIOS & ASOCIADOS AGENTES DE ADUANA S.A",
    },
    "084631": {
        "regimen": "40 - Exportación Definitiva",
        "anio_dam": 2025,
        "aduana_num": "235 - AEROPUERTO INTL JORGE CHÁVEZ",
        "fecha_numeracion": date(2025, 11, 13),
        "exportador": "TEXCORP S.A.C.",
        "agencia_aduanas": "R Y R AGENCIA DE ADUANAS S.A.C.",
    },
    "084681": {
        "regimen": "40 - Exportación Definitiva",
        "anio_dam": 2025,
        "aduana_num": "235 - AEROPUERTO INTL JORGE CHÁVEZ",
        "fecha_numeracion": date(2025, 11, 13),
        "exportador": "REYCAL COMPANY S.A.C.",
        "agencia_aduanas": "ASESORIA Y GESTION EN ADUANAS SOCIEDAD ANONIMA",
    },
    "082075": {
        "regimen": "40 - Exportación Definitiva",
        "anio_dam": 2025,
        "aduana_num": "235 - AEROPUERTO INTL JORGE CHÁVEZ",
        "fecha_numeracion": date(2025, 11, 4),
        "exportador": "INCA TOPS S.A.",
        "agencia_aduanas": "PALACIOS & ASOCIADOS AGENTES DE ADUANA S.A",
    },
}


def consultar_dam(numero_dam: str):
    """Consulta DAM en registro interno."""
    codigo = numero_dam.strip()

    if codigo not in DAM_REGISTROS:
        raise ValueError(f"La DAM '{codigo}' no existe.")

    datos = DAM_REGISTROS[codigo]
    f_num = datos["fecha_numeracion"]
    f_ven = _add_one_month(f_num)

    return {
        "regimen": datos["regimen"],
        "anio_dam": datos["anio_dam"],
        "aduana_num": datos["aduana_num"],
        "fecha_numeracion": f_num,
        "fecha_vencimiento": f_ven,
        "exportador": datos["exportador"],
        "agencia_aduanas": datos["agencia_aduanas"],
    }
