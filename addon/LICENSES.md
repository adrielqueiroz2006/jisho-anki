# Licenças e atribuições

O código deste addon é do autor do projeto. Os dados e as fontes abaixo têm licenças próprias.

| Material | Fonte | Licença |
| --- | --- | --- |
| Dicionário (palavras, leituras, classes gramaticais, significados) | [JMdict](https://www.edrdg.org/jmdict/j_jmdict.html), do EDRDG, na versão JSON do projeto [jmdict-simplified](https://github.com/scriptin/jmdict-simplified) | CC BY-SA 4.0 |
| Kanji (leituras, traços, radical, JLPT, significados) | [KANJIDIC2](https://www.edrdg.org/wiki/index.php/KANJIDIC_Project), do EDRDG | CC BY-SA 4.0 |
| Ordem dos traços | [KanjiVG](https://kanjivg.tagaini.net), de Ulrich Apel e colaboradores | CC BY-SA 3.0 |
| Frases de exemplo e traduções | [Tatoeba](https://tatoeba.org) e seus colaboradores | CC BY 2.0 FR |
| Furigana das frases | [Janome](https://github.com/mocobeta/janome) (com o dicionário MeCab-IPADIC embutido), em `vendor/` | Apache 2.0 (Janome); licença própria do IPADIC |
| Voz (áudio da palavra e da frase) | Serviço de voz neural do Microsoft Edge (não oficial), acessado com um cliente próprio; constantes e token vêm de uma cópia mínima do [edge-tts](https://github.com/rany2/edge-tts) 7.3.1 em `vendor/edge_tts/` (`drm.py` alterado só para não exigir o aiohttp) | LGPL-3.0 (edge-tts, texto em `vendor/edge_tts/LICENSE`) |
| Voz de reserva | [gTTS](https://github.com/pndurette/gTTS) 2.5.4, em `vendor/gtts/` (Google Tradutor) | MIT |
| Fonte Shippori Mincho | Fontworks / Shippori Mincho Project, via Google Fonts (versão reduzida) | SIL OFL 1.1 (`fonts/OFL-ShipporiMincho.txt`) |
| Fonte Literata | TypeTogether, via Google Fonts (versão reduzida, só latim) | SIL OFL 1.1 (`fonts/OFL-Literata.txt`) |

O arquivo `dicionario.sqlite`, que o addon baixa ou que você escolhe nas configurações, é derivado de JMdict, KANJIDIC2, KanjiVG e Tatoeba e deve ser redistribuído mantendo estas atribuições (e a licença CC BY-SA nos trechos derivados dos dados do EDRDG e do KanjiVG).

Os serviços de voz são de terceiros, sem garantia de funcionamento: o addon tenta o Edge, depois o gTTS, e segue sem áudio se ambos falharem. O texto das notas é enviado a esses serviços para gerar a voz.
