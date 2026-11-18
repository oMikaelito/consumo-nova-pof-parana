import inspect
import io
import math
import re
import unicodedata

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Consumo por grau de processamento | POF IBGE", layout="wide")

TEXT_COLOR = "#2B2B2B"
GRID_COLOR = "#E5E5E5"
ANO_COLOR_MAP = {"2008": "#E09F00", "2018": "#9D0208"}

ACCEPTED_YEARS = (2008, 2018)
PERIODO_ANO = {2008: "2008-2009", 2018: "2017-2018"}
ANO_PERIODO = {periodo: ano for ano, periodo in PERIODO_ANO.items()}
ROTULO_ANO = {ano: f"POF {periodo}" for ano, periodo in PERIODO_ANO.items()}

GROUP_ORDER = ["In natura", "Processados", "Ultraprocessados", "Não classificado"]
GROUP_COLORS = {
    "In natura": "#2A9D8F",
    "Processados": "#6C5B7B",
    "Ultraprocessados": "#E76F51",
    "Não classificado": "#B0B0B0",
}
LABEL_TEXT_COLORS = {
    "In natura": TEXT_COLOR,
    "Processados": "#FFFFFF",
    "Ultraprocessados": TEXT_COLOR,
    "Não classificado": TEXT_COLOR,
}

RESULT_COLUMNS = [
    "Periodo", "Ano_Pesquisa", "Grupo", "Participacao_Pct", "IC95_inferior", "IC95_superior", "N_Pessoas",
]
DIFF_COLUMNS = [
    "Grupo", "Participacao_2008_2009", "Participacao_2017_2018", "Diferenca_pp",
    "IC95_inferior", "IC95_superior", "Variacao_relativa_pct", "Diferenca_significativa",
]
DIFF_CORE_COLUMNS = ["Grupo", "Diferenca_pp", "IC95_inferior", "IC95_superior"]
SHEET_KEYS = {"resultado": "Resultados", "diferenca": "Diferencas", "nota": "Notas"}

Z_95 = 1.96
SUM_RANGE = (99.5, 100.5)
DIVERGENCE_TOLERANCE = 0.1
LABEL_MIN_PCT = 3.0

TITLE = "Consumo de calorias por grau de processamento: Paraná, 15 a 29 anos"
SUBTITLE = (
    "Participação (%) de cada grupo da classificação NOVA no total de calorias consumidas, "
    "sem o grupo 2 (ingredientes culinários). "
    "Fonte: IBGE, POF 2008-2009 e 2017-2018, consumo alimentar individual."
)
GROUP2_BANNER = (
    "O grupo 2 (ingredientes culinários) não foi incluído nos cálculos porque não é comparável "
    "entre as duas pesquisas. Por isso os percentuais não são diretamente comparáveis aos "
    "publicados que incluem esse grupo. Veja os detalhes em 'Notas e limitações'."
)

MOTIVO_EM_BRANCO = "linhas em branco"
MOTIVO_PERIODO = "Periodo fora do esperado"
MOTIVO_ANO = "Ano_Pesquisa fora do esperado"
MOTIVO_NAO_COMBINAM = "Periodo e Ano_Pesquisa que não combinam"
MOTIVO_GRUPO = "Grupo fora da lista"
MOTIVO_NAO_NUMERICO = "valor que não é número (participação ou intervalo)"
MOTIVO_FORA_0_100 = "participação fora do intervalo de 0 a 100"
MOTIVO_REPETIDA = "linha repetida para o mesmo período e grupo (foi mantida a primeira)"


def normalize_text_key(text) -> str:
    if text is None or (not isinstance(text, str) and pd.isna(text)):
        return ""
    ascii_text = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode()
    words = re.findall(r"[a-z0-9]+", ascii_text.lower())
    words = [w[:-1] if len(w) > 3 and w.endswith("s") else w for w in words]
    return "".join(words)


GROUP_LOOKUP = {normalize_text_key(nome): nome for nome in GROUP_ORDER}


def format_number_br(value: float, decimals: int = 1) -> str:
    texto = f"{value:,.{decimals}f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def format_pct(value) -> str:
    if pd.isna(value):
        return "—"
    return f"{format_number_br(value)}%"


def format_signed(value, suffix: str) -> str:
    if pd.isna(value):
        return "—"
    rounded = round(float(value), 1) + 0.0
    if rounded == 0:
        return f"0,0{suffix}"
    sinal = "+" if rounded > 0 else "-"
    return f"{sinal}{format_number_br(abs(rounded))}{suffix}"


def format_pp(value) -> str:
    return format_signed(value, " p.p.")


def format_relative(value) -> str:
    return format_signed(value, "%")


def format_count(value) -> str:
    if pd.isna(value):
        return "—"
    return format_number_br(value, 0)


def escape_markdown(text) -> str:
    return str(text).replace("$", "\\$")


def lighten(hex_color: str, factor: float = 0.6) -> str:
    canais = [int(hex_color[i:i + 2], 16) for i in (1, 3, 5)]
    claros = [int(c + (255 - c) * factor) for c in canais]
    return "#{:02X}{:02X}{:02X}".format(*claros)


def parse_number(value) -> float:
    if value is None or isinstance(value, bool):
        return np.nan
    if not isinstance(value, str) and pd.isna(value):
        return np.nan
    if isinstance(value, (int, float, np.integer, np.floating)):
        numero = float(value)
    else:
        texto = str(value).strip().replace("%", "").replace(" ", "")
        if texto == "":
            return np.nan
        if "," in texto:
            texto = texto.replace(".", "").replace(",", ".")
        try:
            numero = float(texto)
        except ValueError:
            return np.nan
    return numero if math.isfinite(numero) else np.nan


def normalize_period(value) -> str:
    if value is None or (not isinstance(value, str) and pd.isna(value)):
        return ""
    texto = str(value).strip().replace("–", "-").replace("—", "-")
    return re.sub(r"\s+", "", texto)


def parse_yes_no(value):
    chave = normalize_text_key(value)
    if chave == "sim":
        return True
    if chave == "nao":
        return False
    return None


def is_significant(ic_inferior, ic_superior):
    if pd.isna(ic_inferior) or pd.isna(ic_superior):
        return None
    return bool(ic_inferior > 0 or ic_superior < 0)


def stretch_kwargs(func) -> dict:
    # Streamlit novo usa width="stretch"; versões antigas usam use_container_width.
    width = inspect.signature(func).parameters.get("width")
    if width is not None and width.default == "stretch":
        return {"width": "stretch"}
    return {"use_container_width": True}


PLOTLY_STRETCH = stretch_kwargs(st.plotly_chart)
DATAFRAME_STRETCH = stretch_kwargs(st.dataframe)


def find_sheets(sheet_names: list) -> dict:
    encontradas = {}
    for nome in sheet_names:
        canonico = SHEET_KEYS.get(normalize_text_key(nome))
        if canonico and canonico not in encontradas:
            encontradas[canonico] = nome
    return encontradas


def read_sheet(excel: pd.ExcelFile, sheet_name: str) -> pd.DataFrame:
    df = excel.parse(sheet_name, dtype=object)
    df.columns = [str(c).strip() for c in df.columns]
    return df


def read_notes(excel: pd.ExcelFile, sheet_name: str) -> list:
    df = excel.parse(sheet_name, header=None, dtype=object)
    notas = []
    for linha in df.itertuples(index=False):
        titulo = "" if pd.isna(linha[0]) else str(linha[0]).strip()
        texto = "" if len(linha) < 2 or pd.isna(linha[1]) else str(linha[1]).strip()
        if titulo or texto:
            notas.append((titulo, texto))
    return notas


def clean_results(df_raw: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    contagem = {
        MOTIVO_EM_BRANCO: 0, MOTIVO_PERIODO: 0, MOTIVO_ANO: 0, MOTIVO_NAO_COMBINAM: 0,
        MOTIVO_GRUPO: 0, MOTIVO_NAO_NUMERICO: 0, MOTIVO_FORA_0_100: 0, MOTIVO_REPETIDA: 0,
    }
    periodos_fora, anos_fora, grupos_fora = set(), set(), set()
    linhas, vistos = [], set()

    for registro in df_raw[RESULT_COLUMNS].to_dict("records"):
        if all(pd.isna(v) for v in registro.values()):
            contagem[MOTIVO_EM_BRANCO] += 1
            continue

        periodo = normalize_period(registro["Periodo"])
        if periodo not in ANO_PERIODO:
            contagem[MOTIVO_PERIODO] += 1
            periodos_fora.add(periodo or "(vazio)")
            continue

        ano = parse_number(registro["Ano_Pesquisa"])
        if pd.isna(ano) or ano not in ACCEPTED_YEARS:
            contagem[MOTIVO_ANO] += 1
            bruto = registro["Ano_Pesquisa"]
            anos_fora.add("(vazio)" if pd.isna(bruto) else str(bruto).strip())
            continue
        ano = int(ano)

        if ANO_PERIODO[periodo] != ano:
            contagem[MOTIVO_NAO_COMBINAM] += 1
            continue

        grupo = GROUP_LOOKUP.get(normalize_text_key(registro["Grupo"]))
        if grupo is None:
            contagem[MOTIVO_GRUPO] += 1
            bruto = registro["Grupo"]
            grupos_fora.add("(vazio)" if pd.isna(bruto) else str(bruto).strip())
            continue

        valor = parse_number(registro["Participacao_Pct"])
        inferior = parse_number(registro["IC95_inferior"])
        superior = parse_number(registro["IC95_superior"])
        if pd.isna(valor) or pd.isna(inferior) or pd.isna(superior):
            contagem[MOTIVO_NAO_NUMERICO] += 1
            continue
        if valor < 0 or valor > 100:
            contagem[MOTIVO_FORA_0_100] += 1
            continue

        if (periodo, grupo) in vistos:
            contagem[MOTIVO_REPETIDA] += 1
            continue
        vistos.add((periodo, grupo))

        linhas.append({
            "Periodo": periodo,
            "Ano_Pesquisa": ano,
            "Grupo": grupo,
            "Participacao_Pct": valor,
            "IC95_inferior": inferior,
            "IC95_superior": superior,
            "N_Pessoas": parse_number(registro["N_Pessoas"]),
        })

    df = pd.DataFrame(linhas, columns=RESULT_COLUMNS)
    detalhes = {
        "contagem": contagem,
        "periodos_fora": sorted(periodos_fora),
        "anos_fora": sorted(anos_fora),
        "grupos_fora": sorted(grupos_fora),
    }
    return df, detalhes


def collect_import_warnings(df: pd.DataFrame, detalhes: dict) -> tuple[list, dict]:
    avisos = []
    contagem = detalhes["contagem"]

    if detalhes["periodos_fora"]:
        avisos.append(
            f"Periodo fora do esperado: {', '.join(detalhes['periodos_fora'])}. "
            "Só 2008-2009 e 2017-2018 são aceitos; essas linhas foram ignoradas."
        )
    if detalhes["anos_fora"]:
        avisos.append(
            f"Ano_Pesquisa fora do esperado: {', '.join(detalhes['anos_fora'])}. "
            "Só 2008 e 2018 são aceitos; essas linhas foram ignoradas."
        )
    if contagem[MOTIVO_NAO_COMBINAM]:
        avisos.append(
            f"{contagem[MOTIVO_NAO_COMBINAM]} linha(s) com Periodo e Ano_Pesquisa que não combinam "
            "(2008-2009 com 2008 e 2017-2018 com 2018) foram ignoradas."
        )
    if detalhes["grupos_fora"]:
        avisos.append(
            f"Grupo fora da lista: {', '.join(detalhes['grupos_fora'])}. "
            f"Os nomes aceitos são: {', '.join(GROUP_ORDER)}. Essas linhas foram ignoradas."
        )
    if contagem[MOTIVO_NAO_NUMERICO]:
        avisos.append(
            f"{contagem[MOTIVO_NAO_NUMERICO]} linha(s) tinham valor que não é número em "
            "Participacao_Pct, IC95_inferior ou IC95_superior e foram ignoradas. "
            "Confira a planilha (números como 25,9 ou 25.9)."
        )
    if contagem[MOTIVO_FORA_0_100]:
        avisos.append(
            f"{contagem[MOTIVO_FORA_0_100]} linha(s) com Participacao_Pct fora do intervalo de 0 a 100 "
            "foram ignoradas."
        )
    if contagem[MOTIVO_REPETIDA]:
        avisos.append(
            f"{contagem[MOTIVO_REPETIDA]} linha(s) repetidas para o mesmo período e grupo. "
            "Foi usada só a primeira de cada uma; confira a planilha."
        )

    n_pessoas = {}
    for periodo in ANO_PERIODO:
        valores = df.loc[df["Periodo"] == periodo, "N_Pessoas"]
        distintos = sorted(set(valores.dropna().astype(int)))
        n_pessoas[periodo] = distintos[0] if distintos else None
        if len(valores) and valores.isna().any():
            avisos.append(
                f"N_Pessoas está vazio (ou não é número) em {int(valores.isna().sum())} linha(s) de "
                f"{periodo}. O número de pessoas fica como \"—\" quando não há valor."
            )
        if len(distintos) > 1:
            avisos.append(
                f"N_Pessoas tem valores diferentes dentro de {periodo}: "
                f"{', '.join(format_count(v) for v in distintos)}. Foi mostrado o primeiro."
            )

    for periodo in ANO_PERIODO:
        if not (df["Periodo"] == periodo).any():
            avisos.append(
                f"Falta o período {periodo} na aba Resultados. "
                "A comparação e a diferença precisam dos dois períodos."
            )

    for periodo, linhas in df.groupby("Periodo"):
        soma = linhas["Participacao_Pct"].sum()
        if not (SUM_RANGE[0] <= soma <= SUM_RANGE[1]):
            avisos.append(
                f"Em {periodo}, a soma dos grupos é {format_pct(soma)}; o esperado é perto de 100% "
                f"(entre {format_pct(SUM_RANGE[0])} e {format_pct(SUM_RANGE[1])}). "
                "Confira se algum grupo está faltando ou com valor diferente."
            )

    for linha in df.itertuples(index=False):
        if linha.IC95_inferior > linha.Participacao_Pct or linha.IC95_superior < linha.Participacao_Pct:
            avisos.append(
                f"O intervalo de confiança de {linha.Grupo} em {linha.Periodo} "
                f"({format_pct(linha.IC95_inferior)} a {format_pct(linha.IC95_superior)}) não contém "
                f"o valor {format_pct(linha.Participacao_Pct)}. Confira IC95_inferior e IC95_superior."
            )
    return avisos, n_pessoas


def compute_differences(df: pd.DataFrame) -> pd.DataFrame:
    colunas = ["Grupo", "Dif_pp", "Dif_inf", "Dif_sup", "Var_rel"]
    if not all((df["Ano_Pesquisa"] == ano).any() for ano in ACCEPTED_YEARS):
        return pd.DataFrame(columns=colunas)

    antes = df[df["Ano_Pesquisa"] == 2008].set_index("Grupo")
    depois = df[df["Ano_Pesquisa"] == 2018].set_index("Grupo")
    linhas = []
    for grupo in GROUP_ORDER:
        if grupo not in antes.index or grupo not in depois.index:
            continue
        a, d = antes.loc[grupo], depois.loc[grupo]
        diferenca = d["Participacao_Pct"] - a["Participacao_Pct"]
        erro_a = abs(a["IC95_superior"] - a["IC95_inferior"]) / (2 * Z_95)
        erro_d = abs(d["IC95_superior"] - d["IC95_inferior"]) / (2 * Z_95)
        erro_dif = math.sqrt(erro_a ** 2 + erro_d ** 2)
        variacao = diferenca / a["Participacao_Pct"] * 100 if a["Participacao_Pct"] > 0 else np.nan
        linhas.append({
            "Grupo": grupo,
            "Dif_pp": diferenca,
            "Dif_inf": diferenca - Z_95 * erro_dif,
            "Dif_sup": diferenca + Z_95 * erro_dif,
            "Var_rel": variacao,
        })
    return pd.DataFrame(linhas, columns=colunas)


def merge_difference_sheet(calculado: pd.DataFrame, df_sheet: pd.DataFrame) -> tuple[pd.DataFrame, list]:
    avisos = []
    colunas_faltando = [c for c in DIFF_CORE_COLUMNS if c not in df_sheet.columns]
    if colunas_faltando:
        avisos.append(
            f"A aba Diferencas está sem as colunas {', '.join(colunas_faltando)} e foi ignorada. "
            "As diferenças foram calculadas pelo app."
        )
        return calculado, avisos

    da_aba, grupos_fora = {}, set()
    for registro in df_sheet.to_dict("records"):
        if all(pd.isna(v) for v in registro.values()):
            continue
        grupo = GROUP_LOOKUP.get(normalize_text_key(registro["Grupo"]))
        if grupo is None:
            grupos_fora.add("(vazio)" if pd.isna(registro["Grupo"]) else str(registro["Grupo"]).strip())
            continue
        da_aba[grupo] = {
            "Dif_pp": parse_number(registro["Diferenca_pp"]),
            "Dif_inf": parse_number(registro["IC95_inferior"]),
            "Dif_sup": parse_number(registro["IC95_superior"]),
            "Var_rel": parse_number(registro.get("Variacao_relativa_pct")),
            "Sig": parse_yes_no(registro.get("Diferenca_significativa")),
        }
    if grupos_fora:
        avisos.append(
            f"A aba Diferencas tem grupo fora da lista: {', '.join(sorted(grupos_fora))}. "
            "Essas linhas foram ignoradas."
        )

    divergencias, sem_grupo, linhas = [], [], []
    for registro in calculado.to_dict("records"):
        grupo = registro["Grupo"]
        aba = da_aba.get(grupo)
        if aba is None:
            sem_grupo.append(grupo)
            linhas.append(registro)
            continue

        usado = dict(registro)
        campos = []
        for campo, nome in (("Dif_pp", "diferença"), ("Dif_inf", "limite inferior"),
                            ("Dif_sup", "limite superior"), ("Var_rel", "variação relativa")):
            valor_aba = aba[campo]
            if pd.isna(valor_aba):
                continue
            if pd.isna(registro[campo]) or abs(valor_aba - registro[campo]) > DIVERGENCE_TOLERANCE:
                campos.append(f"{nome} (aba: {format_number_br(valor_aba, 2)}; "
                              f"recalculado: {format_number_br(registro[campo], 2)})")
            usado[campo] = valor_aba
        significativa = is_significant(usado["Dif_inf"], usado["Dif_sup"])
        if aba["Sig"] is not None and significativa is not None and aba["Sig"] != significativa:
            campos.append("Diferenca_significativa (não bate com o intervalo de confiança)")
        if campos:
            divergencias.append(f"{grupo}: {'; '.join(campos)}")
        linhas.append(usado)

    if sem_grupo:
        avisos.append(
            f"A aba Diferencas não tem o grupo {', '.join(sem_grupo)}; para ele foi usado o valor "
            "calculado pelo app."
        )
    if divergencias:
        avisos.append(
            "A aba Diferencas diverge em mais de 0,1 do valor recalculado pelo app. "
            + " | ".join(divergencias)
            + ". Os números mostrados são os da aba Diferencas; confira o arquivo."
        )
    return pd.DataFrame(linhas, columns=calculado.columns), avisos


def process_workbook(file_bytes: bytes) -> dict:
    excel = pd.ExcelFile(io.BytesIO(file_bytes))
    abas = find_sheets(excel.sheet_names)
    colunas_esperadas = ", ".join(RESULT_COLUMNS)

    if "Resultados" not in abas:
        return {"erro": (
            "Não encontrei a aba \"Resultados\" no arquivo. "
            f"Abas encontradas: {', '.join(excel.sheet_names) or 'nenhuma'}. "
            f"A aba Resultados deve ter as colunas: {colunas_esperadas}. "
            "Confira o arquivo e envie de novo."
        )}

    df_raw = read_sheet(excel, abas["Resultados"])
    faltando = [c for c in RESULT_COLUMNS if c not in df_raw.columns]
    if faltando:
        return {"erro": (
            f"Faltam as colunas: {', '.join(faltando)}. "
            f"Colunas esperadas na aba Resultados: {colunas_esperadas}. "
            f"Colunas encontradas: {', '.join(df_raw.columns) or 'nenhuma'}. "
            "Confira o cabeçalho da aba e envie de novo."
        )}

    resultados, detalhes = clean_results(df_raw)
    avisos, n_pessoas = collect_import_warnings(resultados, detalhes)

    diferencas = compute_differences(resultados)
    if "Diferencas" in abas and not diferencas.empty:
        diferencas, avisos_diferencas = merge_difference_sheet(
            diferencas, read_sheet(excel, abas["Diferencas"])
        )
        avisos.extend(avisos_diferencas)
        fonte_diferencas = "aba Diferencas (conferida com o recálculo do app)"
    elif "Diferencas" in abas:
        fonte_diferencas = "aba Diferencas ignorada (faltam períodos na aba Resultados)"
    else:
        fonte_diferencas = "calculadas pelo app (o arquivo não tem a aba Diferencas)"

    notas = read_notes(excel, abas["Notas"]) if "Notas" in abas else None

    contagem = detalhes["contagem"]
    resumo = {
        "linhas_lidas": len(df_raw),
        "linhas_usadas": len(resultados),
        "ignoradas": [(motivo, n) for motivo, n in contagem.items() if n > 0],
        "periodos": [p for p in ANO_PERIODO if (resultados["Periodo"] == p).any()],
        "grupos": [g for g in GROUP_ORDER if (resultados["Grupo"] == g).any()],
        "n_pessoas": n_pessoas,
        "fonte_diferencas": fonte_diferencas,
        "tem_notas": notas is not None,
        "avisos": avisos,
    }
    return {
        "erro": None,
        "resultados": resultados,
        "diferencas": diferencas,
        "notas": notas,
        "resumo": resumo,
    }


@st.cache_data
def load_results_file(file_bytes: bytes) -> dict:
    return process_workbook(file_bytes)


def build_group_table(resultados: pd.DataFrame, diferencas: pd.DataFrame) -> pd.DataFrame:
    linhas = []
    for grupo in [g for g in GROUP_ORDER if (resultados["Grupo"] == g).any()]:
        registro = {"Grupo": grupo}
        for ano in ACCEPTED_YEARS:
            alvo = resultados[(resultados["Grupo"] == grupo) & (resultados["Ano_Pesquisa"] == ano)]
            if alvo.empty:
                valores = (np.nan, np.nan, np.nan)
            else:
                valores = tuple(alvo.iloc[0][["Participacao_Pct", "IC95_inferior", "IC95_superior"]])
            registro[f"Pct_{ano}"], registro[f"Inf_{ano}"], registro[f"Sup_{ano}"] = valores
        dif = diferencas[diferencas["Grupo"] == grupo]
        for campo in ("Dif_pp", "Dif_inf", "Dif_sup", "Var_rel"):
            registro[campo] = dif.iloc[0][campo] if not dif.empty else np.nan
        linhas.append(registro)
    return pd.DataFrame(linhas)


def show_chart(fig) -> None:
    st.plotly_chart(fig, theme=None, **PLOTLY_STRETCH)


def show_table(table: pd.DataFrame) -> None:
    st.dataframe(table, hide_index=True, **DATAFRAME_STRETCH)


def apply_chart_style(fig, margin: dict, height: int, show_legend: bool) -> None:
    fig.update_layout(
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(size=13, color=TEXT_COLOR),
        title_font=dict(size=18, color=TEXT_COLOR),
        title_x=0,
        margin=margin,
        height=height,
        separators=",.",
        showlegend=show_legend,
    )
    if show_legend:
        fig.update_layout(
            legend=dict(
                orientation="h", y=1.02, yanchor="bottom", x=0,
                title=dict(text=""), font=dict(color=TEXT_COLOR),
            )
        )
    for atualizar, grade in ((fig.update_xaxes, True), (fig.update_yaxes, False)):
        atualizar(
            automargin=True,
            title_font=dict(color=TEXT_COLOR),
            tickfont=dict(color=TEXT_COLOR),
            showgrid=grade,
            gridcolor=GRID_COLOR,
            linecolor=GRID_COLOR,
        )


def hover_participation(grupo, ano, valor, inferior, superior, n_pessoas) -> str:
    return (
        f"<b>{grupo}</b><br>{ROTULO_ANO[ano]}: {format_pct(valor)}"
        f"<br>Intervalo de confiança de 95%: {format_pct(inferior)} a {format_pct(superior)}"
        f"<br>Pessoas na amostra: {format_count(n_pessoas)}"
    )


def build_participation_chart(resultados: pd.DataFrame, show_error_bars: bool):
    grupos = [g for g in GROUP_ORDER if (resultados["Grupo"] == g).any()]
    deslocamento = {2008: -0.2, 2018: 0.2}
    fig = go.Figure()
    topo_maximo = 0.0

    for ano in ACCEPTED_YEARS:
        xs, ys, mais, menos, hover, rotulos, topos = [], [], [], [], [], [], []
        for posicao, grupo in enumerate(grupos):
            alvo = resultados[(resultados["Grupo"] == grupo) & (resultados["Ano_Pesquisa"] == ano)]
            if alvo.empty:
                continue
            r = alvo.iloc[0]
            valor, inferior, superior = r["Participacao_Pct"], r["IC95_inferior"], r["IC95_superior"]
            xs.append(posicao + deslocamento[ano])
            ys.append(valor)
            mais.append(max(superior - valor, 0))
            menos.append(max(valor - inferior, 0))
            hover.append(hover_participation(grupo, ano, valor, inferior, superior, r["N_Pessoas"]))
            rotulos.append(format_pct(valor))
            topos.append(max(valor, superior) if show_error_bars else valor)
        if not xs:
            continue
        topo_maximo = max(topo_maximo, max(topos))
        fig.add_trace(go.Bar(
            x=xs, y=ys, width=0.36, name=ROTULO_ANO[ano],
            marker_color=ANO_COLOR_MAP[str(ano)],
            error_y=dict(
                type="data", symmetric=False, array=mais, arrayminus=menos,
                color=TEXT_COLOR, thickness=1.5, width=5, visible=show_error_bars,
            ),
            hovertext=hover, hoverinfo="text",
        ))
        fig.add_trace(go.Scatter(
            x=xs, y=topos, mode="text", text=rotulos, textposition="top center",
            textfont=dict(size=13, color=TEXT_COLOR), showlegend=False,
            hoverinfo="skip", cliponaxis=False,
        ))

    fig.update_layout(title="Participação de cada grupo no total de calorias (sem o grupo 2)")
    apply_chart_style(fig, margin=dict(t=120, b=60, l=80, r=40), height=480, show_legend=True)
    fig.update_xaxes(
        tickmode="array", tickvals=list(range(len(grupos))), ticktext=grupos,
        range=[-0.6, len(grupos) - 0.4], showgrid=False,
    )
    fig.update_yaxes(
        title_text="Participação no total de calorias (%)", ticksuffix="%",
        range=[0, max(topo_maximo * 1.15, 1.0)], showgrid=True,
    )
    return fig


def build_composition_chart(resultados: pd.DataFrame):
    dados = resultados.copy()
    dados["Pesquisa"] = dados["Ano_Pesquisa"].map(ROTULO_ANO)
    dados["Rotulo"] = dados["Participacao_Pct"].apply(
        lambda v: format_pct(v) if v >= LABEL_MIN_PCT else ""
    )
    grupos = [g for g in GROUP_ORDER if g in set(dados["Grupo"])]
    limite_x = max(100.0, float(dados.groupby("Pesquisa")["Participacao_Pct"].sum().max()))

    fig = px.bar(
        dados, x="Participacao_Pct", y="Pesquisa", color="Grupo", orientation="h",
        barmode="stack", text="Rotulo", color_discrete_map=GROUP_COLORS,
        category_orders={"Grupo": grupos, "Pesquisa": [ROTULO_ANO[2008], ROTULO_ANO[2018]]},
        title="Composição do total de calorias por período (sem o grupo 2)",
    )
    fig.update_traces(
        textposition="inside", insidetextanchor="middle", textangle=0, textfont_size=13,
        hovertemplate="<b>%{y}</b><br>%{fullData.name}: %{x:,.1f}%<extra></extra>",
    )
    fig.for_each_trace(
        lambda t: t.update(textfont_color=LABEL_TEXT_COLORS.get(t.name, TEXT_COLOR))
    )
    apply_chart_style(fig, margin=dict(t=120, b=60, l=140, r=40), height=380, show_legend=True)
    fig.update_xaxes(
        title_text="Participação no total de calorias (%)", range=[0, limite_x], ticksuffix="%",
    )
    fig.update_yaxes(title_text="", autorange="reversed")
    return fig


def build_difference_chart(tabela: pd.DataFrame):
    dados = tabela.dropna(subset=["Dif_pp", "Dif_inf", "Dif_sup"])
    grupos = dados["Grupo"].tolist()
    diferencas = dados["Dif_pp"].tolist()
    inferiores = dados["Dif_inf"].tolist()
    superiores = dados["Dif_sup"].tolist()
    inclui_zero = [not is_significant(i, s) for i, s in zip(inferiores, superiores)]

    cores = [
        lighten(GROUP_COLORS[g]) if zero else GROUP_COLORS[g]
        for g, zero in zip(grupos, inclui_zero)
    ]
    hover = [
        f"<b>{g}</b><br>Diferença: {format_pp(d)}"
        f"<br>Intervalo de confiança de 95%: de {format_pp(i)} a {format_pp(s)}"
        f"<br>{'O intervalo inclui o zero' if z else 'O intervalo não inclui o zero'}"
        for g, d, i, s, z in zip(grupos, diferencas, inferiores, superiores, inclui_zero)
    ]

    limite_baixo = min([0.0] + inferiores)
    limite_alto = max([0.0] + superiores)
    amplitude = max(limite_alto - limite_baixo, 1.0)
    folga = amplitude * 0.03

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=diferencas, y=grupos, orientation="h", marker_color=cores,
        error_x=dict(
            type="data", symmetric=False,
            array=[max(s - d, 0) for d, s in zip(diferencas, superiores)],
            arrayminus=[max(d - i, 0) for d, i in zip(diferencas, inferiores)],
            color=TEXT_COLOR, thickness=1.5, width=5,
        ),
        hovertext=hover, hoverinfo="text", showlegend=False,
    ))
    fig.add_trace(go.Scatter(
        x=[(s + folga) if d >= 0 else (i - folga) for d, i, s in zip(diferencas, inferiores, superiores)],
        y=grupos, mode="text", text=[format_pp(d) for d in diferencas],
        textposition=["middle right" if d >= 0 else "middle left" for d in diferencas],
        textfont=dict(size=13, color=TEXT_COLOR), showlegend=False,
        hoverinfo="skip", cliponaxis=False,
    ))
    if any(inclui_zero):
        fig.add_trace(go.Bar(
            x=[None], y=[None], name="intervalo inclui o zero",
            marker_color=lighten("#808080", 0.6),
        ))
    fig.add_vline(x=0, line_width=1.5, line_color="#6B6B6B")

    fig.update_layout(title="Diferença em pontos percentuais por grupo (2017-2018 menos 2008-2009)")
    apply_chart_style(
        fig, margin=dict(t=120 if any(inclui_zero) else 80, b=60, l=180, r=40),
        height=380, show_legend=any(inclui_zero),
    )
    fig.update_xaxes(
        title_text="Diferença (pontos percentuais)", tickformat=",.1f",
        range=[limite_baixo - amplitude * 0.25, limite_alto + amplitude * 0.25],
        zeroline=False,
    )
    fig.update_yaxes(
        title_text="", categoryorder="array", categoryarray=grupos, autorange="reversed",
    )
    return fig


def show_import_summary(resumo: dict) -> None:
    with st.expander("Resumo da importação", expanded=True):
        total_ignoradas = sum(n for _, n in resumo["ignoradas"])
        linhas = [
            f"- Linhas lidas (aba Resultados): {resumo['linhas_lidas']}",
            f"- Linhas usadas: {resumo['linhas_usadas']}",
            f"- Linhas ignoradas: {total_ignoradas}",
        ]
        linhas.extend(f"  - {motivo}: {n}" for motivo, n in resumo["ignoradas"])
        linhas.append(f"- Períodos encontrados: {', '.join(resumo['periodos']) or 'nenhum'}")
        linhas.append(f"- Grupos encontrados: {', '.join(resumo['grupos']) or 'nenhum'}")
        linhas.append("- Pessoas na amostra (N_Pessoas) por período:")
        for periodo in ANO_PERIODO:
            n = resumo["n_pessoas"].get(periodo)
            linhas.append(f"  - {periodo}: {format_count(n) if n is not None else 'não informado'}")
        linhas.append(f"- Diferenças: {resumo['fonte_diferencas']}")
        linhas.append(f"- Aba Notas: {'encontrada' if resumo['tem_notas'] else 'não encontrada'}")
        st.markdown("\n".join(linhas))

        for aviso in resumo["avisos"]:
            st.warning(aviso)


def show_upload_guide() -> None:
    st.info("Envie o arquivo de resultados (.xlsx) pela barra lateral.")

    st.markdown(
        "Este app **não processa microdados**: ele só lê e mostra um arquivo .xlsx com resultados "
        "já calculados (gerado pelo script `processar_microdados.py`).\n\n"
        "**Abas do arquivo:**\n"
        "- `Resultados` (obrigatória), com as colunas `Periodo` (2008-2009 ou 2017-2018), "
        "`Ano_Pesquisa` (2008 ou 2018), `Grupo`, `Participacao_Pct`, `IC95_inferior`, "
        "`IC95_superior` e `N_Pessoas`.\n"
        "- `Diferencas` (opcional), com as colunas `Grupo`, `Participacao_2008_2009`, "
        "`Participacao_2017_2018`, `Diferenca_pp`, `IC95_inferior`, `IC95_superior`, "
        "`Variacao_relativa_pct` e `Diferenca_significativa` (Sim ou Não). "
        "Sem esta aba, o app calcula a diferença e o intervalo de confiança.\n"
        "- `Notas` (opcional), com duas colunas: título e texto. Aparecem em \"Notas e limitações\".\n"
        "- `Kcal_por_dia`: se existir, o app ignora.\n\n"
        f"**Grupos aceitos na coluna `Grupo`:** {', '.join(GROUP_ORDER)}. "
        "O grupo 2 (ingredientes culinários) fica de fora de propósito.\n\n"
        "`Participacao_Pct` e os limites do intervalo de confiança (`IC95_inferior` e "
        "`IC95_superior`) são porcentagens de 0 a 100 (25,9 significa 25,9%), com vírgula ou "
        "ponto decimal."
    )

    exemplo = pd.DataFrame({
        "Periodo": ["2008-2009", "2008-2009", "2017-2018", "2017-2018"],
        "Ano_Pesquisa": [2008, 2008, 2018, 2018],
        "Grupo": ["In natura", "Processados", "In natura", "Processados"],
        "Participacao_Pct": ["60,0", "40,0", "55,0", "45,0"],
        "IC95_inferior": ["55,0", "35,0", "50,0", "40,0"],
        "IC95_superior": ["65,0", "45,0", "60,0", "50,0"],
        "N_Pessoas": [400, 400, 450, 450],
    })
    st.caption("Exemplo ilustrativo (valores inventados; não entram em nenhum cálculo):")
    show_table(exemplo)


def reading_sentence(dif_inf, dif_sup) -> str:
    significativa = is_significant(dif_inf, dif_sup)
    if significativa is None:
        return (
            "Não dá para avaliar a diferença: faltam dados de um dos períodos "
            "para este grupo."
        )
    if significativa:
        return (
            "A diferença é estatisticamente significativa "
            "(o intervalo de confiança de 95% não inclui o zero)."
        )
    return (
        "Com estes dados não dá para afirmar que houve mudança: o intervalo de confiança de 95% "
        f"da diferença inclui o zero (de {format_pp(dif_inf)} a {format_pp(dif_sup)})."
    )


def show_highlight_metrics(tabela: pd.DataFrame, grupo: str, n_pessoas: dict) -> None:
    linha = tabela[tabela["Grupo"] == grupo]
    r = linha.iloc[0].to_dict() if not linha.empty else {}

    def valor(campo):
        return r.get(campo, np.nan)

    def ajuda_ic(ano):
        return (
            "Intervalo de confiança de 95%: de "
            f"{format_pct(valor(f'Inf_{ano}'))} a {format_pct(valor(f'Sup_{ano}'))}."
        )

    st.subheader(f"Grupo em destaque: {grupo}")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Participação em 2008-2009", format_pct(valor("Pct_2008")), help=ajuda_ic(2008))
    col2.metric("Participação em 2017-2018", format_pct(valor("Pct_2018")), help=ajuda_ic(2018))
    col3.metric(
        "Diferença (p.p.)",
        format_pp(valor("Dif_pp")),
        help=(
            "Ponto percentual (p.p.) é a subtração direta entre as duas participações: "
            "de 20% para 23%, são +3 p.p. O intervalo de confiança de 95% é a faixa de valores "
            "plausíveis para a diferença verdadeira; se ele inclui o zero, os dados não permitem "
            "afirmar que houve mudança."
        ),
    )
    col4.metric(
        "Variação relativa",
        format_relative(valor("Var_rel")),
        help=(
            "Mostra quanto a participação mudou em relação ao valor de 2008-2009: de 20% para 23%, "
            "são +15,0% (3 p.p. divididos por 20). Fica como \"—\" quando o valor de 2008-2009 é zero."
        ),
    )

    col5, col6, _, _ = st.columns(4)
    n_antes, n_depois = n_pessoas.get("2008-2009"), n_pessoas.get("2017-2018")
    col5.metric("Pessoas na amostra em 2008-2009", format_count(np.nan if n_antes is None else n_antes))
    col6.metric("Pessoas na amostra em 2017-2018", format_count(np.nan if n_depois is None else n_depois))

    st.info(reading_sentence(valor("Dif_inf"), valor("Dif_sup")))


def show_group_table(tabela: pd.DataFrame) -> None:
    def com_intervalo(pct, inferior, superior):
        if pd.isna(pct):
            return "—"
        return f"{format_pct(pct)} ({format_pct(inferior)} a {format_pct(superior)})"

    def significativa(linha):
        resposta = is_significant(linha["Dif_inf"], linha["Dif_sup"])
        return "—" if resposta is None else ("Sim" if resposta else "Não")

    def intervalo_diferenca(linha):
        if pd.isna(linha["Dif_inf"]) or pd.isna(linha["Dif_sup"]):
            return "—"
        return f"{format_pp(linha['Dif_inf'])} a {format_pp(linha['Dif_sup'])}"

    exibicao = pd.DataFrame({
        "Grupo": tabela["Grupo"],
        "2008-2009 (IC 95%)": [
            com_intervalo(r.Pct_2008, r.Inf_2008, r.Sup_2008) for r in tabela.itertuples()
        ],
        "2017-2018 (IC 95%)": [
            com_intervalo(r.Pct_2018, r.Inf_2018, r.Sup_2018) for r in tabela.itertuples()
        ],
        "Diferença (p.p.)": tabela["Dif_pp"].apply(format_pp),
        "IC 95% da diferença": tabela.apply(intervalo_diferenca, axis=1),
        "Variação relativa": tabela["Var_rel"].apply(format_relative),
        "Diferença significativa": tabela.apply(significativa, axis=1),
    })
    show_table(exibicao)


def show_notes(notas) -> None:
    with st.expander("Notas e limitações", expanded=True):
        if not notas:
            st.markdown(escape_markdown(GROUP2_BANNER))
            return
        for titulo, texto in notas:
            if titulo:
                st.markdown(f"**{escape_markdown(titulo)}**")
            if texto:
                st.markdown(escape_markdown(texto))


def show_raw_data(resultados: pd.DataFrame, diferencas: pd.DataFrame) -> None:
    with st.expander("Ver dados brutos"):
        st.caption("Aba Resultados (linhas usadas)")
        brutos = resultados.copy()
        for coluna in ("Participacao_Pct", "IC95_inferior", "IC95_superior"):
            brutos[coluna] = brutos[coluna].apply(lambda v: format_number_br(v, 2))
        brutos["N_Pessoas"] = brutos["N_Pessoas"].apply(format_count)
        show_table(brutos)

        st.caption("Diferenças usadas no app")
        if diferencas.empty:
            st.write("Sem diferenças: faltam dados de um dos períodos.")
        else:
            exibicao = pd.DataFrame({
                "Grupo": diferencas["Grupo"],
                "Diferença (p.p.)": diferencas["Dif_pp"].apply(format_pp),
                "IC 95% inferior (p.p.)": diferencas["Dif_inf"].apply(format_pp),
                "IC 95% superior (p.p.)": diferencas["Dif_sup"].apply(format_pp),
                "Variação relativa": diferencas["Var_rel"].apply(format_relative),
            })
            show_table(exibicao)


def main():
    st.title(TITLE)
    st.caption(SUBTITLE)
    st.warning(GROUP2_BANNER)

    with st.sidebar:
        st.header("Dados")
        uploaded_file = st.file_uploader("Enviar arquivo de resultados (.xlsx)", type=["xlsx"])

    if uploaded_file is None:
        show_upload_guide()
        st.stop()

    try:
        dados = load_results_file(uploaded_file.getvalue())
    except Exception as e:
        st.error("Não consegui ler o arquivo. Confira se ele abre normalmente no Excel e envie de novo.")
        with st.expander("Detalhes técnicos"):
            st.exception(e)
        st.stop()

    if dados["erro"]:
        st.error(dados["erro"])
        st.stop()

    resultados, diferencas = dados["resultados"], dados["diferencas"]
    resumo = dados["resumo"]
    show_import_summary(resumo)

    if resultados.empty:
        st.error(
            "Não encontramos nenhuma linha válida na aba Resultados. Confira se Periodo é "
            "2008-2009 ou 2017-2018, se Ano_Pesquisa é 2008 ou 2018, se Grupo é um dos nomes "
            f"aceitos ({', '.join(GROUP_ORDER)}) e se os valores são números (ex.: 25,9)."
        )
        st.stop()

    grupos = resumo["grupos"]
    indice_padrao = grupos.index("Ultraprocessados") if "Ultraprocessados" in grupos else 0
    with st.sidebar:
        st.header("Opções")
        grupo_destaque = st.selectbox("Grupo em destaque", options=grupos, index=indice_padrao)
        mostrar_erro = st.toggle("Mostrar margem de erro", value=True)

    tabela = build_group_table(resultados, diferencas)
    show_highlight_metrics(tabela, grupo_destaque, resumo["n_pessoas"])

    show_chart(build_participation_chart(resultados, mostrar_erro))
    show_chart(build_composition_chart(resultados))

    if tabela["Dif_pp"].notna().any():
        show_chart(build_difference_chart(tabela))
    else:
        st.info("A diferença entre os períodos precisa dos dois períodos na aba Resultados.")

    st.subheader("Resultados por grupo")
    show_group_table(tabela)

    show_notes(dados["notas"])
    show_raw_data(resultados, diferencas)


if __name__ == "__main__":
    main()
