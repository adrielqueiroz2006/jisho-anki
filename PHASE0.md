# Fase 0: planejamento e riscos (aprovado)

Data: 2026-10-15. Aprovado pelo usuário, com a decisão do SVG animado abaixo.

## Versões conferidas

| Item | Versão atual | Observação |
| --- | --- | --- |
| Anki | 26.09.3 | `pyproject` do Anki pede Python >= 3.12. Data da release não confirmada. |
| jmdict-simplified | 3.6.2+20261012 | JMdict 218.898 entradas (115 MB JSON); versão com exemplos 69 MB; Kanjidic 15 MB com en, es, fr e pt. |
| KanjiVG | r20260714 | |
| Tatoeba | exports semanais | CC BY 2.0 FR. Pares por idioma saem da ferramenta de exportação. |
| Janome | 0.5.0 (jul/2023) | Wheel 19,65 MB, Apache 2.0, Python puro. Projeto parado. |
| edge-tts | 7.3.1 (13/out/2026) | LGPL-3. Depende de aiohttp, certifi, tabulate e typing-extensions. |
| gTTS | 2.5.4 (nov/2024) | Depende de requests e click. |

Confirmado na Fase 2, no Anki instalado (26.8.1, Python 3.13): **não há Pillow, aiohttp nem websockets** embutidos; há `requests`, `click`, `certifi`, `PyQt6` e `typing_extensions`. Não confirmado: limites de mídia do AnkiWeb.

## Decisões do usuário

1. Ajustes de risco abaixo: aprovados.
2. **Traços: SVG animado colorido**, não GIF. O traço sendo desenhado aparece em **rosa**; os traços já feitos ficam numa cor legível no claro e no escuro (via `.nightMode`). Sem GIF e sem versão dupla de mídia. PNG estático numerado continua opcional para impressão.
3. Este relatório salvo como `PHASE0.md`.

4. (Fase 1, 2026-10-15) **Significados e traduções das frases ficam em inglês.** Sem tradução para português: `translate.py`, a opção `traducao_pt` e a chave de API saem do escopo. A tela de config da Fase 7 perde "idioma do significado" e "chave de API". Os significados em português do KANJIDIC2 para kanji isolado continuam, a menos que o usuário peça o contrário.

## Ajustes aprovados

1. edge-tts depende de aiohttp (extensões nativas). Teste curto no início da Fase 4; se falhar, cliente WebSocket mínimo. Fallback de áudio: edge-tts, gTTS, `{{tts}}`.
2. Animação dos traços: SVG com CSS animation direto no campo. Paths do KanjiVG usados no próprio SVG, sem dependência de Qt ou Pillow. Gravado no campo `Traços`, sem mídia.
3. Frase de exemplo: usar exemplos ligados às entradas do `jmdict-examples`, cruzados com Tatoeba para português, no `build_db`. Janome só para furigana.
4. Conjugação: tags `v5aru`, `vk` e `vs-*`; conjugar sempre o final (する/来る); forma escrita e leitura em paralelo com furigana alinhado.
5. Nunca sobrescrever: preencher só campos vazios. "Regerar" substitui tudo menos `Notas`, com confirmação.
6. Banco: release no GitHub, compactado e com checksum; download com progresso e retomada; guardado em `user_files`; aviso claro se offline.
7. Janome carregado só quando necessário; medir memória e tempo no Anki real.
8. Fontes: no máximo 2 pesos, com fallback para fonte do sistema.
9. Licenças: banco publicado sob CC BY-SA; KanjiVG (CC BY-SA 3.0) com atribuição separada e compatibilidade a conferir; `LICENSES.md` por fonte.
10. Normalizar formas flexionadas digitadas (食べます) para a forma de dicionário com o Janome, pedindo confirmação.
11. Verificar glosas em português no JMdict na Fase 1 e usar quando existirem.

5. (Fase 3, 2026-10-15) **Adjetivos い e な também terão tabela de conjugação** (antes estavam fora do escopo), além da tabela de 13 formas dos verbos. Entra na Fase 6, junto com `conjugate.py`; o campo `Conjugação` e o `<details>` do template já servem para os dois.
