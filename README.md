# Consumo de calorias por grau de processamento: jovens de 15 a 29 anos do Paraná

Comparação entre a **POF 2008-2009** e a **POF 2017-2018** (IBGE) da participação de cada grupo da classificação NOVA nas calorias consumidas por pessoas de 15 a 29 anos do Paraná.

**Aplicativo online:** https://estudopoftcc.streamlit.app/

Este repositório faz parte de um Trabalho de Conclusão de Curso sobre o impacto dos estímulos sensoriais (cor, marketing, paladar, cheiro) na decisão de consumo de alimentos ultraprocessados. Os dados aqui descritos servem de contexto para esse trabalho.

## Sumário

1. [O que o aplicativo faz (e o que não faz)](#o-que-o-aplicativo-faz-e-o-que-não-faz)
2. [Como usar o aplicativo](#como-usar-o-aplicativo)
3. [O que aparece na tela](#o-que-aparece-na-tela)
4. [Como ler os resultados](#como-ler-os-resultados)
5. [Arquivo de resultados aceito pelo aplicativo](#arquivo-de-resultados-aceito-pelo-aplicativo)
6. [Validações e avisos](#validações-e-avisos)
7. [Rodar o aplicativo no seu computador](#rodar-o-aplicativo-no-seu-computador)
8. [Como os resultados foram gerados](#como-os-resultados-foram-gerados)
9. [Metodologia em resumo](#metodologia-em-resumo)
10. [Ressalvas importantes](#ressalvas-importantes)
11. [Estrutura do repositório](#estrutura-do-repositório)
12. [Testes do aplicativo](#testes-do-aplicativo)
13. [Fontes, autoria e licença](#fontes-autoria-e-licença)

<!-- Dica: salve prints do aplicativo em uma pasta docs/ e mostre aqui, por exemplo: ![Tela principal](docs/tela_principal.png) -->

## O que o aplicativo faz (e o que não faz)

O aplicativo é uma ferramenta de **visualização**. Ele lê uma planilha de resultados já calculados e mostra, em tabelas e gráficos:

- a participação (%) de cada grupo da classificação NOVA no total de calorias, em cada pesquisa, com a margem de erro (intervalo de confiança de 95%);
- a diferença entre as duas pesquisas, em pontos percentuais (p.p.), com o intervalo de confiança e a indicação de se ela é estatisticamente significativa;
- as notas de método e as limitações do estudo, lidas da própria planilha.

Antes de mostrar qualquer resultado, ele confere a planilha e avisa, em português simples, o que está errado ou faltando.

**O aplicativo não faz:**

- **Não processa microdados.** Quem faz isso é o script `processar_microdados.py` (veja [Como os resultados foram gerados](#como-os-resultados-foram-gerados)).
- **Não classifica alimentos.** A classificação de cada alimento em um grupo NOVA é uma decisão da autora e está em `classificacao_NOVA_final.xlsx`.
- **Não compara alimentos específicos** nem diz que um alimento é mais ou menos processado que outro.
- **Não usa dados fictícios em nenhum cálculo.** Sem arquivo enviado, ele mostra só um guia de uso, com uma tabela de exemplo marcada como ilustrativa.
- **Não grava o arquivo enviado em disco.** Ele é lido na memória só para montar a tela.

## Como usar o aplicativo

1. Abra https://estudopoftcc.streamlit.app/.
2. Na barra lateral, em **Dados**, clique em **Enviar arquivo de resultados (.xlsx)** e escolha o arquivo `resultados_NOVA_PR_15a29.xlsx`, que está neste repositório.
3. Confira o **Resumo da importação** e os avisos, se houver.
4. Em **Opções**, escolha o **Grupo em destaque** (por padrão, Ultraprocessados) e se quer mostrar a **margem de erro** nos gráficos.
5. Role a página para ver os gráficos, a tabela por grupo e as notas.

O aplicativo não procura o arquivo sozinho: é preciso enviá-lo a cada sessão.

## O que aparece na tela

De cima para baixo:

| Elemento | O que mostra |
|---|---|
| **Título e subtítulo** | Participação (%) de cada grupo da NOVA no total de calorias consumidas, **sem o grupo 2**, com a fonte (IBGE, POF 2008-2009 e 2017-2018) |
| **Faixa de aviso do grupo 2** | Sempre visível. Diz que o grupo 2 (ingredientes culinários) foi deixado de fora por não ser comparável entre as pesquisas, e que por isso os percentuais não são diretamente comparáveis aos de estudos que o incluem |
| **Resumo da importação** | Linhas lidas, usadas e ignoradas (com o motivo), períodos e grupos encontrados, número de pessoas por período, de onde vieram as diferenças e se a aba Notas foi encontrada. Os avisos de validação aparecem aqui |
| **Grupo em destaque** | Participação em cada período (com o intervalo de confiança ao passar o mouse), diferença em p.p., variação relativa e número de pessoas na amostra. Abaixo, uma frase de leitura que diz se a diferença é significativa ou não |
| **Gráfico 1: participação de cada grupo** | Barras lado a lado, uma para cada pesquisa, por grupo, com barras de erro (que podem ser desligadas na barra lateral) |
| **Gráfico 2: composição do total** | Uma barra empilhada por pesquisa, somando 100% das calorias (sem o grupo 2) |
| **Gráfico 3: diferença entre as pesquisas** | Diferença em p.p. por grupo (2017-2018 menos 2008-2009), com o intervalo de confiança e uma linha no zero. A barra fica mais clara quando o intervalo inclui o zero |
| **Resultados por grupo** | Tabela com as participações e seus intervalos, a diferença, o intervalo da diferença, a variação relativa e se a diferença é significativa |
| **Notas e limitações** | O texto da aba Notas da planilha, linha por linha |
| **Ver dados brutos** | As linhas da planilha que foram usadas e as diferenças que o aplicativo usou |

Os números aparecem no formato brasileiro (vírgula decimal). Os grupos aparecem sempre na mesma ordem e em cores categóricas, sem escala de intensidade e sem textos que sugiram que um grupo é melhor ou pior que outro.

## Como ler os resultados

- **Ponto percentual (p.p.)** é a subtração direta entre as duas participações. De 20% para 23% são +3 p.p.
- **Variação relativa** é a diferença dividida pela participação de 2008-2009. De 20% para 23% são +15%. Ponto percentual e variação relativa respondem a perguntas diferentes e não devem ser confundidos.
- **Intervalo de confiança de 95%** é a faixa em que o valor verdadeiro provavelmente está. Como os dados vêm de uma amostra, o valor exato é incerto.
- **Diferença significativa** quer dizer que o intervalo de confiança da diferença **não** inclui o zero.
- **Diferença não significativa não quer dizer que nada mudou.** Quer dizer que, com estes dados, não dá para afirmar que houve mudança. O recorte tem poucas pessoas (426 e 444) e só detecta diferenças grandes. O aplicativo escreve isso na frase de leitura.
- **Não classificado** mede a parte das calorias de alimentos que a planilha de classificação não cobre. Uma variação nele reflete a cobertura da classificação, e não uma mudança de consumo.

## Arquivo de resultados aceito pelo aplicativo

Um arquivo `.xlsx` com estas abas:

| Aba | Obrigatória | Conteúdo |
|---|---|---|
| `Resultados` | Sim | Uma linha por período e grupo, com as colunas `Periodo`, `Ano_Pesquisa`, `Grupo`, `Participacao_Pct`, `IC95_inferior`, `IC95_superior` e `N_Pessoas` |
| `Diferencas` | Não | `Grupo`, `Participacao_2008_2009`, `Participacao_2017_2018`, `Diferenca_pp`, `IC95_inferior`, `IC95_superior`, `Variacao_relativa_pct` e `Diferenca_significativa` (Sim ou Não). Sem esta aba, o aplicativo calcula a diferença e o intervalo |
| `Notas` | Não | Duas colunas: título e texto. Aparecem em "Notas e limitações" |
| `Kcal_por_dia` | Não | Consumo médio diário em kcal por grupo. O aplicativo ignora esta aba |

Regras dos valores:

- `Periodo` é `2008-2009` ou `2017-2018`, e `Ano_Pesquisa` é `2008` ou `2018`, combinando entre si.
- `Grupo` é um destes: `In natura`, `Processados`, `Ultraprocessados` ou `Não classificado`. Maiúsculas, espaços e acentos são normalizados. O grupo 2 fica de fora de propósito.
- `Participacao_Pct` e o intervalo de confiança são porcentagens de 0 a 100 (25,9 quer dizer 25,9%), com vírgula ou ponto decimal.

## Validações e avisos

| Situação | O que o aplicativo faz |
|---|---|
| Aba `Resultados` ausente | Mostra um erro com as abas encontradas e as colunas esperadas, e para |
| Colunas faltando | Mostra um erro com as colunas esperadas e as encontradas, e para |
| Arquivo que não abre | Mostra uma mensagem simples, com um bloco de detalhes técnicos, e para |
| Período, ano ou grupo fora da lista | Ignora a linha e avisa |
| `Periodo` e `Ano_Pesquisa` que não combinam | Ignora a linha e avisa |
| Valor que não é número, ou participação fora de 0 a 100 | Ignora a linha e avisa |
| Linha repetida no mesmo período e grupo | Mantém a primeira e avisa |
| Soma dos grupos de um período fora de 99,5 a 100,5 | Avisa e mostra os dados mesmo assim |
| Intervalo de confiança que não contém o valor | Avisa e mostra os dados mesmo assim |
| Falta um dos dois períodos | Avisa. A diferença aparece como "—" e o gráfico da diferença vira uma mensagem |
| `N_Pessoas` vazio ou com valores diferentes no mesmo período | Avisa. Mostra o primeiro valor, ou "—" |
| Aba `Diferencas` diverge mais de 0,1 do valor recalculado | Avisa e continua usando os números da aba |
| Aba `Diferencas` ausente | Calcula a diferença e o intervalo a partir dos intervalos de cada pesquisa |

## Rodar o aplicativo no seu computador

É preciso Python 3.12 ou mais novo.

- **Windows:** dê um duplo clique em `iniciar.bat`. Na primeira vez ele instala as bibliotecas (precisa de internet) e abre o aplicativo.
- **Outros sistemas:**

```bash
pip install -r requirements.txt
streamlit run app.py
```

O aplicativo abre em http://localhost:8501.

Para publicar no Streamlit Community Cloud, aponte para o `app.py` deste repositório e escolha Python 3.12 ou mais novo nas configurações avançadas, porque o `requirements.txt` fixa versões recentes das bibliotecas. Ao enviar uma versão nova do `app.py` para o GitHub, o Streamlit republica sozinho, no mesmo endereço.

## Como os resultados foram gerados

```
microdados do IBGE ──> processar_microdados.py ──> resultados_NOVA_PR_15a29.xlsx ──> app.py
 (POF 2008-09 e 2017-18)     (usa a classificação NOVA)        (planilha de resultados)    (tabelas e gráficos)
```

O cálculo fica no script, que pode ser conferido e repetido. O aplicativo só mostra o resultado.

### Requisitos do script

Python 3.9 ou superior e as bibliotecas:

```bash
pip install pandas numpy openpyxl xlrd
```

A `xlrd` é necessária para ler os arquivos `.xls` do IBGE.

### Onde obter os microdados

No site do IBGE (Pesquisa de Orçamentos Familiares):

- Microdados da POF 2008-2009 (com a documentação e o dicionário de variáveis);
- Microdados da POF 2017-2018 (com a documentação e o dicionário de variáveis);
- Tabelas de Composição Nutricional dos Alimentos Consumidos no Brasil (arquivo `tabelacompleta.xls`), usada para calcular a energia de 2008-2009.

Os microdados **não** estão neste repositório, por causa do tamanho. Cada pesquisa deve ser passada ao script no seu zip oficial. Um único zip com as duas pesquisas juntas pode fazer o script escolher o dicionário de variáveis errado.

### Execução

```bash
python processar_microdados.py \
  --zip-2017 POF_2017-2018.zip \
  --zip-2008 POF_2008-2009.zip \
  --zip-composicao Tabelas.zip \
  --classificacao classificacao_NOVA_final.xlsx \
  --saida resultados_NOVA_PR_15a29.xlsx
```

Opcionalmente, `--notas-de arquivo.xlsx` copia a aba Notas de um arquivo anterior. A leitura da POF 2017-2018 leva alguns minutos.

Ao terminar, o script imprime conferências: o número de pessoas de 15 a 29 anos em cada pesquisa (426 e 444), o número de pessoas de 10 anos ou mais com consumo no Paraná em 2017-2018 (1.988, igual ao valor publicado pelo IBGE) e quantos registros de 2008-2009 ficaram sem energia (7).

## Metodologia em resumo

- **Recorte:** pessoas de 15 a 29 anos, Paraná inteiro (UF 41), com registro de consumo alimentar individual.
- **Energia:** em 2017-2018, a energia já vem no microdado. Em 2008-2009, é calculada com a quantidade consumida e a tabela de composição do IBGE.
- **Classificação:** cada alimento pertence a um único grupo NOVA, conforme `classificacao_NOVA_final.xlsx`, com base na lista de Louzada et al. (2023). Alimentos fora da planilha ficam como "Não classificado".
- **Participação:** soma ponderada das calorias do grupo dividida pela soma ponderada das calorias de todos os grupos, **sem o grupo 2**, usando o peso final (`PESO_FINAL`) do IBGE.
- **Margem de erro:** intervalo de confiança de 95%, por linearização de Taylor, considerando estratos e setores censitários (amostra complexa).
- **Diferença entre as pesquisas:** em pontos percentuais (2017-2018 menos 2008-2009), tratando as pesquisas como amostras independentes. É significativa quando o intervalo de 95% não inclui o zero.
- **Dias de consumo:** são usados os dois dias de cada pessoa, nas duas pesquisas.

## Ressalvas importantes

- **O grupo 2 (ingredientes culinários) ficou de fora.** Ele não é comparável entre as pesquisas, porque o açúcar e o azeite adicionados foram coletados de modo diferente. Por isso os percentuais deste trabalho **não** são diretamente comparáveis aos de estudos que incluem o grupo 2 no total.
- **A amostra do recorte é pequena** (426 e 444 pessoas). Os intervalos de confiança são largos, e uma diferença não significativa **não** significa que não houve mudança.
- **As pesquisas usaram métodos de coleta diferentes** (registro alimentar em 2008-2009 e recordatório de 24 horas em 2017-2018), e os códigos de alimentos mudaram entre elas.
- **A classificação é por alimento**, sem desmontar preparações em ingredientes. Alguns itens dependem de suposição (por exemplo, o suco genérico foi considerado ultraprocessado).

A descrição completa do método, das decisões de classificação e das limitações está no documento técnico do trabalho. [Inserir o link ou a referência do documento.]

## Estrutura do repositório

| Arquivo | Para que serve |
|---|---|
| `app.py` | Aplicativo (Streamlit) que lê a planilha de resultados e mostra tabelas e gráficos |
| `requirements.txt` | Bibliotecas do aplicativo, com as versões testadas |
| `iniciar.bat` | No Windows, instala as bibliotecas e abre o aplicativo com um duplo clique |
| `LEIA-ME.txt` | Instruções de uso do aplicativo em texto simples |
| `processar_microdados.py` | Lê os microdados do IBGE, calcula as participações, as margens de erro e as diferenças, e grava a planilha de resultados |
| `classificacao_NOVA_final.xlsx` | Liga cada código de alimento do IBGE a um grupo NOVA (262 alimentos). Foi produzida neste trabalho e não vem de nenhuma fonte externa |
| `resultados_NOVA_PR_15a29.xlsx` | Resultados já calculados pelo script |
| `gerar_testes.py` | Cria a pasta `testes/` com planilhas que provocam cada situação de validação do aplicativo |
| `app_versao_anterior.py` | Versão anterior do aplicativo (aquisição domiciliar). Não é usada |

## Testes do aplicativo

```bash
python gerar_testes.py
```

Cria a pasta `testes/` com 12 planilhas: arquivo correto, sem a aba Diferencas, sem a aba Notas, soma errada, grupo inválido, intervalo invertido, só um período, coluna faltando, ano inválido, valores com vírgula, diferenças divergentes e arquivo corrompido. O script imprime o comportamento esperado do aplicativo para cada uma. Para testar, envie cada planilha ao aplicativo e compare com o que foi impresso.

## Fontes, autoria e licença

**Fontes**

- IBGE. Pesquisa de Orçamentos Familiares 2008-2009 e 2017-2018: microdados e documentação.
- IBGE. Tabelas de Composição Nutricional dos Alimentos Consumidos no Brasil.
- LOUZADA, M. L. C. et al. Consumo de alimentos ultraprocessados no Brasil: distribuição e evolução temporal 2008-2018. *Revista de Saúde Pública*, v. 57, 2023. doi: 10.11606/s1518-8787.2023057004744.

**Autoria**

Metodologia, classificação dos alimentos e interpretação dos resultados: [nome da autora do TCC].

Script e aplicativo: [seu nome].

**Licença**

[Escolher a licença do código, por exemplo MIT, ou remover esta seção.] Os microdados e as tabelas do IBGE seguem os termos de uso do IBGE.
