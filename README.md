# Text-Prediction-Models

O presente trabalho foi desenvolvido para a cadeira de Processamento de
Linguagem Natural, do Mestrado em Engenharia Informática do ISEL, lecionada pela
Dra. Matilde Pato.

Este trabalho insere-se como uma implementação prática dos conteúdos lecionados
em aula, mais especificamente, referente à criação de modelos de previsão de
texto de n-gramas.

## Objetivo

O tópico atribuído ao trabalho foi utilizar modelos de previsão de texto para
tentar responder a perguntas.

Para isso, escolhemos treinar os modelos exclusivamente na obra de José
Saramago, precisamente por ser uma escrita difícil de modelar:

- na maior parte das obras, as personagens não têm nome (*o médico*, *a rapariga
  dos óculos escuros*);
- o diálogo não é marcado por travessões nem aspas, mas apenas por vírgulas e
  maiúsculas, o que torna difícil separar o diálogo da narração;
- as frases são longas e a pontuação foge às convenções, o que dificulta a
  modelação em geral.

Do lado prático, a obra de Saramago permite reunir um *corpus* de português
europeu de grandes dimensões, de um autor de que gostamos de ler.

Sobre esta base, o trabalho procura perceber até onde um modelo de n-gramas
consegue chegar:

- **Perguntas:** consegue o modelo responder no tema a um conjunto fixo de
  perguntas (*O que é a democracia?*, *Porque é que existem partidos
  políticos?*)?
- **Quantidade de texto:** como melhora o modelo com o número de obras no
  treino?
- **Configuração:** que técnica de suavização e que ordem de n-grama funcionam
  melhor neste *corpus*?
- **Comparação:** como se compara com um modelo neural (GPT-2) e com o mesmo
  modelo treinado noutro *corpus* de português (Machado de Assis, do NLTK)?

## Abordagem

- **Corpus:** 19 obras de Saramago, convertidas de EPUB, MOBI e PDF para texto e
  restritas ao português europeu.
- **Limpeza:** um *pipeline* em várias fases corrige os problemas encontrados
  nos ficheiros originais: erros de digitalização (OCR), números de página e
  quebras de linha, diferenças ortográficas antes e depois do Acordo de 1990, e
  texto que não é de Saramago (créditos, sinopses, ensaios de outros autores).
- **Modelo:** modelos de linguagem de n-gramas com várias técnicas de suavização
  (Laplace, Lidstone e Kneser-Ney), treinados com 1 a 18 obras e com
  n = 2, 3 e 4.
- **Avaliação:** perplexidade e previsão das palavras seguintes (*top-5*) numa
  obra que fica fora do treino (*Caim*), e respostas às perguntas, contando as
  que ficam no tema.

Cada fase de limpeza é medida pelo seu efeito no texto gerado, e todos os
resultados podem ser reproduzidos a partir do código.

## Instalação

Programas do sistema, usados na conversão das obras para texto:

- [Calibre](https://calibre-ebook.com/) (`ebook-convert`), para EPUB e MOBI;
- [Poppler](https://poppler.freedesktop.org/) (`pdftotext`), para PDF.

```bash
sudo apt install calibre poppler-utils
```

Pacotes de Python:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

O `torch` e o `transformers` só são precisos para o `gpt2.py`. Para instalar o
`torch` sem suporte para GPU (mais leve):

```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

## Organização dos ficheiros

```
Text-Prediction-Models/
├── code/
│   ├── domain/                  # classes partilhadas (pistas, perguntas, pares ortográficos)
│   ├── preprocessing/           # limpeza do corpus (ver code/preprocessing/README.md)
│   │   ├── main.py              # corre todas as fases e mostra as estatísticas do corpus
│   │   ├── run_all.sh           # corre o pipeline completo, incluindo os cortes manuais
│   │   ├── steps/               # uma fase por ficheiro, numeradas de 01 a 09
│   │   └── resources/           # dados de cada fase em JSON, com o número da fase
│   └── model/                   # modelos de n-gramas (ver code/model/README.md)
│       ├── ngram_model.py       # o modelo
│       ├── corpus.py            # seleção dos livros e divisão em frases e palavras
│       ├── train.py             # treina e guarda um modelo
│       ├── use.py               # usa um modelo treinado
│       ├── experiments.py       # experiências da apresentação
│       ├── gpt2.py              # comparação com o GPT-2
│       ├── baseline.py          # baseline com o corpus machado do NLTK
│       └── resources/           # perguntas, palavras de tema e inícios de frase
├── requirements.txt             # pacotes de Python
└── data/                        # ignorada pelo Git (ver data/README.md)
    ├── raw/                     # ficheiros originais das obras (EPUB, MOBI, PDF)
    ├── work/                    # resultados intermédios da limpeza
    ├── clean/                   # corpus limpo pelas fases automáticas
    ├── final/                   # corpus final, depois dos cortes manuais
    ├── models/                  # modelos treinados
    └── experiments/             # resultados das experiências
```

> **Nota:** os textos das obras não estão incluídos no repositório por estarem
> protegidos por direitos de autor. Para correr o projeto é necessário ter
> cópias próprias das obras.
