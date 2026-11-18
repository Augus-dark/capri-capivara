# Capri

Assistente virtual para Windows, feita por Augusto. A Capri conversa em português, por texto ou voz, e executa o que você pedir no computador.

## O que ela faz

- Abre programas, sites, pastas e arquivos
- Controla volume, música, brilho, tema, energia e papel de parede
- Usa mouse e teclado quando você autoriza
- Lê e altera configurações do Windows
- Mostra CPU, memória, disco e rede
- Tira print, cria notas e guarda o que você pedir para lembrar
- Fecha programa, desliga ou reinicia só depois da sua confirmação

Ações perigosas, como apagar a Lixeira, mexer no Registro ou rodar um comando, sempre pedem permissão.

## Requisitos

- Windows 10 ou 11
- Python 3.10 ou mais novo
- Uma chave de API do Groq

## Instalação

```bash
python -m pip install customtkinter psutil pillow groq edge-tts playsound==1.2.2 SpeechRecognition sounddevice numpy
python capri_app.py
