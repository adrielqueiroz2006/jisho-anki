# Jisho Card (辞書カード)

O jeito mais fácil de mudar tudo isto é **Ferramentas › Jisho Card › Configurações**.

- `onyomi_script`: `"hiragana"` (padrão) ou `"katakana"`. Escrita das leituras onyomi.
- `auto_preencher`: `true` preenche a nota ao sair do campo Palavra (só em nota nova e vazia).
  Com `false`, use o botão 辞 ou Ctrl+Shift+J.
- `max_acepcoes`: quantas acepções do dicionário vão para o campo Significado.
- `gerar_audio`: `true` gera o áudio da palavra e da frase ao preencher (precisa de internet). `false` desliga.
- `tts_voice`: voz do Edge: `"ja-JP-NanamiNeural"` (feminina, padrão) ou `"ja-JP-KeitaNeural"` (masculina).
- `tts_backends`: ordem de tentativa dos serviços de voz: `"edge"` (vozes neurais) e `"gtts"` (reserva, Google Tradutor).
- `lote_sobrescrever`: `false` (padrão): o preenchimento em lote só preenche campos vazios. `true` substitui os campos
  gerados. O item “Regerar notas selecionadas” do navegador sempre substitui.
- `perguntar_download`: `true` oferece baixar o dicionário ao abrir o Anki quando ele não está instalado. Vira `false`
  sozinho se você responder “Não”.
- `db_url`: endereço do `dicionario.sqlite.xz` (release do GitHub); usado por Ferramentas › Jisho Card › Baixar dicionário.
- `db_path`: caminho de um `dicionario.sqlite` já existente; tem prioridade sobre o baixado.
