# Modelo

Modelos de linguagem de n-gramas treinados sobre o *corpus* limpo. O treino e o
uso dos modelos são feitos por *scripts* separados.

```
model/
├── ngram_model.py   # o modelo: contagens, suavização, previsão, geração, perplexidade
├── corpus.py        # seleção dos livros e divisão em frases e palavras
├── train.py         # treina um modelo e guarda-o num ficheiro
├── use.py           # usa um modelo já treinado
├── experiments.py   # experiências da apresentação
├── gpt2.py          # comparação com o GPT-2
├── baseline.py      # baseline treinado no corpus machado do NLTK
└── resources/
    ├── questions.json        # perguntas, inícios de resposta e palavras de tema
    └── book_prompts.json     # inícios de frase de obras do treino
```

## Modelo (`ngram_model.py`)

Modelo de n-gramas de ordem configurável, com três técnicas de suavização:

| Suavização | Ideia |
|---|---|
| `laplace` | soma 1 a todas as contagens |
| `lidstone` | soma *k* < 1 a todas as contagens |
| `kneser_ney` | desconto absoluto e interpolação; as ordens inferiores contam em quantos contextos diferentes cada palavra aparece |

A previsão das palavras seguintes, a geração de texto e a perplexidade usam a
mesma distribuição de probabilidade suavizada. As maiúsculas e a pontuação são
mantidas.

## Treino (`train.py`)

```bash
python code/model/train.py <pasta_corpus> <ficheiro_modelo> [opções]
```

| Argumento | Por omissão | Significado |
|---|---|---|
| `-n` | `3` | ordem do n-grama |
| `--smoothing` | `kneser_ney` | técnica de suavização (`laplace`, `lidstone`, `kneser_ney`) |
| `--lidstone-k` | `0.01` | valor somado a cada contagem na suavização de Lidstone |
| `--books` | todos | títulos dos livros usados no treino |
| `--books-json` | — | ficheiro JSON com a lista dos títulos dos livros usados no treino |

Exemplos:

```bash
# todos os livros, trigramas, Kneser-Ney
python code/model/train.py data/final data/models/kn3.pkl

# um só livro, bigramas, Laplace
python code/model/train.py data/final data/models/laplace2_caverna.pkl -n 2 --smoothing laplace --books "A Caverna"

# um conjunto de livros definido num ficheiro
python code/model/train.py data/final data/models/kn4.pkl -n 4 --books-json livros.json
```

## Uso (`use.py`)

```bash
python code/model/use.py <ficheiro_modelo> <comando> [opções]
```

| Comando | O que faz |
|---|---|
| `predict "<texto>" [-k 5]` | as *k* palavras seguintes mais prováveis |
| `generate "<texto>" [--max-tokens 40] [--seed N]` | continua o texto |
| `questions <perguntas_json> [--answers 3] [--max-tokens 40] [--seed N]` | responde às perguntas, continuando o início de resposta de cada uma |
| `perplexity <pasta_corpus> [--books TÍTULO …]` | perplexidade do modelo num conjunto de livros |

Exemplos:

```bash
python code/model/use.py data/models/kn3.pkl predict "A democracia é"
python code/model/use.py data/models/kn3.pkl generate "O voto é" --seed 1
python code/model/use.py data/models/kn3.pkl questions code/model/resources/questions.json --seed 42
python code/model/use.py data/models/kn3.pkl perplexity data/final --books Caim
```

Para medir a perplexidade de forma justa, os livros usados no comando
`perplexity` não devem ter sido usados no treino.

Os modelos são guardados com `pickle` e devem ser carregados apenas a partir de
ficheiros de confiança. Ficam em `data/models/`, que é ignorada pelo Git.

## Experiências (`experiments.py`)

Reproduz os resultados da apresentação, com um livro de teste que nunca é usado no
treino (por omissão, as primeiras 300 frases de *Caim*; `--test-book` e
`--test-sentences`):

- efeito do número de obras no treino (1, 3, 6, 12 e 18);
- comparação das técnicas de suavização e da ordem do n-grama;
- previsões para inícios de frase de obras que estão, ou não, no treino
  (`resources/book_prompts.json`: cada início de frase é um nome ou expressão
  típica da obra indicada);
- respostas às perguntas e avaliação das perguntas de medição com o modelo final
  (todas as obras, por omissão Kneser-Ney com n = 4; `--final-n` e
  `--final-smoothing`): 5 respostas por pergunta, contando as que ficam no tema
  (usam alguma das palavras de `topics` da pergunta em `resources/questions.json`).

```bash
python code/model/experiments.py data/final code/model/resources/questions.json data/experiments/results.json
```

## Comparação com o GPT-2 (`gpt2.py`)

Acrescenta ao mesmo ficheiro de resultados a comparação com o GPT-2 *small*
português (`pierreguillou/gpt2-small-portuguese`, alterável com `--model`):
perplexidade por palavra no livro de teste, continuação dos mesmos inícios de
frase e respostas às perguntas de medição. Requer `torch` e `transformers` e deve
correr depois do `experiments.py`.

```bash
python code/model/gpt2.py data/final code/model/resources/questions.json data/experiments/results.json
```

## *Baseline* com o *corpus* `machado` (`baseline.py`)

Treina o mesmo modelo (por omissão n = 4 e Kneser-Ney; `-n` e `--smoothing`)
sobre o *corpus* `machado` do NLTK (obras de Machado de Assis, em português do
Brasil) e compara-o com o modelo treinado nas obras de Saramago sem o livro de
teste. Cada modelo é avaliado no livro de teste de Saramago e numa obra de
Machado que fica fora do treino (por omissão *Dom Casmurro*; `--machado-test`).
Acrescenta ao ficheiro de resultados o tamanho dos dois *corpora*, a
perplexidade, o *top-5* e a taxa de palavras desconhecidas, e as respostas do
modelo `machado` às perguntas de medição. Deve correr depois do
`experiments.py`.

```bash
python code/model/baseline.py data/final code/model/resources/questions.json data/experiments/results.json
```
