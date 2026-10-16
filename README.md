# Jisho Card (辞書カード)

Addon do Anki para estudar japonês. Você digita só a palavra (`食べる`) e o addon preenche o resto do
cartão a partir de um dicionário offline: leitura em hiragana, furigana, classe gramatical, significados,
kanji (kun, on, traços, radical, JLPT), frase de exemplo com furigana, áudio, animação da ordem dos traços
e a tabela de conjugação. O cartão tem aparência de verbete de dicionário, com modo escuro e layout de celular.

Tudo fica gravado nos campos e na mídia da coleção. Por isso o cartão funciona no AnkiDroid, no AnkiMobile e
no AnkiWeb, onde o addon não roda.

## Requisitos

- Anki 24.11 ou mais recente (desktop). Testado no 26.8.1.
- Internet só para gerar o áudio e, uma vez, para baixar o dicionário.

## Instalação

1. **Pacote pronto:** baixe `jisho_card.ankiaddon` na página de
   [Releases](https://github.com/adrielqueiroz2006/jisho-anki/releases) e use, no Anki,
   Ferramentas › Complementos › Instalar a partir de arquivo.
   **A partir do código:** `python tools/setup_vendor.py` (instala Janome e gTTS em `addon/vendor/`), depois
   `python tools/package.py` cria `build/jisho_card.ankiaddon`. Para desenvolver, `python tools/install_dev.py`
   liga a pasta `addon/` ao Anki (feche o Anki antes).
2. **Dicionário.** O addon precisa do `dicionario.sqlite`, que não vai dentro do pacote (tem 132 MB; o download
   compactado tem 27 MB). Ao abrir o Anki pela primeira vez, ele oferece baixar o dicionário do release
   `dicionario-v1` deste repositório (confere o SHA-256 antes de instalar). Se preferir:
   - Gerar na sua máquina: `python tools/build_db.py` cria `build/dicionario.sqlite` (baixa JMdict, KANJIDIC2,
     KanjiVG e Tatoeba; leva alguns minutos). No modo `install_dev` o addon já o encontra sozinho.
   - Ferramentas › Jisho Card › **Escolher arquivo do dicionário…** e apontar um `dicionario.sqlite`.
   - Ferramentas › Jisho Card › **Baixar dicionário**, a qualquer momento.
3. Reabra o Anki. O tipo de nota **Jisho Card** é criado sozinho.

## Como usar

- **Adicionar:** escolha o tipo “Jisho Card”, digite a palavra no primeiro campo e saia do campo (ou clique em
  **辞**, ou Ctrl+Shift+J). O addon preenche os campos vazios. Se a palavra tiver mais de uma entrada (生, 水,
  上手), abre uma janela para escolher. Formas flexionadas (食べます) e verbos com する (勉強する) são entendidos.
- **Nunca sobrescreve o que você escreveu.** Só preenche campos vazios. O botão **再** (Regerar) substitui o
  conteúdo gerado, menos Palavra e Notas, e pede confirmação.
- **Em lote:** no navegador, selecione notas e use o menu **Jisho Card › Preencher notas selecionadas**
  (também no clique direito) ou **Regerar notas selecionadas…**. Dá para cancelar com Esc, e o Anki desfaz o
  lote em Editar › Desfazer. Ao fim aparece um relatório (não encontradas, formas flexionadas, entradas ambíguas).
- **Deck de teste:** Ferramentas › Jisho Card › Criar deck de teste cria 20 palavras que cobrem os casos difíceis.
- **Configurações:** Ferramentas › Jisho Card › Configurações (voz, hiragana ou katakana no onyomi, áudio,
  preenchimento automático, lote, dicionário).

### Os 16 campos

Palavra · Leitura · Furigana · ÁudioPalavra · ClasseGramatical · Significado · KanjiInfo · Kunyomi · Onyomi ·
Exemplo · ExemploFurigana · ExemploTradução · ExemploÁudio · Traços · Conjugação · Notas.
Você só digita o primeiro; o resto é preenchido e pode ser editado à mão. As notas ganham tags como
`jisho::verbo`, `jisho::godan` e `jisho::jlpt_n5`.

### Conjugação

Verbos: 13 formas (辞書形 … 命令形), com o grupo decidido pela tag do JMdict e não pela terminação (帰る é godan).
Cobre 行く, ある, 問う, する, 来る (com a leitura de cada forma), verbos com する e honoríficos
(くださる, いらっしゃる, おっしゃる, なさる). Adjetivos い e な têm tabela própria. A tabela é recolhível.

## Limitações conhecidas

- **Significados em inglês.** O JMdict não tem português; as traduções das frases também ficam em inglês (o
  Tatoeba tem poucas em português, e essas aparecem no lugar quando existem). Os significados dos kanji
  isolados vêm em português do KANJIDIC2 quando há.
- **Voz.** O áudio vem do serviço de voz do Edge e, se falhar, do Google Tradutor. São serviços de terceiros, sem
  garantia de funcionamento, e o texto da nota é enviado a eles. Sem internet a nota fica sem áudio.
- **Áudio da frase.** É um player `<audio>` no verso, que não toca sozinho. O da palavra toca na frente.
- **JLPT.** O KANJIDIC2 usa a escala antiga de 4 níveis; só os níveis 4 e 3 casam com N5 e N4.
- **Editor experimental.** O editor novo do Anki (SvelteKit, atrás de um experimento) não expõe a nota ao addon;
  nele, use o preenchimento em lote do navegador.
- **Template.** O Jisho Card atualiza o CSS e os templates do tipo de nota quando o addon muda de versão. Edições
  suas nos templates serão perdidas ao atualizar; campos que você acrescentar são preservados.
- **Sem tabela de conjugação:** verbos arcaicos (nidan, yodan), 得る (`v5uru`) e ずる.

## Desenvolvimento

```text
addon/                 o addon (vira o .ankiaddon)
  fill.py              monta os campos de uma nota (usa lookup, furigana, pos, render, conjugate, stroke_svg)
  batch.py, browser.py preenchimento em lote
  editor.py            botões 辞/再, Ctrl+Shift+J, preenchimento ao sair do campo
  tts/                 vozes (edge.py, gtts.py) e um cliente WebSocket próprio (ws.py)
  vendor/              Janome, gTTS e uma cópia mínima do edge-tts (LGPL)
tools/                 build_db.py, build_fonts.py, package.py, install_dev.py, preview.py, strokes_frames.py
tests/                 pytest
```

```text
pip install pytest anki==26.8.1 aqt==26.8.1 fonttools brotli
python tools/setup_vendor.py       # Janome e gTTS em addon/vendor (não versionados)
python tools/build_db.py           # gera build/dicionario.sqlite (necessário para vários testes)
python -m pytest tests             # JISHO_LIVE=1 também testa o Edge e o gTTS de verdade (usa a internet)
python tools/preview.py --shots    # capturas dos cartões (claro/escuro, desktop/celular), precisa do Edge
python tools/strokes_frames.py     # quadros congelados da animação dos traços
```

Se a Microsoft mudar o protocolo do serviço de voz, atualize `addon/vendor/edge_tts` com a versão nova do
[edge-tts](https://github.com/rany2/edge-tts) (`constants.py` e `drm.py`).

## Licenças

JMdict e KANJIDIC2 (EDRDG, CC BY-SA 4.0), KanjiVG (CC BY-SA 3.0), Tatoeba (CC BY 2.0 FR), Janome (Apache 2.0),
edge-tts (LGPL-3.0), gTTS (MIT), Shippori Mincho e Literata (SIL OFL 1.1). Detalhes e atribuições em
[addon/LICENSES.md](addon/LICENSES.md).
