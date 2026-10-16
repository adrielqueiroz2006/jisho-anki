# Plano de ação: Addon de Japonês para Anki (Claude Code)

Oct 15, 2026 · @Adriel Queiroz

## Como usar este plano com o Claude Code

Este documento é a especificação completa; o Claude Code deve executá-lo fase por fase, parando para você testar no Anki ao fim de cada uma.

1. Crie uma pasta vazia, por exemplo `anki-jp-dicionario/`, e salve este plano lá como `PLAN.md` (exporte o doc como Markdown).
2. Abra o Claude Code nessa pasta e cole o prompt da última seção.
3. Peça para ele usar o modo de planejamento (Shift+Tab duas vezes) na Fase 0, revise o plano dele e só então libere a execução.
4. Ao fim de cada fase, instale o addon no Anki (ele vai gerar um `.ankiaddon` ou um link simbólico para a pasta de addons) e teste com as palavras da seção de testes.
5. Se algo ficar feio ou errado, descreva o problema com um print; ele corrige antes de avançar.

Requisitos na sua máquina: Anki 24.11 ou mais recente (desktop), Python 3.9+ para os scripts de build e internet na primeira execução (para baixar os dicionários e gerar áudio).

## Objetivo e visão geral

O entregável é um addon do Anki chamado **Jisho Card (辞書カード)** que cria um note type próprio e preenche o verso automaticamente a partir de um dicionário offline, assim que você digita a palavra.

**Fluxo do usuário:**

1. No Anki, você clica em Adicionar e escolhe o note type `Jisho Card`.
2. Digita só o kanji ou a palavra no campo da frente (ex.: `食べる`).
3. Ao sair do campo, ou ao clicar no botão **辞** da barra do editor (atalho Ctrl+Shift+J), o addon preenche todos os outros campos: leituras, classe gramatical, significado, frase de exemplo com tradução, áudios, GIF de traços e tabela de conjugação.
4. Se a palavra tiver mais de uma entrada no dicionário (ex.: `生`, `上手`), abre uma janela para você escolher a acepção certa.
5. Você revisa, edita o que quiser e salva.

**Princípios que o Claude Code deve respeitar:**

- **Tudo fica gravado nos campos.** O HTML, os áudios e os GIFs são gerados uma vez e salvos na coleção. Assim o card funciona no AnkiDroid, no AnkiMobile e no AnkiWeb, onde o addon não roda.
- **Offline primeiro.** Dicionário, leituras, traços e frases de exemplo vêm de bases locais em SQLite. Só o áudio e a tradução opcional para português usam internet.
- **Nunca sobrescrever edição manual.** Campo já preenchido só é substituído se você pedir (botão "Regerar" ou opção na config).
- **Preenchimento em lote.** No navegador de cards, um menu permite preencher várias notas selecionadas de uma vez.
- **Aparência de verbete de dicionário**, legível no claro, no escuro e no celular.

## Decisões técnicas

A regra geral: dados abertos convertidos para um único `dicionario.sqlite`, baixado na primeira execução (não embutido no pacote, para não estourar o limite do AnkiWeb).

| Informação | Solução | Fonte e licença |
| --- | --- | --- |
| Palavra, leitura, classe gramatical, significado | JMdict (versão JSON do projeto jmdict-simplified) | EDRDG, CC BY-SA 4.0 |
| Kunyomi, onyomi, nº de traços, radical, JLPT, série escolar | KANJIDIC2 (inclui significados em português para muitos kanji) | EDRDG, CC BY-SA 4.0 |
| Ordem dos traços | SVGs do KanjiVG, animados e convertidos em GIF dentro do addon | KanjiVG, CC BY-SA 3.0 |
| Frase de exemplo + tradução | Tatoeba, pares japonês–português; se não houver, japonês–inglês | Tatoeba, CC BY 2.0 FR |
| Furigana da frase | Janome (tokenizador em Python puro, com IPADIC embutido) | Apache 2.0 |
| Áudio da palavra e da frase | edge-tts (vozes neurais `ja-JP-NanamiNeural` e `ja-JP-KeitaNeural`), com gTTS como reserva | Requer internet |

**Leituras em hiragana.** KANJIDIC2 traz onyomi em katakana; converter com deslocamento Unicode (katakana U+30A1–U+30F6 menos 0x60 = hiragana), preservando `ー`. Kunyomi vem com ponto separando o okurigana (`た.べる`): exibir a raiz em destaque e o okurigana em cinza claro (た**べる**). Ambas as leituras ficam numa opção da config (`onyomi_script: "hiragana" | "katakana"`), com hiragana como padrão.

**Significado em português.** O JMdict não tem glosas em português. Padrão: mostrar as glosas em inglês. Opcional (config `traducao_pt`): traduzir as glosas e a frase de exemplo para português via API (Claude API ou DeepL, chave do próprio usuário), com cache local para não pagar duas vezes pela mesma palavra. Para kanji isolado, usar primeiro os significados em português do KANJIDIC2.

**Áudio.** Gerar `.mp3` no momento do preenchimento, salvar em `collection.media` com nome determinístico (`jisho_<hash>.mp3`) e gravar `[sound:...]` no campo. Fallback no template: `{{tts ja_JP:Palavra}}` quando o campo de áudio estiver vazio. Arquitetura com backends plugáveis (`tts/edge.py`, `tts/gtts.py`) para trocar de voz depois. O addon deve tocar o áudio da palavra automaticamente na frente e deixar o da frase num botão.

**GIF de traços.** Gerado sob demanda, um por kanji da palavra:

- Ler o SVG do KanjiVG do kanji (código Unicode em hex, 5 dígitos).
- Renderizar quadro a quadro com `QSvgRenderer` + `QPainter` do próprio Qt do Anki: traços já feitos em cinza escuro, traço atual em vermelho sendo desenhado (8 a 12 quadros por traço via `stroke-dashoffset`), números dos traços pequenos ao lado.
- Codificar o GIF com Pillow se estiver disponível; senão, com um codificador GIF/LZW em Python puro incluído no addon (paleta de 4 cores basta).
- 200×200 px, fundo transparente ou papel, grade guia pontilhada em cruz (como caderno de caligrafia), pausa de 1,5 s no final antes de repetir.
- Também gerar uma imagem estática PNG "todos os traços numerados", útil para impressão.

**Compatibilidade.** Anki 24.11+ (Qt6). Nada de dependências com extensão nativa além do que o Anki já traz; bibliotecas puras vão em `vendor/`. O Claude Code deve conferir as versões atuais de cada biblioteca antes de fixar.

## Campos do note type

O note type `Jisho Card` tem 16 campos; você só digita o primeiro, o resto é preenchido pelo addon e pode ser editado à mão.

| # | Campo | Conteúdo | Exemplo (食べる) |
| --- | --- | --- | --- |
| 1 | Palavra | O que você digita | 食べる |
| 2 | Leitura | Leitura da palavra inteira em hiragana | たべる |
| 3 | Furigana | Palavra com ruby no formato do Anki | 食\[た\]べる |
| 4 | ÁudioPalavra | `[sound:...]` gerado | \[sound:jisho\_a1b2.mp3\] |
| 5 | ClasseGramatical | Rótulo em português + tag técnica | Verbo ichidan, transitivo (v1, vt) |
| 6 | Significado | Lista numerada de acepções | 1. comer 2. viver de |
| 7 | KanjiInfo | HTML de um bloco por kanji: kun, on, traços, radical, JLPT | 食 · kun: た・べる, く・う · on: しょく, じき |
| 8 | Kunyomi | Só as leituras kun em hiragana (para busca/filtros) | た.べる、く.う |
| 9 | Onyomi | Só as leituras on em hiragana | しょく、じき |
| 10 | Exemplo | Frase em japonês | 毎朝パンを食べます。 |
| 11 | ExemploFurigana | Frase com ruby, palavra-alvo destacada | 毎朝\[まいあさ\]パンを\<b>食\[た\]べます\</b>。 |
| 12 | ExemploTradução | Tradução (pt, ou en de reserva) | Como pão todas as manhãs. |
| 13 | ExemploÁudio | `[sound:...]` da frase | \[sound:jisho\_c3d4.mp3\] |
| 14 | Traços | `<img>` dos GIFs, um por kanji | \<img src="jisho\_stroke\_98df.gif"> |
| 15 | Conjugação | Tabela HTML pronta (vazia se não for verbo) | ver seção das conjugações |
| 16 | Notas | Livre, para suas anotações | — |

Tags automáticas na nota: `jisho::verbo`, `jisho::jlpt_n5`, `jisho::godan` etc., para criar decks filtrados.

## Design do card: verbete de dicionário

A referência visual é um dicionário impresso japonês (estilo 広辞苑 / 大辞林): tipografia serifada, hierarquia clara, muito espaço em branco e cor só para destaque.

**Frente:** a palavra grande e centralizada (fonte mincho, \~72px), botão de áudio discreto abaixo, áudio tocando sozinho ao abrir. Nada mais na frente.

**Verso (de cima para baixo):**

```text
┌──────────────────────────────────────────────┐
│  たべる                         [▶ áudio]      │
│  食べる                     (cabeçalho grande) │
│  ─────────────────────────────────────────── │
│  【動・一段・他】 Verbo ichidan, transitivo      │
│                                              │
│  ❶ comer                                     │
│  ❷ viver de, sustentar-se                    │
│                                              │
│  ┌ 漢字 ─────────────────────────────────┐   │
│  │ 食   [GIF traços]  訓 た・べる  く・う   │   │
│  │      9画 · 部首 食 · N5    音 しょく  じき │   │
│  └──────────────────────────────────────┘   │
│                                              │
│  ┌ 例文 ──────────────────────── [▶] ─┐     │
│  │ まいあさ        た                    │     │
│  │ 毎朝パンを【食べます】。               │     │
│  │ Como pão todas as manhãs.             │     │
│  └──────────────────────────────────────┘   │
│                                              │
│  ▸ 活用 Conjugação (tabela, recolhível)        │
└──────────────────────────────────────────────┘
```

**Especificações visuais:**

- **Fontes:** Shippori Mincho ou Noto Serif JP para japonês; Noto Serif ou Literata para português. Embutir os arquivos em `collection.media` com prefixo `_` (ex.: `_ShipporiMincho.woff2`) para sincronizar com o celular e não serem apagados pela verificação de mídia.
- **Paleta:** fundo cor de papel (#FBF8F1), texto quase preto (#1F1B16), vermelho-carimbo (#B7282E) para rótulos 訓/音/例文 e para o traço atual do GIF, cinza (#8A8178) para okurigana e notas.
- **Rótulos 訓 e 音** em selos pequenos (quadradinho com borda vermelha), como nos dicionários de kanji.
- **Classe gramatical** entre colchetes 【 】 abreviada em japonês + versão por extenso em português.
- **Acepções** numeradas com ❶ ❷ ❸.
- **Frase de exemplo** com `<ruby>` (furigana só nos kanji), palavra-alvo sublinhada ou em negrito vermelho, tradução em itálico logo abaixo.
- **GIF de traços** num quadro com grade guia; para palavras com vários kanji, um bloco por kanji lado a lado (quebra de linha no celular).
- **Tabela de conjugação** recolhível (`<details>`), fechada por padrão, para o verso não ficar longo demais.
- **Modo noturno:** classe `.nightMode` do Anki com fundo #1C1A17, texto #EDE6DA, vermelho suavizado (#E0645A); o GIF precisa de fundo transparente ou de uma versão clara.
- **Responsivo:** largura máxima \~640px no desktop; no celular, os blocos empilham e a fonte do cabeçalho cai para \~48px.
- **Palavra só em kana** (ex.: きれい): o bloco 漢字 some automaticamente (`{{#KanjiInfo}}`).

## Tabela das 13 conjugações

Quando a classe gramatical for verbo, o verso mostra estas 13 formas, cada uma com furigana e uma explicação curta de uso. A lista abaixo é a proposta; troque qualquer linha antes de passar ao Claude Code.

| # | Forma | 食べる (ichidan) | 書く (godan) | Uso |
| --- | --- | --- | --- | --- |
| 1 | 辞書形 dicionário | 食べる | 書く | forma básica, informal |
| 2 | ます形 polida | 食べます | 書きます | presente/futuro educado |
| 3 | ない形 negativa | 食べない | 書かない | "não come" |
| 4 | た形 passado | 食べた | 書いた | "comeu" |
| 5 | なかった形 passado negativo | 食べなかった | 書かなかった | "não comeu" |
| 6 | て形 conectiva | 食べて | 書いて | ligar frases, pedidos, ～ている |
| 7 | 意向形 volitiva | 食べよう | 書こう | "vamos comer", intenção |
| 8 | 可能形 potencial | 食べられる | 書ける | "conseguir comer" |
| 9 | 受身形 passiva | 食べられる | 書かれる | "ser comido" |
| 10 | 使役形 causativa | 食べさせる | 書かせる | "fazer/deixar comer" |
| 11 | 使役受身形 causativa-passiva | 食べさせられる | 書かされる | "ser obrigado a comer" |
| 12 | 仮定形 condicional ば | 食べれば | 書けば | "se comer" |
| 13 | 命令形 imperativa | 食べろ | 書け | ordem direta |

**Regras que o motor de conjugação precisa cobrir** (em `conjugate.py`, com testes unitários):

- Usar a tag do JMdict para decidir o grupo, nunca a terminação: 帰る, 入る, 走る, 知る, 切る parecem ichidan mas são godan (`v5r`).
- Todos os godan: う つ る → って/った; む ぶ ぬ → んで/んだ; く → いて; ぐ → いで; す → して.
- Exceções: 行く → 行って/行った (`v5k-s`); ある → negativa ない (`v5r-i`); 問う → 問うて; する e 来る totalmente irregulares; 来る mostra a leitura de cada forma (こない, きた, こよう, こられる).
- Verbos com する (勉強する, `vs`): conjugar só o する e manter o substantivo; potencial vira できる.
- Honoríficos (くださる, いらっしゃる, おっしゃる, なさる): ます形 com い (くださいます) e imperativo ください/いらっしゃい.
- Causativa-passiva godan: forma curta (書かされる) como principal, forma longa (書かせられる) em cinza; para verbos em す só a longa (話させられる).
- Linhas 8 e 9 iguais no ichidan: marcar com uma nota pequena "mesma forma, contexto decide".
- Adjetivos い e な: fora do escopo agora; deixar a função preparada para uma tabela própria depois.

## Fases de implementação

São 8 fases; cada uma termina com algo testável no Anki e só avança depois do seu "ok".

**Estrutura de pastas esperada:**

```text
anki-jp-dicionario/
├── PLAN.md
├── addon/                  # vira o .ankiaddon
│   ├── __init__.py         # hooks do Anki
│   ├── manifest.json, config.json, config.md
│   ├── notetype.py         # cria/atualiza o note type
│   ├── editor.py           # botão 辞, atalho, preenchimento ao sair do campo
│   ├── browser.py          # preenchimento em lote
│   ├── lookup.py           # consultas ao SQLite
│   ├── kana.py             # katakana→hiragana, okurigana
│   ├── conjugate.py        # 13 formas
│   ├── furigana.py         # Janome → ruby
│   ├── stroke_gif.py       # KanjiVG → GIF
│   ├── tts/ (edge.py, gtts.py)
│   ├── translate.py        # opcional, pt-BR
│   ├── templates/ (front.html, back.html, style.css)
│   ├── fonts/  vendor/  LICENSES.md
├── tools/build_db.py       # gera dicionario.sqlite
└── tests/
```

1. **Fase 0 — Planejamento.** Ler este plano, verificar versões atuais das bibliotecas e da API de addons do Anki, apontar riscos e propor ajustes. Critério: plano revisado aprovado por você.
2. **Fase 1 — Banco de dados.** `tools/build_db.py` baixa JMdict, KANJIDIC2, KanjiVG e Tatoeba (jpn+por+eng), e gera `dicionario.sqlite` com índices por kanji, kana e leitura. Critério: consultar 食べる, 日本, 水, きれい e 生 em menos de 50 ms cada; arquivo publicado como release no GitHub para download na primeira execução.
3. **Fase 2 — Note type e templates estáticos.** Criar o note type com os 16 campos, frente, verso e CSS conforme o design. Critério: uma nota preenchida à mão fica bonita no desktop, no modo noturno e no AnkiDroid/AnkiMobile.
4. **Fase 3 — Preenchimento automático.** Botão 辞, Ctrl+Shift+J, preenchimento ao sair do campo Palavra, janela de escolha para homógrafos, leituras em hiragana, classe gramatical em português, significados, frase de exemplo com furigana e tradução. Critério: todas as palavras de teste preenchem sem erro.
5. **Fase 4 — Áudio.** TTS da palavra e da frase, cache por hash, fallback gTTS e `{{tts}}`. Critério: áudio toca no desktop e no celular após sincronizar.
6. **Fase 5 — GIF de traços.** Animação a partir do KanjiVG, com grade, cores do design e versão clara/escura. Critério: GIFs corretos para 食, 書, 日, 水, 必 (ordem de traços difícil) e 鬱 (muitos traços).
7. **Fase 6 — Conjugação.** `conjugate.py` com testes cobrindo todas as regras; tabela HTML recolhível no verso. Critério: 100% dos testes de conjugação passam.
8. **Fase 7 — Lote, configuração e acabamento.** Menu no navegador para preencher notas selecionadas com barra de progresso; tela de config (voz, hiragana/katakana, idioma do significado, chave de API, sobrescrever ou não); tratamento de erro sem travar o Anki (sem internet, palavra inexistente); `LICENSES.md` com as atribuições; empacotar `.ankiaddon` e README em português.

## Testes e palavras de validação

Estas 20 entradas cobrem os casos difíceis; o Claude Code deve criar um deck de teste com todas e você confere visualmente.

| Palavra | O que testa |
| --- | --- |
| 食べる | ichidan, transitivo, caso base |
| 書く | godan く |
| 泳ぐ | godan ぐ |
| 話す | godan す, causativa-passiva longa |
| 待つ | godan つ |
| 死ぬ | godan ぬ |
| 遊ぶ | godan ぶ |
| 帰る | godan com cara de ichidan |
| 行く | exceção 行って |
| ある | negativa ない |
| する | irregular |
| 来る | irregular com mudança de leitura |
| 勉強する | verbo com する |
| いらっしゃる | honorífico |
| 日本 | substantivo, dois kanji, leitura especial |
| 水 | kanji isolado, significado em pt do KANJIDIC2 |
| 生 | muitas leituras, janela de escolha |
| きれい | só kana, adjetivo な, sem bloco de kanji |
| 必ず | ordem de traços pouco intuitiva |
| 鬱 | 29 traços, GIF longo |

**Testes automáticos** (`pytest`, rodando fora do Anki): conversão kana, divisão de okurigana, as 13 formas para cada verbo acima comparadas com respostas fixas, geração de furigana da frase e geração de GIF (número de quadros = traços × quadros por traço + pausa).

## Prompt pronto para colar no Claude Code

Cole o texto abaixo na primeira mensagem, com o `PLAN.md` já salvo na pasta.

```text
Você vai construir um addon do Anki chamado "Jisho Card (辞書カード)" para estudar japonês.
A especificação completa está em PLAN.md nesta pasta. Leia o arquivo inteiro antes de qualquer coisa.

Como trabalhar:
- Responda e comente o código em português do Brasil.
- Execute uma fase por vez, na ordem do PLAN.md. Ao fim de cada fase: rode os testes, me diga
  exatamente como instalar/testar no Anki e PARE esperando meu "ok" antes da próxima.
- Comece pela Fase 0 em modo de planejamento: confira as versões atuais da API de addons do Anki
  (24.11+, Qt6), do jmdict-simplified, KANJIDIC2, KanjiVG, Tatoeba, Janome e edge-tts; aponte
  riscos (tamanho do banco, limites do AnkiWeb, dependências nativas) e proponha ajustes.
- Nada de dependências com extensão nativa além das que o Anki já traz; bibliotecas puras em vendor/.
- Todo conteúdo gerado (HTML, áudio, GIF) deve ser gravado nos campos/mídia da nota, para funcionar
  no AnkiDroid e AnkiMobile sem o addon.
- Nunca sobrescreva um campo que eu editei, a menos que eu clique em "Regerar".
- Onyomi e kunyomi SEMPRE em hiragana por padrão (configurável).
- O verso tem que parecer um verbete de dicionário japonês impresso: siga à risca a seção de design,
  incluindo modo noturno e layout de celular. Mostre prints/HTML de pré-visualização para eu aprovar.
- A tabela de conjugação tem exatamente as 13 formas do PLAN.md e usa a tag do JMdict para o grupo do verbo.
- Escreva testes pytest para kana, okurigana, conjugação, furigana e GIF.
- Inclua LICENSES.md com as atribuições de JMdict/KANJIDIC2 (CC BY-SA 4.0), KanjiVG (CC BY-SA 3.0)
  e Tatoeba (CC BY 2.0 FR).

Comece agora pela Fase 0.
```

Dica: se o contexto do Claude Code ficar longo entre fases, abra uma sessão nova e diga "Leia PLAN.md e continue da Fase N"; o plano é autossuficiente para isso.
