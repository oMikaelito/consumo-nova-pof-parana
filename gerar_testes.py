"""
Gera planilhas de teste em testes/ para o app.py (resultados NOVA, Paraná, 15 a 29 anos).
Os dados do arquivo resultados_NOVA_PR_15a29.xlsx estão embutidos aqui (4 abas), então o
script não depende do arquivo original. Os dados de teste nunca entram no app.py.
"""

import copy
import os

from openpyxl import Workbook

OUTPUT_DIR = "testes"

SHEETS = {
    'Resultados': [
        ['Periodo', 'Ano_Pesquisa', 'Grupo', 'Participacao_Pct', 'IC95_inferior', 'IC95_superior', 'N_Pessoas'],
        ['2008-2009', 2008, 'In natura', 52.95, 49.83, 56.07, 426],
        ['2017-2018', 2018, 'In natura', 46.52, 41.85, 51.19, 444],
        ['2008-2009', 2008, 'Processados', 17.49, 15.1, 19.88, 426],
        ['2017-2018', 2018, 'Processados', 18.76, 17.15, 20.38, 444],
        ['2008-2009', 2008, 'Ultraprocessados', 25.87, 23.41, 28.33, 426],
        ['2017-2018', 2018, 'Ultraprocessados', 29.52, 24.57, 34.46, 444],
        ['2008-2009', 2008, 'Não classificado', 3.69, 2.86, 4.52, 426],
        ['2017-2018', 2018, 'Não classificado', 5.2, 4.22, 6.18, 444],
    ],
    'Diferencas': [
        ['Grupo', 'Participacao_2008_2009', 'Participacao_2017_2018', 'Diferenca_pp', 'IC95_inferior', 'IC95_superior', 'Variacao_relativa_pct', 'Diferenca_significativa'],
        ['In natura', 52.95, 46.52, -6.43, -12.05, -0.81, -12.1, 'Sim'],
        ['Processados', 17.49, 18.76, 1.27, -1.61, 4.16, 7.3, 'Não'],
        ['Ultraprocessados', 25.87, 29.52, 3.65, -1.88, 9.17, 14.1, 'Não'],
        ['Não classificado', 3.69, 5.2, 1.51, 0.22, 2.8, 40.9, 'Sim'],
    ],
    'Notas': [
        ['Resultado', "Classificação fechada: os três itens ambíguos foram decididos (ver 'Itens ambíguos'). Os números não incluem o grupo 2."],
        ['Recorte', 'Paraná, pessoas de 15 a 29 anos, POF 2008-2009 (426 pessoas) e POF 2017-2018 (444 pessoas), módulo de consumo alimentar individual.'],
        ['Medida', 'Participação (%) de cada grupo da classificação NOVA no total de calorias consumidas, sem o grupo 2, ponderada pelos pesos de expansão do IBGE. Margem de erro (IC 95%) calculada considerando estratos e setores da amostra.'],
        ['Classificação', "Cada alimento foi ligado a um grupo NOVA a partir da lista de subgrupos de Louzada et al. (2023), seguindo a regra padrão da NOVA para os pães. A classificação cobre os 262 alimentos que concentram cerca de 95% das calorias; os demais aparecem como 'Não classificado' (3,7% em 2008-2009 e 5,2% em 2017-2018)."],
        ['Itens ambíguos', 'SUCO (8500401): classificado como ultraprocessado, assumindo que o item genérico seja suco industrializado ou em pó; a suposição não pôde ser verificada. Se fosse in natura ou não classificado, os ultraprocessados seriam 23,8% e 28,0% (diferença de +4,1 p.p.). SUCO DE LARANJA (8500407): in natura, por ser registrado pelo nome da fruta (em 2017-2018 existe código separado para suco industrializado). BOLO SIMPLES (8004603): processado, igual ao bolo de trigo (8004601) de 2008-2009, seu equivalente.'],
        ['Limite da parte não classificada', 'Se toda a parte não classificada fosse ultraprocessada, a participação seria de 29.6% em 2008-2009 e 34.7% em 2017-2018, com diferença de +5.2 p.p. (IC 95%: -0.2 a +10.5).'],
        ['Grupo 2 fora dos cálculos', 'O grupo 2 (ingredientes culinários: óleos, gorduras, açúcar e sal) não foi incluído nos cálculos nem na comparação entre as pesquisas. Para estimá-lo de forma comparável no consumo individual é preciso desmontar as preparações em ingredientes usando receitas padronizadas (como fazem Louzada et al., 2023, com a TBCA), e essas receitas não estavam disponíveis. Além disso, segundo o artigo, açúcar e azeite adicionados foram coletados de modo diferente nas duas pesquisas: em 2017-2018 como itens separados para alguns alimentos, e em 2008-2009 por uma pergunta sobre o costume de adicionar. Sem o mesmo critério nos dois anos, a comparação do grupo 2 não seria válida.'],
        ['Consequência', 'As participações foram calculadas sobre o total de calorias SEM o grupo 2. Por isso não são diretamente comparáveis aos percentuais publicados que incluem o grupo 2 no total (por exemplo, 19,7% de ultraprocessados em 2017-2018 no Brasil). Se o grupo 2 fosse incluído (cerca de 15,8% das calorias no Brasil em 2017-2018), os ultraprocessados seriam de 4 a 5 pontos menores; a diferença entre os períodos mudaria menos, se o peso do grupo 2 for parecido nos dois períodos (não verificável para 2008-2009).'],
        ['Referência para o grupo 2', 'Na aquisição domiciliar (IBGE, POF 2017-2018, Tabela 11, Brasil), o grupo 2 representa 24,2% das calorias adquiridas em 2008-2009 e 22,3% em 2017-2018.'],
        ['Limitações', 'Amostra pequena para o recorte (o Paraná não é domínio de divulgação da pesquisa); intervalos de confiança largos. Os métodos de coleta diferem entre as edições (registro alimentar em 2008-2009 e recordatório em 2017-2018). Cada alimento recebe um único grupo, sem desmontar as preparações. Os códigos de alimentos mudaram entre as pesquisas.'],
    ],
    'Kcal_por_dia': [
        ['Grupo', 'Kcal_dia_2008_2009', 'IC95_inf_2008_2009', 'IC95_sup_2008_2009', 'Kcal_dia_2017_2018', 'IC95_inf_2017_2018', 'IC95_sup_2017_2018', 'Diferenca_kcal', 'IC95_inf_dif', 'IC95_sup_dif'],
        ['In natura', 1038, 953, 1122, 844, 766, 921, -194, -309, -80],
        ['Processados', 343, 293, 392, 340, 298, 383, -2, -68, 63],
        ['Ultraprocessados', 507, 451, 563, 535, 414, 657, 28, -106, 162],
        ['Não classificado', 72, 57, 88, 94, 77, 111, 22, -1, 45],
        ['Total (inclui o grupo 2, parcial)', 1968, 1865, 2071, 1962, 1794, 2131, -6, -203, 192],
        [None, None, None, None, None, None, None, None, None, None],
        ['Nota: consumo médio diário de energia por pessoa (kcal/dia), Paraná, 15 a 29 anos. O grupo 2 não é comparável entre as pesquisas e não está nesta tabela; o total inclui as calorias do grupo 2 registradas em cada pesquisa, por isso a soma dos grupos é menor que o total.', None, None, None, None, None, None, None, None, None],
    ],
}


ARQUIVOS_ANTIGOS = [
    "ok_utf8.csv", "ok_latin1.csv", "so_grupos.csv", "soma_errada.csv",
    "classificacao_variacoes.csv", "nivel_invalido.csv", "ano_errado.csv", "so_um_ano.csv",
    "percentual_invalido.csv", "coluna_faltando.csv", "com_classificacao.csv", "grande.csv",
    "coluna_errada.csv", "gasto_invalido.csv", "espaco_e_vazio.csv", "classificacao_vazia.csv",
    "ano_extra.csv", "duas_abas.xlsx", "vazio.csv", "corrompido.xlsx", "produtos_um_ano.csv",
    "nomes_diferentes.csv", "duplicadas.csv",
]


def copia() -> dict:
    return copy.deepcopy(SHEETS)


def indice(sheets: dict, aba: str, coluna: str) -> int:
    return sheets[aba][0].index(coluna)


def linha_de(sheets: dict, aba: str, **filtros) -> list:
    """Devolve a linha (lista, editável) da aba que bate com todos os filtros."""
    for linha in sheets[aba][1:]:
        if all(linha[indice(sheets, aba, c)] == v for c, v in filtros.items()):
            return linha
    raise ValueError(f"Linha não encontrada em {aba}: {filtros}")


def salvar(sheets: dict, nome: str) -> None:
    wb = Workbook()
    wb.remove(wb.active)
    for titulo, linhas in sheets.items():
        ws = wb.create_sheet(titulo)
        for linha in linhas:
            ws.append(linha)
        for coluna in ws.columns:
            maior = max((len(str(c.value)) for c in coluna if c.value is not None), default=8)
            ws.column_dimensions[coluna[0].column_letter].width = min(maior + 2, 80)
    wb.save(os.path.join(OUTPUT_DIR, nome))


def gerar_ok():
    salvar(copia(), "ok.xlsx")


def gerar_sem_diferencas():
    s = copia()
    del s["Diferencas"]
    salvar(s, "sem_diferencas.xlsx")


def gerar_sem_notas():
    s = copia()
    del s["Notas"]
    salvar(s, "sem_notas.xlsx")


def gerar_soma_errada():
    s = copia()
    linha = linha_de(s, "Resultados", Periodo="2017-2018", Grupo="Ultraprocessados")
    linha[indice(s, "Resultados", "Participacao_Pct")] = 35.0
    linha[indice(s, "Resultados", "IC95_inferior")] = 30.1  # mantém o IC coerente com o novo valor
    linha[indice(s, "Resultados", "IC95_superior")] = 39.9
    del s["Diferencas"]  # isola o aviso de soma (a aba Diferencas deixaria de bater)
    salvar(s, "soma_errada.xlsx")


def gerar_grupo_invalido():
    s = copia()
    ig = indice(s, "Resultados", "Grupo")
    linha_de(s, "Resultados", Periodo="2008-2009", Grupo="Ultraprocessados")[ig] = "ultra processado "
    s["Resultados"].append(["2008-2009", 2008, "Grupo X", 5.0, 4.0, 6.0, 426])
    s["Resultados"].append(["2017-2018", 2018, "Grupo X", 4.0, 3.0, 5.0, 444])
    salvar(s, "grupo_invalido.xlsx")


def gerar_ic_invertido():
    s = copia()
    ii = indice(s, "Resultados", "IC95_inferior")
    isup = indice(s, "Resultados", "IC95_superior")
    linha = linha_de(s, "Resultados", Periodo="2017-2018", Grupo="Processados")
    linha[ii], linha[isup] = linha[isup], linha[ii]  # troca os limites; o erro padrão não muda
    salvar(s, "ic_invertido.xlsx")


def gerar_so_um_periodo():
    s = copia()
    s["Resultados"] = [s["Resultados"][0]] + [
        l for l in s["Resultados"][1:] if l[indice(s, "Resultados", "Periodo")] == "2017-2018"
    ]
    salvar(s, "so_um_periodo.xlsx")


def gerar_coluna_faltando():
    s = copia()
    posicao = indice(s, "Resultados", "IC95_superior")
    s["Resultados"] = [[v for i, v in enumerate(l) if i != posicao] for l in s["Resultados"]]
    salvar(s, "coluna_faltando.xlsx")


def gerar_ano_invalido():
    s = copia()
    ia = indice(s, "Resultados", "Ano_Pesquisa")
    for linha in s["Resultados"][1:]:
        if linha[ia] == 2008:
            linha[ia] = "2008-09"
    salvar(s, "ano_invalido.xlsx")


def gerar_valores_com_virgula():
    s = copia()
    colunas = [indice(s, "Resultados", c) for c in ("Participacao_Pct", "IC95_inferior", "IC95_superior")]
    for linha in s["Resultados"][1:]:
        for i in colunas:
            linha[i] = f"{linha[i]:.2f}".replace(".", ",")  # texto, como "52,95"
    salvar(s, "valores_com_virgula.xlsx")


def gerar_diferencas_divergentes():
    s = copia()
    linha_de(s, "Diferencas", Grupo="Ultraprocessados")[indice(s, "Diferencas", "Diferenca_pp")] = 5.0
    salvar(s, "diferencas_divergentes.xlsx")


def gerar_arquivo_corrompido():
    with open(os.path.join(OUTPUT_DIR, "arquivo_corrompido.xlsx"), "w", encoding="utf-8") as f:
        f.write("Isto é um arquivo de texto comum renomeado para .xlsx.")


ESPERADO = [
    ('ok.xlsx', 'Carrega normal, sem avisos. Ultraprocessados: 25,9% e 29,5%, +3,6 p.p., +14,1%; 426 e 444 pessoas. Frase: com estes dados não dá para afirmar que houve mudança (IC de -1,9 a +9,2 p.p.). Notas completas e 3 gráficos.'),
    ('sem_diferencas.xlsx', "Carrega normal, sem avisos, com os mesmos números do ok.xlsx: o app calcula a diferença e o IC (resumo: 'calculadas pelo app')."),
    ('sem_notas.xlsx', "Carrega normal, sem avisos. 'Notas e limitações' mostra só o texto do grupo 2."),
    ('soma_errada.xlsx', 'Carrega com 1 aviso: em 2017-2018 a soma dos grupos é 105,5%. Ultraprocessados vira 35,0% e a diferença +9,1 p.p., significativa (sem aba Diferencas; o app calcula).'),
    ('grupo_invalido.xlsx', "Carrega com 1 aviso: 'Grupo X' (2 linhas) ignorado. 'ultra processado ' (minúsculas, com espaço) é normalizado para Ultraprocessados; números iguais aos do ok.xlsx."),
    ('ic_invertido.xlsx', 'Carrega com 1 aviso: o IC de Processados em 2017-2018 (20,4% a 17,1%) não contém o valor 18,8%. Nada é ignorado; o resto igual ao ok.xlsx.'),
    ('so_um_periodo.xlsx', "Carrega com 1 aviso: falta o período 2008-2009. Participação 2008-2009, diferença e variação ficam '—'; o gráfico de diferença vira uma mensagem; a aba Diferencas é ignorada."),
    ('coluna_faltando.xlsx', "Erro e parada: 'Faltam as colunas: IC95_superior', com as colunas esperadas e as encontradas."),
    ('ano_invalido.xlsx', "Carrega com 2 avisos: 4 linhas com Ano_Pesquisa '2008-09' ignoradas e falta do período 2008-2009 (mesmos efeitos do so_um_periodo.xlsx)."),
    ('valores_com_virgula.xlsx', "Carrega normal, sem avisos, igual ao ok.xlsx: textos como '52,95' são lidos como número."),
    ('diferencas_divergentes.xlsx', 'Carrega com 1 aviso: na aba Diferencas, a diferença de Ultraprocessados (5,00) diverge do recalculado (3,65). São mostrados os números da aba: +5,0 p.p.'),
    ('arquivo_corrompido.xlsx', "Erro e parada: 'Não consegui ler o arquivo...', com o expander 'Detalhes técnicos' mostrando o erro."),
]


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for nome in ARQUIVOS_ANTIGOS:
        caminho = os.path.join(OUTPUT_DIR, nome)
        if os.path.exists(caminho):
            os.remove(caminho)
            print(f"Removido arquivo antigo: {nome}")

    gerar_ok()
    gerar_sem_diferencas()
    gerar_sem_notas()
    gerar_soma_errada()
    gerar_grupo_invalido()
    gerar_ic_invertido()
    gerar_so_um_periodo()
    gerar_coluna_faltando()
    gerar_ano_invalido()
    gerar_valores_com_virgula()
    gerar_diferencas_divergentes()
    gerar_arquivo_corrompido()

    largura = max(len(nome) for nome, _ in ESPERADO)
    print(f"\nArquivos gerados em '{OUTPUT_DIR}/':\n")
    print(f"{'Arquivo'.ljust(largura)}  Comportamento esperado")
    print(f"{'-' * largura}  {'-' * 60}")
    for nome, comportamento in ESPERADO:
        print(f"{nome.ljust(largura)}  {comportamento}")


if __name__ == "__main__":
    main()
