# Dados

Esta pasta contém as obras usadas para treinar os modelos, os modelos treinados
e os resultados das experiências. Os textos não estão incluídos no repositório
por estarem protegidos por direitos de autor; só a estrutura de pastas é
distribuída.

## Estrutura

| Pasta | Conteúdo | Quem cria |
|---|---|---|
| `raw/` | ficheiros originais (EPUB, MOBI, PDF) | o utilizador |
| `raw/ocr/` | originais digitalizados (PDF com texto obtido por OCR) | o utilizador |
| `work/` | resultado intermédio de cada passo do pré-processamento | `main.py` |
| `clean/` | *corpus* após os passos automáticos | `main.py` |
| `final/` | *corpus* final, com a limpeza manual | `run_all.sh` |
| `models/` | modelos treinados (`.pkl`) | `train.py` |
| `experiments/` | resultados das experiências (`results.json`) | `experiments.py` e `gpt2.py` |

## Como preparar

1. Colocar os originais em `raw/`, com o título da obra como nome, e os
   digitalizados em `raw/ocr/`.
2. Correr, a partir da raiz do repositório:

   ```bash
   bash code/preprocessing/run_all.sh
   ```

3. Treinar um modelo e correr as experiências:

   ```bash
   python code/model/train.py data/final data/models/kn4.pkl -n 4
   python code/model/experiments.py data/final code/model/resources/questions.json data/experiments/results.json
   python code/model/gpt2.py data/final code/model/resources/questions.json data/experiments/results.json
   ```

## Obras usadas

| Obra | Formato |
|---|---|
| *A Bagagem do Viajante* | EPUB |
| *A Caverna* | EPUB |
| *A Jangada de Pedra* | EPUB |
| *A Viagem do Elefante* | EPUB |
| *Alabardas, Alabardas, Espingardas, Espingardas* | EPUB |
| *As Intermitências da Morte* | EPUB |
| *Caim* | EPUB |
| *Claraboia* | EPUB |
| *Deste Mundo e do Outro* | EPUB |
| *Ensaio sobre a Cegueira* | EPUB |
| *Ensaio sobre a Lucidez* | PDF (digital) |
| *História do Cerco de Lisboa* | EPUB |
| *Levantado do Chão* | PDF (digitalizado, OCR) |
| *Memorial do Convento* | PDF (digital) |
| *O Ano da Morte de Ricardo Reis* | MOBI |
| *O Evangelho segundo Jesus Cristo* | EPUB |
| *O Homem Duplicado* | EPUB |
| *Terra do Pecado* | PDF (digital) |
| *Todos os Nomes* | PDF (digitalizado, OCR) |

Total: 19 obras (13 EPUB, 1 MOBI, 5 PDF).

- **PDF digitalizado (OCR):** imagens de páginas impressas com texto reconhecido
  automaticamente; têm erros de reconhecimento que o *pipeline* corrige em
  parte.
- ***Manual de Pintura e Caligrafia*** foi excluído: era a obra com pior
  qualidade de digitalização e a mais distante do resto do *corpus*.
