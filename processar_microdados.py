#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
processar_microdados.py
=======================

Calcula a participação (%) de cada grupo da classificação NOVA nas calorias
consumidas por pessoas de 15 a 29 anos do Paraná, na POF 2008-2009 e na POF
2017-2018 (módulo de consumo alimentar individual), e grava o arquivo de
resultados que o aplicativo (Streamlit) lê.

O QUE O SCRIPT FAZ, NA ORDEM
----------------------------
1. Abre os zips do IBGE e lê os dicionários de variáveis para descobrir a
   posição de cada coluna nos arquivos de texto de largura fixa.
2. Lê os registros de consumo e o cadastro de moradores, mantendo só o Paraná
   (UF 41), e liga cada pessoa à sua idade.
3. Calcula a energia (kcal) de cada item consumido:
     - 2017-2018: o microdado já traz ENERGIA_KCAL;
     - 2008-2009: kcal = quantidade em gramas x kcal por 100 g / 100, usando as
       Tabelas de Composição Nutricional do IBGE (chave: código do alimento +
       código da preparação).
4. Liga cada alimento ao grupo NOVA, usando a planilha de classificação
   (coluna Grupo_NOVA_final). Alimentos fora da planilha ficam como
   "Não classificado".
5. Mantém só pessoas de 15 a 29 anos e calcula, por período:
     - participação (%) de cada grupo no total de calorias, SEM o grupo 2
       (ingredientes culinários), ponderada pelo PESO_FINAL;
     - consumo médio diário (kcal por pessoa por dia) de cada grupo;
     - intervalos de confiança de 95% por linearização de Taylor, com os
       estratos (ESTRATO_POF) e os setores (UPA) da amostra;
     - a diferença entre os períodos e o intervalo da diferença.
6. Grava o arquivo de resultados (abas Resultados, Diferencas, Notas e
   Kcal_por_dia).

COMO USAR
---------
    python processar_microdados.py \
        --zip-2017 POF_2017-2018.zip \
        --zip-2008 POF_2008-2009.zip \
        --zip-composicao Tabelas.zip \
        --classificacao classificacao_NOVA_final.xlsx \
        --saida resultados_NOVA_PR_15a29.xlsx

Requisitos: Python 3.9+, pandas, numpy, openpyxl, xlrd (para os .xls do IBGE).
    pip install pandas numpy openpyxl xlrd

Os zips são os baixados do site do IBGE (microdados e documentação). O script
extrai temporariamente só os arquivos de que precisa e apaga tudo no final.
"""

import argparse
import io
import os
import re
import shutil
import sys
import tempfile
import zipfile

import numpy as np
import pandas as pd
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

# ----------------------------------------------------------------------------
# PARÂMETROS DO ESTUDO
# ----------------------------------------------------------------------------
UF_PARANA = "41"
IDADE_MIN, IDADE_MAX = 15, 29
GRUPO_2 = "Ingredientes culinários"            # fora da comparação (ver Notas)
GRUPOS = ["In natura", "Processados", "Ultraprocessados", "Não classificado"]
Z95 = 1.96


# ----------------------------------------------------------------------------
# LEITURA DOS ARQUIVOS DO IBGE
# ----------------------------------------------------------------------------
def achar_membro(zf, padrao):
    """Acha, dentro do zip, o arquivo cujo NOME (sem pasta) casa com o padrão."""
    achados = [i for i in zf.infolist()
               if not i.is_dir() and re.search(padrao, os.path.basename(i.filename), re.I)]
    if not achados:
        sys.exit(f"Arquivo não encontrado no zip ({padrao}).")
    return sorted(achados, key=lambda i: len(i.filename))[0]


def posicoes(zf, aba, nomes):
    """Lê o dicionário de variáveis (xls) e devolve {variavel: (inicio, fim)} (base 0)."""
    info = achar_membro(zf, r"^Dicion.*\.xls$")
    df = pd.read_excel(io.BytesIO(zf.read(info)), sheet_name=aba, header=None)
    col = next(c for c in range(df.shape[1])
               if df.iloc[:15, c].astype(str).str.contains("Código da variável", na=False).any())
    h = df.index[df.iloc[:, col].astype(str).str.contains("Código da variável", na=False)][0]
    d = df.iloc[h + 1:, [0, 1, col]].dropna(subset=[col])
    d.columns = ["ini", "tam", "var"]
    pos = {str(r.var).strip(): (int(r.ini) - 1, int(r.ini) - 1 + int(r.tam)) for r in d.itertuples()}
    faltam = [n for n in nomes if n not in pos]
    if faltam:
        sys.exit(f"Variáveis ausentes no dicionário ({aba}): {faltam}")
    return {n: pos[n] for n in nomes}


def ler_largura_fixa(caminho, pos, coluna_uf):
    """Lê o txt de largura fixa em blocos e mantém só o Paraná."""
    nomes = list(pos)
    partes = []
    for bloco in pd.read_fwf(caminho, colspecs=[pos[n] for n in nomes], names=nomes,
                             header=None, dtype=str, encoding="latin-1", chunksize=400_000):
        bloco = bloco[bloco[coluna_uf].str.strip() == UF_PARANA]
        if len(bloco):
            partes.append(bloco)
    return pd.concat(partes, ignore_index=True)


def extrair(zf, info, pasta):
    destino = os.path.join(pasta, os.path.basename(info.filename))
    with zf.open(info) as src, open(destino, "wb") as dst:
        shutil.copyfileobj(src, dst, length=1 << 24)
    return destino


# ----------------------------------------------------------------------------
# CARGA DE CADA PESQUISA
# ----------------------------------------------------------------------------
def carregar_2017(zip_path, pasta):
    """POF 2017-2018: registros de consumo do Paraná, com idade e energia."""
    zf = zipfile.ZipFile(zip_path)
    pos_c = posicoes(zf, "Consumo Alimentar",
                     ["UF", "ESTRATO_POF", "COD_UPA", "NUM_DOM", "NUM_UC", "COD_INFORMANTE",
                      "QUADRO", "V9001", "ENERGIA_KCAL", "PESO_FINAL"])
    pos_m = posicoes(zf, "Morador", ["UF", "COD_UPA", "NUM_DOM", "NUM_UC", "COD_INFORMANTE", "V0403"])
    cons = ler_largura_fixa(extrair(zf, achar_membro(zf, r"^CONSUMO_ALIMENTAR\.txt$"), pasta), pos_c, "UF")
    mor = ler_largura_fixa(extrair(zf, achar_membro(zf, r"^MORADOR\.txt$"), pasta), pos_m, "UF")

    chave = ["COD_UPA", "NUM_DOM", "NUM_UC", "COD_INFORMANTE"]
    for d in (cons, mor):
        for k in chave:
            d[k] = d[k].str.strip().astype(int)
    mor["idade"] = mor["V0403"].astype(int)
    cons = cons.merge(mor[chave + ["idade"]], on=chave, how="left")

    out = pd.DataFrame({
        "cod": cons["V9001"].str.strip().astype(int),
        "kcal": cons["ENERGIA_KCAL"].astype(float),
        "w": cons["PESO_FINAL"].astype(float),
        "idade": cons["idade"],
        "psu": cons["COD_UPA"].astype(str),                     # setor (UPA)
        "strat": cons["ESTRATO_POF"].str.strip(),
        "pessoa": cons[chave].astype(str).agg("-".join, axis=1),
    })
    out["dia"] = out["pessoa"] + "-" + cons["QUADRO"].astype(str)    # pessoa-dia
    return out, int(mor["idade"].ge(10).sum()), int(cons.drop_duplicates(chave).shape[0])


def carregar_2008(zip_path, pasta, composicao):
    """POF 2008-2009: registros de consumo do Paraná, com idade e energia calculada."""
    zf = zipfile.ZipFile(zip_path)
    pos_c = posicoes(zf, "Consumo Alimentar",
                     ["COD_UF", "NUM_SEQ", "NUM_DV", "NUM_DOM", "NUM_UC", "COD_INFORMANTE",
                      "ESTRATO_POF", "PESO_FINAL", "NUM_QUADRO", "V9001", "V9016", "QTD_FINAL"])
    pos_m = posicoes(zf, "Morador",
                     ["COD_UF", "NUM_SEQ", "NUM_DV", "NUM_DOM", "NUM_UC", "COD_INFORMANTE", "IDADE_ANOS"])
    cons = ler_largura_fixa(extrair(zf, achar_membro(zf, r"^T_CONSUMO_S\.txt$"), pasta), pos_c, "COD_UF")
    mor = ler_largura_fixa(extrair(zf, achar_membro(zf, r"^T_MORADOR_S\.txt$"), pasta), pos_m, "COD_UF")

    chave = ["NUM_SEQ", "NUM_DV", "NUM_DOM", "NUM_UC", "COD_INFORMANTE"]
    for d in (cons, mor):
        for k in chave:
            d[k] = d[k].str.strip().astype(int)      # remove zeros à esquerda (as chaves diferem entre os arquivos)
    mor["idade"] = mor["IDADE_ANOS"].astype(int)
    cons = cons.merge(mor[chave + ["idade"]], on=chave, how="left")

    cons["cod"] = cons["V9001"].str.strip().astype(int)
    cons["prep"] = pd.to_numeric(cons["V9016"].str.strip().replace("", np.nan), errors="coerce")
    cons = cons.merge(composicao, on=["cod", "prep"], how="left")
    sem_kcal = int(cons["kcal100"].isna().sum())
    cons["kcal"] = (cons["QTD_FINAL"].astype(float) * cons["kcal100"] / 100).fillna(0.0)

    out = pd.DataFrame({
        "cod": cons["cod"], "kcal": cons["kcal"], "w": cons["PESO_FINAL"].astype(float),
        "idade": cons["idade"],
        "psu": cons["NUM_SEQ"].astype(str) + "-" + cons["NUM_DV"].astype(str),   # setor (UPA)
        "strat": cons["ESTRATO_POF"].str.strip(),
        "pessoa": cons[chave].astype(str).agg("-".join, axis=1),
    })
    out["dia"] = out["pessoa"] + "-" + cons["NUM_QUADRO"].astype(str)
    return out, sem_kcal, len(cons), int(cons.drop_duplicates(chave).shape[0])


def carregar_composicao(zip_path):
    """Tabela de composição do IBGE (2008-2009): kcal por 100 g, por alimento e preparação."""
    zf = zipfile.ZipFile(zip_path)
    info = achar_membro(zf, r"^tabelacompleta\.xls$")
    bruto = pd.read_excel(io.BytesIO(zf.read(info)), sheet_name=0, header=None, skiprows=4)
    t = bruto.iloc[:, [0, 2, 6]].copy()               # alimento, preparação, energia (kcal/100 g)
    t.columns = ["cod", "prep", "kcal100"]
    t["cod"] = pd.to_numeric(t["cod"], errors="coerce")
    t = t.dropna(subset=["cod"])                      # descarta linhas de rodapé
    t["cod"] = t["cod"].astype(int)
    t["prep"] = pd.to_numeric(t["prep"], errors="coerce")
    t["kcal100"] = pd.to_numeric(t["kcal100"], errors="coerce")
    return t.drop_duplicates(["cod", "prep"])


def carregar_classificacao(caminho):
    c = pd.read_excel(caminho, sheet_name="Rascunho")
    c["cod"] = c["Codigo"].astype(int)
    return c.set_index("cod")["Grupo_NOVA_final"]


# ----------------------------------------------------------------------------
# ESTIMAÇÃO
# ----------------------------------------------------------------------------
def _variancia(z, d):
    """Variância de um total por linearização: soma por setor dentro de cada estrato."""
    tot = pd.DataFrame({"z": z, "psu": d["psu"].values, "strat": d["strat"].values}) \
        .groupby(["strat", "psu"])["z"].sum().reset_index()
    var = 0.0
    for _, g in tot.groupby("strat"):
        n = len(g)
        if n > 1:                                     # estrato com 1 setor não contribui
            var += n / (n - 1) * ((g["z"] - g["z"].mean()) ** 2).sum()
    return var


def participacao(d, grupo):
    """% do grupo no total de calorias (sem o grupo 2), pessoas de 15 a 29 anos. Devolve (%, erro-padrão)."""
    dom = d["idade"].between(IDADE_MIN, IDADE_MAX)
    no_total = d["grp"] != GRUPO_2
    den = np.where(dom & no_total, d["w"] * d["kcal"], 0.0)
    num = np.where(dom & no_total & (d["grp"] == grupo), d["w"] * d["kcal"], 0.0)
    r = num.sum() / den.sum()
    return r * 100, np.sqrt(_variancia(num - r * den, d)) / den.sum() * 100


def kcal_dia(d, grupo=None):
    """Consumo médio diário (kcal/pessoa/dia). grupo=None => total. Devolve (média, erro-padrão)."""
    dom = d[d["idade"].between(IDADE_MIN, IDADE_MAX)]
    dias = dom.drop_duplicates("dia")[["dia", "w", "psu", "strat"]].set_index("dia")
    sel = dom if grupo is None else dom[dom["grp"] == grupo]
    soma = (sel["w"] * sel["kcal"]).groupby(sel["dia"]).sum()
    dias["num"] = soma.reindex(dias.index).fillna(0.0)
    r = dias["num"].sum() / dias["w"].sum()
    z = (dias["num"] - r * dias["w"]).values
    return r, np.sqrt(_variancia(z, dias)) / dias["w"].sum()


# ----------------------------------------------------------------------------
# SAÍDA
# ----------------------------------------------------------------------------
def cabecalho(ws):
    for c in ws[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="404040")
        c.alignment = Alignment(horizontal="center", wrap_text=True)
    ws.freeze_panes = "A2"


def gravar(saida, d08, d18, n08, n18, notas_de):
    wb = Workbook()
    ws = wb.active
    ws.title = "Resultados"
    ws.append(["Periodo", "Ano_Pesquisa", "Grupo", "Participacao_Pct", "IC95_inferior", "IC95_superior", "N_Pessoas"])
    wd = wb.create_sheet("Diferencas")
    wd.append(["Grupo", "Participacao_2008_2009", "Participacao_2017_2018", "Diferenca_pp",
               "IC95_inferior", "IC95_superior", "Variacao_relativa_pct", "Diferenca_significativa"])
    resumo = {}
    for g in GRUPOS:
        a, sa = participacao(d08, g)
        b, sb = participacao(d18, g)
        ws.append(["2008-2009", 2008, g, round(a, 2), round(a - Z95 * sa, 2), round(a + Z95 * sa, 2), n08])
        ws.append(["2017-2018", 2018, g, round(b, 2), round(b - Z95 * sb, 2), round(b + Z95 * sb, 2), n18])
        se, dif = (sa ** 2 + sb ** 2) ** 0.5, b - a
        sig = "Sim" if (dif - Z95 * se > 0 or dif + Z95 * se < 0) else "Não"
        wd.append([g, round(a, 2), round(b, 2), round(dif, 2), round(dif - Z95 * se, 2),
                   round(dif + Z95 * se, 2), round(dif / a * 100, 1), sig])
        resumo[g] = (a, b, dif, dif - Z95 * se, dif + Z95 * se)

    # notas: copiadas de um arquivo anterior, se existir
    wn = wb.create_sheet("Notas")
    if notas_de and os.path.exists(notas_de):
        antigo = load_workbook(notas_de, read_only=True)
        if "Notas" in antigo.sheetnames:
            for linha in antigo["Notas"].iter_rows(values_only=True):
                wn.append(list(linha))
    if wn.max_row <= 1 and wn["A1"].value is None:
        wn.append(["Nota", "Gerado por processar_microdados.py. Acrescente aqui as notas de método e as limitações."])
    wn.column_dimensions["A"].width = 30
    wn.column_dimensions["B"].width = 140
    for row in wn.iter_rows():
        row[0].font = Font(bold=True)
        row[0].alignment = Alignment(vertical="top", wrap_text=True)
        if len(row) > 1:
            row[1].alignment = Alignment(wrap_text=True, vertical="top")

    wk = wb.create_sheet("Kcal_por_dia")
    wk.append(["Grupo", "Kcal_dia_2008_2009", "IC95_inf_2008_2009", "IC95_sup_2008_2009",
               "Kcal_dia_2017_2018", "IC95_inf_2017_2018", "IC95_sup_2017_2018",
               "Diferenca_kcal", "IC95_inf_dif", "IC95_sup_dif"])
    for g, rot in [(x, x) for x in GRUPOS] + [(None, "Total (inclui o grupo 2, parcial)")]:
        a, sa = kcal_dia(d08, g)
        b, sb = kcal_dia(d18, g)
        se, dif = (sa ** 2 + sb ** 2) ** 0.5, b - a
        wk.append([rot, round(a), round(a - Z95 * sa), round(a + Z95 * sa), round(b), round(b - Z95 * sb),
                   round(b + Z95 * sb), round(dif), round(dif - Z95 * se), round(dif + Z95 * se)])
    wk.append([])
    wk.append(["Nota: consumo médio diário de energia por pessoa (kcal/dia), Paraná, 15 a 29 anos. O grupo 2 não é "
               "comparável entre as pesquisas e não está nesta tabela; o total inclui as calorias do grupo 2 "
               "registradas em cada pesquisa, por isso a soma dos grupos é menor que o total."])

    for planilha, larguras in ((ws, [14, 13, 20, 18, 14, 14, 11]), (wd, [20, 22, 22, 14, 14, 14, 20, 22]),
                               (wk, [34, 18, 18, 18, 18, 18, 18, 16, 14, 14])):
        for i, w in enumerate(larguras, 1):
            planilha.column_dimensions[get_column_letter(i)].width = w
        cabecalho(planilha)
    wb.save(saida)
    return resumo


# ----------------------------------------------------------------------------
# PROGRAMA PRINCIPAL
# ----------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--zip-2017", required=True, help="POF_2017-2018.zip (microdados e documentação)")
    ap.add_argument("--zip-2008", required=True, help="POF_2008-2009.zip (microdados e documentação)")
    ap.add_argument("--zip-composicao", required=True, help="zip com a tabela de composição nutricional (tabelacompleta.xls)")
    ap.add_argument("--classificacao", required=True, help="planilha com a coluna Grupo_NOVA_final (aba Rascunho)")
    ap.add_argument("--saida", default="resultados_NOVA_PR_15a29.xlsx")
    ap.add_argument("--notas-de", default=None, help="arquivo de resultados anterior de onde copiar a aba Notas")
    args = ap.parse_args()

    pasta = tempfile.mkdtemp(prefix="pof_")
    try:
        print("1/5 Lendo a tabela de composição nutricional ...")
        comp = carregar_composicao(args.zip_composicao)
        print("2/5 Lendo a POF 2017-2018 (pode levar alguns minutos) ...")
        d18, n18_mais10, n18_pess = carregar_2017(args.zip_2017, pasta)
        print("3/5 Lendo a POF 2008-2009 ...")
        d08, sem_kcal, n08_reg, n08_pess = carregar_2008(args.zip_2008, pasta, comp)
        print("4/5 Aplicando a classificação NOVA ...")
        mapa = carregar_classificacao(args.classificacao)
        for d in (d08, d18):
            d["grp"] = d["cod"].map(mapa).fillna("Não classificado")
        n08 = int(d08[d08["idade"].between(IDADE_MIN, IDADE_MAX)]["pessoa"].nunique())
        n18 = int(d18[d18["idade"].between(IDADE_MIN, IDADE_MAX)]["pessoa"].nunique())
        print("5/5 Estimando e gravando ...")
        resumo = gravar(args.saida, d08, d18, n08, n18, args.notas_de)
    finally:
        shutil.rmtree(pasta, ignore_errors=True)

    print("\n=== CONFERÊNCIAS ===")
    print(f"Pessoas de {IDADE_MIN} a {IDADE_MAX} anos no Paraná: {n08} (2008-2009) e {n18} (2017-2018)")
    print(f"Pessoas com 10 anos ou mais com consumo no Paraná em 2017-2018: {n18_pess} (o IBGE publica 1.988)")
    print(f"Registros de 2008-2009 sem energia (sem par na tabela de composição): {sem_kcal} de {n08_reg}")
    print("\n=== PARTICIPAÇÃO (%) NO TOTAL DE CALORIAS, SEM O GRUPO 2 ===")
    for g, (a, b, dif, lo, hi) in resumo.items():
        print(f"{g:18s} 2008-2009 {a:5.1f}% | 2017-2018 {b:5.1f}% | diferença {dif:+.1f} p.p. (IC 95%: {lo:+.1f} a {hi:+.1f})")
    print(f"\nArquivo gravado em: {args.saida}")


if __name__ == "__main__":
    main()
