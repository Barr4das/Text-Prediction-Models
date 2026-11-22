# Pré-processamento

Esta pasta contém os passos que transformam as obras originais no *corpus* usado
para treinar os modelos. Cada passo está num ficheiro próprio, numerado pela
ordem em que foi criado (`01_`, `02_`, …).

```
preprocessing/
├── main.py       # corre todos os passos
├── run_all.sh    # corre todos os passos e aplica a limpeza manual registada
├── steps/        # um script por passo
└── resources/    # dados usados pelos passos (pistas, clíticos, grafias, meses, confusões do OCR)
```

## Correr todos os passos

```bash
python code/preprocessing/main.py <pasta_originais> <pasta_trabalho> <pasta_corpus_limpo>
```

Os passos são corridos por esta ordem: 01, 02, 03, 09, 04, 05, 06 e 07. O resultado
intermédio de cada passo fica numa subpasta da pasta de trabalho
(`01_txt/`, `03_pdf_fix/`, `09_page_breaks/`, `04_normalization/`,
`06_orthography/`) e o *corpus*
final na pasta indicada. As obras digitalizadas devem estar na subpasta `ocr/`
da pasta de originais.

No fim, mostra uma tabela com o número de palavras, o tamanho do vocabulário
(formas distintas, sem distinguir maiúsculas de minúsculas) e o número de frases
do *corpus* depois de cada passo que altera o texto.

Para incluir também a limpeza manual (passo 08), a partir da raiz do repositório:

```bash
bash code/preprocessing/run_all.sh
```

que corre o `main.py` com `data/raw`, `data/work` e `data/clean`, aplica os cortes
registados em `resources/08_manual_cuts.json` e escreve o *corpus* final em
`data/final`.

Cada passo também pode ser corrido isoladamente, como descrito abaixo.

## Passos

| Ficheiro | Passo |
|---|---|
| `01_file_conversion.sh` | Conversão dos originais (EPUB, MOBI, PDF) para texto |
| `02_variety_clues.py` | Pistas de português europeu vs. do Brasil em cada obra |
| `03_pdf_fix.py` | Correção dos defeitos da conversão de PDF |
| `04_normalization.py` | Normalização de Unicode e espaços |
| `05_silent_consonants.py` | Identificação das obras escritas segundo o Acordo Ortográfico de 1990 |
| `06_orthography.py` | Conversão das obras escritas segundo o Acordo de 1990 para a grafia anterior |
| `07_ocr_fix.py` | Correção de erros de OCR nas obras digitalizadas |
| `09_page_breaks.py` | Remoção das quebras de página nas obras com a paginação do livro impresso |
| `08_manual_cuts.py` | Aplicação da limpeza manual registada (paratexto e ruído de digitalização) |

## 01 Conversão de formato (`01_file_conversion.sh`)

Converte cada obra da pasta de origem num ficheiro `.txt` na pasta de destino,
com o mesmo nome da obra (`Caim.epub` → `Caim.txt`). O texto é escrito em UTF-8
e não é limpo nesta fase.

A ferramenta usada depende do formato:

| Formato | Ferramenta |
|---|---|
| EPUB, MOBI | `ebook-convert` ([Calibre](https://calibre-ebook.com/)) |
| PDF | `pdftotext` ([Poppler](https://poppler.freedesktop.org/)) |

Ficheiros com outras extensões são ignorados. As subpastas da pasta de origem
(por exemplo, `ocr/`) são mantidas na pasta de destino.

### Utilização

```bash
bash code/preprocessing/steps/01_file_conversion.sh <pasta_origem> <pasta_destino>
```

Para cada obra, o *script* indica o resultado:

```
OK       Caim.epub
ERROR    Livro danificado.pdf
SKIPPED  notas.docx
```

Uma obra que falhe não interrompe a conversão das restantes. O *script* termina
com erro se faltarem argumentos, se a pasta de origem não existir ou se o
`ebook-convert` ou o `pdftotext` não estiverem instalados.

## 02 Pistas de variedade (`02_variety_clues.py`)

Procura, em cada obra, pistas de que o texto está em português europeu (PE) ou do
Brasil (PB). O *script* não decide a variedade: mostra as pistas encontradas e o
veredicto é tomado à mão.

As pistas dividem-se em dois tipos, contados separadamente:

- **Edição** (`credits`): ISBN e editora, procurados nos créditos. Dizem onde o
  livro foi publicado, não em que variedade está o texto.
- **Texto** (`text`): acentuação, ortografia, vocabulário e sintaxe, procurados no
  texto da obra.

A separação é necessária porque as duas podem não coincidir: as edições
brasileiras de Saramago mantêm o texto original em português europeu.

### Utilização

```bash
python code/preprocessing/steps/02_variety_clues.py <pasta_txt> <pistas_json>
```

As pistas estão definidas em `resources/02_variety_clues.json`. Cada pista tem a variedade
(`PE`/`PB`), a categoria, a expressão regular, a força (`strong`, `medium`,
`weak`) e onde é procurada (`credits` ou `text`):

```json
{
  "variety": "PB",
  "category": "ISBN",
  "pattern": "\\b978[-\\s]?(?:85|65)[-\\s]?\\d",
  "strength": "strong",
  "scope": "credits"
}
```

A pesquisa não distingue maiúsculas de minúsculas.

Em cada obra são lidas amostras do `.txt`:

- **créditos:** nas obras vindas de PDF, as páginas 2 a 6 (o `pdftotext` separa
  as páginas com `\f`); nas restantes, o início do texto;
- **texto:** três excertos a 25%, 50% e 75% da obra.

Estes valores podem ser alterados com argumentos opcionais:

| Argumento | Por omissão | Significado |
|---|---|---|
| `--sample-size` | `3000` | caracteres em cada amostra |
| `--text-positions` | `25 50 75` | posições das amostras de texto, em % da obra |
| `--credits-pages` | `2 6` | primeira e última página lidas como créditos |

## 03 Correção dos PDF (`03_pdf_fix.py`)

Corrige os defeitos que a conversão de PDF deixa no texto:

- números de página e cabeçalhos ou rodapés repetidos (por exemplo, o título da
  obra ou o nome do autor), procurados só nas primeiras e últimas linhas de cada
  página;
- palavras partidas por hífen no fim da linha (`extra-` / `vagâncias`), mantendo
  o hífen quando faz parte da palavra (`disse-me`);
- linhas do mesmo parágrafo partidas a meio.

Uma obra é tratada como vinda de PDF quando o texto tem quebras de página (`\f`),
que o `pdftotext` insere entre páginas. As restantes obras são copiadas sem
alterações, para que a pasta de destino fique completa.

### Utilização

```bash
python code/preprocessing/steps/03_pdf_fix.py <pasta_origem> <pasta_destino> <cliticos_json>
```

Os pronomes que mantêm o hífen quando a palavra é partida no fim da linha
(`disse-` / `me`) estão definidos em `resources/03_clitics.json`.

| Argumento | Por omissão | Significado |
|---|---|---|
| `--min-header-repeats` | `8` | vezes que uma linha tem de se repetir nas margens das páginas para ser considerada cabeçalho |
| `--margin-lines` | `2` | linhas do topo e do fundo de cada página onde se procuram cabeçalhos e números de página |
| `--max-header-length` | `60` | comprimento máximo de uma linha de cabeçalho |

## 04 Normalização (`04_normalization.py`)

Uniformiza a forma como o texto está escrito, sem alterar o conteúdo:

- converte o texto para a forma Unicode NFC, para que cada letra acentuada seja
  sempre o mesmo carácter (`é` como um só carácter, e não `e` + acento);
- remove o hífen invisível (*soft hyphen*, U+00AD), que marca onde uma palavra
  pode ser partida;
- junta espaços, tabulações e espaços não separáveis num único espaço;
- remove os espaços no início e no fim das linhas e as linhas vazias, ficando
  um parágrafo por linha.

Não altera maiúsculas nem pontuação.

### Utilização

```bash
python code/preprocessing/steps/04_normalization.py <pasta_origem> <pasta_destino>
```

## 05 Consoantes mudas (`05_silent_consonants.py`)

Identifica as obras escritas segundo o Acordo Ortográfico de 1990. Para cada
obra, conta:

- as palavras com grupos consonânticos (`acção`, `actual`, `óptimo`), por 1000
  palavras;
- as ocorrências da grafia anterior e da posterior ao Acordo, num conjunto de
  pares de palavras (`acção`/`ação`, `direcção`/`direção`, …).

Uma obra em que as formas posteriores ao Acordo são mais frequentes do que as
anteriores segue o Acordo de 1990.

### Utilização

```bash
python code/preprocessing/steps/05_silent_consonants.py <pasta_origem> <pares_json>
```

Os pares de grafias estão definidos em `resources/05_spelling_pairs.json`, cada um com a
forma anterior (`pre_agreement`) e a posterior (`post_agreement`) ao Acordo.

| Argumento | Por omissão | Significado |
|---|---|---|
| `--top` | `20` | número de palavras com grupos consonânticos mais frequentes a mostrar |

## 06 Ortografia anterior ao Acordo (`06_orthography.py`)

Converte as obras escritas segundo o Acordo Ortográfico de 1990 para a grafia
anterior, usada por Saramago.

As obras que seguem o Acordo são identificadas com os pares de grafias do passo
05: são as que têm mais formas posteriores ao Acordo do que anteriores. As
restantes obras servem de vocabulário de referência e são copiadas sem
alterações.

Em cada obra que segue o Acordo:

1. para cada palavra, gera-se a grafia anterior repondo a consoante muda antes
   de *ç*, *t* ou *c* (`ação` → `acção`, `ótimo` → `óptimo`,
   `seleção` → `selecção`);
2. a palavra é substituída só quando a grafia anterior é frequente nas obras de
   referência e a posterior (quase) não aparece nelas, para não alterar palavras
   que existem nas duas grafias (`fato`, peça de roupa, não passa a `facto`);
3. aplicam-se as outras alterações do Acordo: `há de` → `há-de`,
   `leem` → `lêem` e os meses em maiúscula nas datas (`5 de março` →
   `5 de Março`).

### Utilização

```bash
python code/preprocessing/steps/06_orthography.py <pasta_origem> <pasta_destino> <pares_json> <grafias_json> <meses_json>
```

- `resources/05_spelling_pairs.json`: pares usados para identificar as obras que
  seguem o Acordo (os mesmos do passo 05);
- `resources/06_explicit_spellings.json`: grafias alteradas pelo Acordo que não
  envolvem consoantes mudas, em duas classes: verbos em *-eem* que perderam o
  acento circunflexo (`lêem`/`leem`) e ditongos abertos *ói* em palavras graves
  que perderam o acento agudo (`jóia`/`joia`, `heróica`/`heroica`). Cada entrada
  só é aplicada se a grafia anterior aparecer nas obras de referência; ficam de
  fora as palavras em que a grafia posterior coincide com outra palavra
  (`pára`/`para`);
- `resources/06_months.json`: nomes dos meses.

| Argumento | Por omissão | Significado |
|---|---|---|
| `--min-old-in-reference` | `3` | ocorrências da grafia anterior nas obras de referência para a usar |
| `--max-new-in-reference` | `1` | ocorrências máximas da grafia posterior nas obras de referência |

## 07 Correção de OCR (`07_ocr_fix.py`)

Corrige erros de reconhecimento ótico de caracteres (OCR) nas obras digitalizadas,
como acentos perdidos ou trocados (`nao` → `não`, `Jodo` → `João`) e algarismos
lidos em vez de letras (`s6` → `só`, `j4` → `já`).

As restantes obras servem de vocabulário de referência. Uma palavra de uma obra
digitalizada é corrigida quando:

1. é desconhecida, ou seja, aparece poucas vezes nas obras de referência;
2. trocando até três caracteres, segundo as confusões típicas do OCR, se obtém
   uma palavra frequente nas obras de referência.

Entre as correções possíveis, ganha a que troca menos caracteres e, em caso de
empate, a mais frequente. Palavras sem uma correção possível ficam como estão.

As obras digitalizadas são as que estão na subpasta `ocr/` da pasta de origem;
as restantes são copiadas sem alterações.

### Utilização

```bash
python code/preprocessing/steps/07_ocr_fix.py <pasta_origem> <pasta_destino> <confusoes_json>
```

As confusões do OCR estão definidas em `resources/07_ocr_confusions.json`: para cada
carácter lido pelo OCR, os caracteres que pode representar (por exemplo,
`"6": "ó"`).

| Argumento | Por omissão | Significado |
|---|---|---|
| `--ocr-subdir` | `ocr` | subpasta com as obras digitalizadas |
| `--max-edits` | `3` | número máximo de caracteres trocados numa palavra |
| `--min-reference-count` | `3` | ocorrências nas obras de referência para uma palavra ser conhecida |
| `--min-frequency-ratio` | `10` | quantas vezes a correção tem de ser mais frequente do que a palavra original |

## 08 Limpeza manual (`08_manual_cuts.py`)

O paratexto (créditos, sinopses, índices, biografias, dedicatórias e epígrafes),
os ensaios de outros autores em *Alabardas, Alabardas, Espingardas, Espingardas* e
o ruído de digitalização foram removidos manualmente. Para que o resultado possa
ser reproduzido, os cortes ficam registados em `resources/08_manual_cuts.json`:
para cada obra, a primeira e a última linha mantidas, o início de linha retirado
quando o texto estava colado a um cabeçalho e outras edições feitas no meio do
texto.

### Utilização

```bash
python code/preprocessing/steps/08_manual_cuts.py <pasta_origem> <pasta_destino> <cortes_json>
```

Os cortes referem-se a uma versão concreta do *corpus*: se o número de linhas de
uma obra não coincidir com o registado, o passo termina com erro. Para não perder
edições feitas à mão, também não escreve por cima de um ficheiro com alterações
que não estejam registadas.

| Argumento | Por omissão | Significado |
|---|---|---|
| `--overwrite` | — | escreve por cima mesmo que o ficheiro de destino tenha alterações não registadas |

## 09 Quebras de página (`09_page_breaks.py`)

Algumas obras, apesar de não virem de PDF, mantêm a paginação do livro impresso:

- números de página sozinhos numa linha;
- números de página colados ao fim da última linha de cada página
  (`tem o céu 13`);
- frases e palavras partidas no fim de cada página ou linha (`acto poé-` /
  `tico`).

O passo remove os números de página e junta as linhas que não terminam uma
frase. Os números no fim das linhas só são removidos quando, ao longo da obra,
formam uma sequência crescente. Só são alteradas as obras com a paginação
partida; as restantes são copiadas sem alterações.

### Utilização

```bash
python code/preprocessing/steps/09_page_breaks.py <pasta_origem> <pasta_destino> <cliticos_json>
```

Usa os mesmos clíticos do passo 03 (`resources/03_clitics.json`).

| Argumento | Por omissão | Significado |
|---|---|---|
| `--min-trailing-numbers` | `10` | números no fim das linhas necessários para serem tratados como números de página |
| `--min-increasing` | `0.9` | proporção desses números que tem de ser crescente |
| `--max-open-lines` | `0.3` | proporção de linhas sem fim de frase acima da qual a paginação está partida |
| `--max-title-length` | `40` | comprimento até ao qual uma linha seguida de maiúscula é um título |
