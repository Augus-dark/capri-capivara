import asyncio, ctypes, os, json, queue, re, shutil, subprocess, tempfile, threading, time, webbrowser, datetime, winreg, sys, base64, io
from pathlib import Path
from urllib.parse import quote_plus

try:
    import customtkinter as ctk
    import tkinter as tk
    from tkinter import messagebox
    import edge_tts, psutil
    import sounddevice as sd
    import speech_recognition as sr
    from playsound import playsound
    from PIL import Image, ImageDraw, ImageGrab
    from groq import Groq
except ImportError as e:
    try:
        (Path.home() / "capri_erro.txt").write_text(
            f"Falta instalar a biblioteca: {e.name}\n"
            "Rode no cmd: python -m pip install customtkinter psutil pillow groq edge-tts "
            "playsound==1.2.2 SpeechRecognition sounddevice numpy\n", encoding="utf-8")
    except Exception:
        pass
    print("Falta instalar uma biblioteca:", e.name)
    print("Rode este comando no cmd e depois abra a Capri de novo:")
    print("python -m pip install customtkinter psutil pillow groq edge-tts playsound==1.2.2 SpeechRecognition sounddevice numpy")
    try:
        input("\nAperte Enter para fechar...")
    except Exception:
        pass
    raise SystemExit

MODELO = "openai/gpt-oss-20b"
# modelos com visão no Groq (a lista muda com o tempo; confira em console.groq.com/docs/vision)
VISAO_CANDIDATOS = ["qwen/qwen3.8-27b"]
CRIADOR_PADRAO = "Augusto"  # nome inicial do criador (dá para mudar no botão "👤 Criador")
PERSONA = ("Você é a Capri, uma assistente virtual simpática que controla o computador do usuário (Windows). "
           "Responda em português, de forma curta. Use as ferramentas quando o usuário pedir para fazer algo no PC. "
           "Para configurações do Windows, prefira as ferramentas específicas (tema, volume, energia, papel de parede, "
           "abrir_configuracao...); use registro_escrever, executar_powershell ou executar_comando só quando nenhuma "
           "outra servir. Depois de mudar uma configuração, diga o que mudou. "
           "Você só enxerga a tela quando usa ver_tela (ou quando o modo 👁 Tela está ligado). Use ver_tela sempre que "
           "precisar saber o que há na tela. Você NÃO consegue medir coordenadas exatas olhando a imagem, então prefira "
           "atalhos de teclado a cliques. O texto digitado vai para a janela ativa. "
           "Se aparecerem senhas ou dados sensíveis na tela, não repita nem guarde. "
           "Nunca digite senhas e nunca guarde senhas ou dados sensíveis na memória. "
           "Nunca rode comandos que apaguem arquivos ou alterem o sistema sem o usuário ter pedido isso claramente. "
           "Quando o usuário contar um fato pessoal ou uma preferência, use lembrar. "
           "Use as memórias salvas. Nunca invente que fez algo: confie no resultado das ferramentas.")

HOME = Path.home()
CONFIG = HOME / "capri_config.json"
MEMORIA = HOME / "capri_memoria.json"
PASTAS = {"desktop": HOME / "Desktop", "downloads": HOME / "Downloads",
          "documentos": HOME / "Documents", "imagens": HOME / "Pictures",
          "musicas": HOME / "Music", "videos": HOME / "Videos"}
APPS = {
    "bloco de notas": "notepad", "calculadora": "calc", "paint": "mspaint",
    "explorador de arquivos": "explorer", "gerenciador de tarefas": "taskmgr",
    "prompt de comando": "cmd", "powershell": "powershell", "terminal": "wt",
    "configuracoes": "ms-settings:", "navegador padrão": "",
    "chrome": "chrome", "edge": "msedge", "firefox": "firefox",
    "discord": "discord", "spotify": "spotify", "steam": "steam",
    "whatsapp": "whatsapp:", "telegram": "telegram", "vscode": "code",
    "word": "winword", "excel": "excel", "powerpoint": "powerpnt",
    "vlc": "vlc", "obs": "obs64", "afterburner": "msiafterburner",
    "nvidia": "nvcplui", "captura de tela": "snippingtool",
    "loja": "ms-windows-store:", "camera": "microsoft.windows.camera:",
    "fotos": "ms-photos:", "xbox": "xbox:",
}
EXTENSOES_PERIGOSAS = {".exe", ".bat", ".cmd", ".ps1", ".vbs", ".js", ".msi", ".scr", ".com", ".jar"}
ALTERACOES_LOG = HOME / "capri_alteracoes.log"
PAGINAS_CONFIG = {
    "wifi": "ms-settings:network-wifi", "bluetooth": "ms-settings:bluetooth",
    "tela": "ms-settings:display", "som": "ms-settings:sound",
    "bateria": "ms-settings:batterysaver", "energia": "ms-settings:powersleep",
    "rede": "ms-settings:network", "vpn": "ms-settings:network-vpn",
    "proxy": "ms-settings:network-proxy", "aplicativos": "ms-settings:appsfeatures",
    "aplicativos_padrao": "ms-settings:defaultapps", "aplicativos_iniciais": "ms-settings:startupapps",
    "atualizacao": "ms-settings:windowsupdate", "privacidade": "ms-settings:privacy",
    "microfone": "ms-settings:privacy-microphone", "camera": "ms-settings:privacy-webcam",
    "personalizacao": "ms-settings:personalization", "fundo": "ms-settings:personalization-background",
    "cores": "ms-settings:colors", "armazenamento": "ms-settings:storagesense",
    "data_hora": "ms-settings:dateandtime", "idioma": "ms-settings:regionlanguage",
    "digitacao": "ms-settings:typing", "mouse": "ms-settings:mousetouchpad",
    "impressoras": "ms-settings:printers", "contas": "ms-settings:yourinfo",
    "notificacoes": "ms-settings:notifications", "acessibilidade": "ms-settings:easeofaccess",
    "sobre": "ms-settings:about", "recuperacao": "ms-settings:recovery",
}
PLANOS_ENERGIA = {
    "economia": "a1841308-3541-4fab-bc81-f71556f20b4a",
    "equilibrado": "381b4222-f694-41f0-9685-ff5bb260df2e",
    "desempenho": "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c",
}

# teclas de mídia do Windows
VK_MUDO, VK_BAIXO, VK_CIMA = 0xAD, 0xAE, 0xAF
VK_MIDIA = {"proxima": 0xB0, "anterior": 0xB1, "play_pause": 0xB3}


def tecla(vk, vezes=1):
    for _ in range(vezes):
        ctypes.windll.user32.keybd_event(vk, 0, 0, 0)
        ctypes.windll.user32.keybd_event(vk, 0, 2, 0)
        time.sleep(0.02)


ULONG_PTR = ctypes.c_ulonglong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_ulong
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", ctypes.c_ushort), ("wScan", ctypes.c_ushort),
                ("dwFlags", ctypes.c_ulong), ("time", ctypes.c_ulong),
                ("dwExtraInfo", ULONG_PTR)]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", ctypes.c_long), ("dy", ctypes.c_long),
                ("mouseData", ctypes.c_ulong), ("dwFlags", ctypes.c_ulong),
                ("time", ctypes.c_ulong), ("dwExtraInfo", ULONG_PTR)]


class INPUTUNION(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT)]


class INPUT(ctypes.Structure):
    _anonymous_ = ("u",)
    _fields_ = [("type", ctypes.c_ulong), ("u", INPUTUNION)]


def send_input(inp):
    ctypes.windll.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))


def digitar_texto(texto):
    for ch in str(texto)[:500]:
        if ch == "\r":
            continue
        if ch == "\n":
            atalho([0x0D])
            continue
        dados = ch.encode("utf-16-le")
        for i in range(0, len(dados), 2):
            u = int.from_bytes(dados[i:i + 2], "little")
            send_input(INPUT(type=1, ki=KEYBDINPUT(0, u, KEYEVENTF_UNICODE, 0, 0)))
            send_input(INPUT(type=1, ki=KEYBDINPUT(0, u, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, 0, 0)))
        time.sleep(0.01)


TECLAS = {
    "enter": 0x0D, "esc": 0x1B, "espaco": 0x20, "tab": 0x09, "backspace": 0x08,
    "delete": 0x2E, "seta_cima": 0x26, "seta_baixo": 0x28, "seta_esquerda": 0x25,
    "seta_direita": 0x27, "windows": 0x5B, "ctrl": 0x11, "alt": 0x12, "shift": 0x10,
    "f5": 0x74, "print": 0x2C,
}


def posicao_mouse():
    class POINT(ctypes.Structure):
        _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
    p = POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(p))
    return p.x, p.y


def mover_mouse(x, y):
    w = ctypes.windll.user32.GetSystemMetrics(0)
    h = ctypes.windll.user32.GetSystemMetrics(1)
    ctypes.windll.user32.SetCursorPos(max(1, min(w - 1, int(x))), max(1, min(h - 1, int(y))))


def clicar_mouse(botao="esquerdo", vezes=1):
    downs = {"esquerdo": 0x0002, "direito": 0x0008, "meio": 0x0020}
    ups = {"esquerdo": 0x0004, "direito": 0x0010, "meio": 0x0040}
    down, up = downs.get(botao, 0x0002), ups.get(botao, 0x0004)
    for _ in range(max(1, vezes)):
        ctypes.windll.user32.mouse_event(down, 0, 0, 0, 0)
        ctypes.windll.user32.mouse_event(up, 0, 0, 0, 0)
        time.sleep(0.05)


TECLAS_EXTRAS = {"win": 0x5B, "return": 0x0D, "escape": 0x1B, "space": 0x20, "del": 0x2E,
                 "up": 0x26, "down": 0x28, "left": 0x25, "right": 0x27, "home": 0x24, "end": 0x23,
                 "pageup": 0x21, "pagedown": 0x22, "control": 0x11, "printscreen": 0x2C}
TECLAS_ESTENDIDAS = {0x26, 0x28, 0x25, 0x27, 0x24, 0x23, 0x21, 0x22, 0x2E, 0x5B}


def vk_de(nome):
    n = str(nome).lower().strip()
    if n in TECLAS:
        return TECLAS[n]
    if n in TECLAS_EXTRAS:
        return TECLAS_EXTRAS[n]
    if re.fullmatch(r"f([1-9]|1[0-2])", n):
        return 0x6F + int(n[1:])
    if len(n) == 1 and n.isascii() and n.isalnum():
        return ord(n.upper())
    return None


def atalho(vks):
    for vk in vks:
        ctypes.windll.user32.keybd_event(vk, 0, 1 if vk in TECLAS_ESTENDIDAS else 0, 0)
        time.sleep(0.03)
    for vk in reversed(vks):
        ctypes.windll.user32.keybd_event(vk, 0, (1 if vk in TECLAS_ESTENDIDAS else 0) | 2, 0)
        time.sleep(0.03)


def registrar_alteracao(msg):
    try:
        with open(ALTERACOES_LOG, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.datetime.now():%d/%m/%Y %H:%M:%S}] {msg}\n")
    except Exception:
        pass


def texto_oem(b):
    return (b or b"").decode(f"cp{ctypes.windll.kernel32.GetOEMCP()}", errors="replace").strip()


def reg_dividir(caminho):
    caminho = str(caminho).strip().strip("\\")
    raiz, _, sub_chave = caminho.partition("\\")
    raiz = raiz.upper()
    hives = {"HKCU": winreg.HKEY_CURRENT_USER, "HKEY_CURRENT_USER": winreg.HKEY_CURRENT_USER,
             "HKLM": winreg.HKEY_LOCAL_MACHINE, "HKEY_LOCAL_MACHINE": winreg.HKEY_LOCAL_MACHINE}
    if raiz not in hives or not sub_chave:
        raise ValueError("Use um caminho começando por HKCU\\ ou HKLM\\.")
    return raiz, hives[raiz], sub_chave


def reg_ler(caminho, valor):
    _, hive, sub_chave = reg_dividir(caminho)
    with winreg.OpenKey(hive, sub_chave, 0, winreg.KEY_READ) as k:
        dado, _tipo = winreg.QueryValueEx(k, valor)
    return dado


def reg_bloqueado(caminho):
    p = "\\" + str(caminho).lower().strip("\\")
    if re.search(r"\\(run|runonce|runonceex|runservices)(\\|$)", p):
        return True
    return any(x in p for x in ("\\policies", "\\winlogon", "\\image file execution options",
                               "\\currentcontrolset\\services", "\\appinit_dlls", "\\lsa"))


def reg_escrever(caminho, valor, tipo, dados):
    raiz, hive, sub_chave = reg_dividir(caminho)
    if raiz not in ("HKCU", "HKEY_CURRENT_USER"):
        raise PermissionError("Só é permitido escrever em HKCU.")
    if reg_bloqueado(caminho):
        raise PermissionError("Essa área do Registro é protegida (inicialização, políticas, serviços).")
    try:
        antigo = reg_ler(caminho, valor)
    except Exception:
        antigo = None
    with winreg.CreateKeyEx(hive, sub_chave, 0, winreg.KEY_SET_VALUE) as k:
        if tipo == "numero":
            winreg.SetValueEx(k, valor, 0, winreg.REG_DWORD, int(dados))
        else:
            winreg.SetValueEx(k, valor, 0, winreg.REG_SZ, str(dados))
    registrar_alteracao(f"registro {caminho} [{valor}] = {dados!r} (antes: {antigo!r})")
    return antigo


def capturar_tela_b64(lado_max=1280):
    img = ImageGrab.grab().convert("RGB")
    img.thumbnail((lado_max, lado_max))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=70)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def ler_config():
    try:
        return json.loads(CONFIG.read_text(encoding="utf-8"))
    except Exception:
        return {}


def salvar_config(**dados):
    cfg = ler_config()
    cfg.update(dados)
    CONFIG.write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")


def carregar_memoria():
    try:
        dados = json.loads(MEMORIA.read_text(encoding="utf-8"))
        if isinstance(dados, list):
            return [str(x)[:300] for x in dados][:40]
    except Exception:
        pass
    return []


def salvar_memoria(itens):
    MEMORIA.write_text(json.dumps(itens[-40:], ensure_ascii=False, indent=2), encoding="utf-8")


def criar_atalho_desktop():
    destino = PASTAS["desktop"] / "Abrir Capri.bat"
    if getattr(sys, "frozen", False):
        destino.write_text(f'@echo off\r\nstart "" "{sys.executable}"\r\n', encoding="utf-8")
    else:
        script = Path(__file__).resolve()
        py = shutil.which("pythonw") or shutil.which("python") or "pythonw"
        destino.write_text(f'@echo off\r\nstart "" "{py}" "{script}"\r\n', encoding="utf-8")
    return destino


def janelas_abertas():
    user32 = ctypes.windll.user32
    res = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def cb(hwnd, lp):
        if user32.IsWindowVisible(hwnd):
            n = user32.GetWindowTextLengthW(hwnd)
            if n > 0:
                buf = ctypes.create_unicode_buffer(n + 1)
                user32.GetWindowTextW(hwnd, buf, n + 1)
                pid = ctypes.c_ulong()
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                try:
                    nome = psutil.Process(pid.value).name()
                except Exception:
                    nome = "?"
                res.append(f"{nome} - {buf.value}")
        return True

    user32.EnumWindows(cb, 0)
    return res


def achar_firefox():
    caminhos = [
        r"C:\Program Files\Mozilla Firefox\firefox.exe",
        r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe",
        str(HOME / "AppData" / "Local" / "Mozilla Firefox" / "firefox.exe"),
    ]
    for c in caminhos:
        if os.path.exists(c):
            return c
    return shutil.which("firefox")


FIREFOX = achar_firefox()


def abrir_url(url):
    if FIREFOX:
        subprocess.Popen([FIREFOX, url])
    else:
        webbrowser.open(url)


def ferramenta(nome, desc, props=None, obrig=None):
    return {"type": "function", "function": {
        "name": nome, "description": desc,
        "parameters": {"type": "object", "properties": props or {}, "required": obrig or []}}}


TOOLS = [
    ferramenta("abrir_programa", "Abre um programa do Windows.",
               {"nome": {"type": "string", "enum": list(APPS)}}, ["nome"]),
    ferramenta("abrir_site", "Abre um site no navegador.",
               {"url": {"type": "string"}}, ["url"]),
    ferramenta("pesquisar_web", "Pesquisa algo no Google, no navegador.",
               {"consulta": {"type": "string"}}, ["consulta"]),
    ferramenta("abrir_pasta", "Abre uma pasta do usuário no Explorador.",
               {"pasta": {"type": "string", "enum": list(PASTAS)}}, ["pasta"]),
    ferramenta("listar_arquivos", "Lista os nomes dos arquivos de uma pasta do usuário.",
               {"pasta": {"type": "string", "enum": list(PASTAS)}}, ["pasta"]),
    ferramenta("abrir_arquivo", "Abre um arquivo ou pasta pelo caminho completo.",
               {"caminho": {"type": "string"}}, ["caminho"]),
    ferramenta("volume", "Controla o volume do PC: aumentar, diminuir, mutar/desmutar ou definir um nível.",
               {"acao": {"type": "string", "enum": ["aumentar", "diminuir", "mutar", "definir"]},
                "valor": {"type": "integer",
                          "description": "Porcentagem de 0 a 100. Em aumentar/diminuir é quanto mudar (padrão 10). Em definir é o volume final."}},
               ["acao"]),
    ferramenta("controle_midia", "Controla a música ou o vídeo que está tocando.",
               {"acao": {"type": "string", "enum": ["play_pause", "proxima", "anterior"]}}, ["acao"]),
    ferramenta("listar_programas_abertos", "Lista as janelas e programas abertos agora."),
    ferramenta("fechar_programa", "Fecha um programa pelo nome do processo, como firefox.exe. Pede permissão.",
               {"processo": {"type": "string"}}, ["processo"]),
    ferramenta("info_sistema", "Mostra uso de CPU, memória e disco do PC."),
    ferramenta("hora_data", "Informa a data e a hora atuais."),
    ferramenta("criar_nota", "Salva uma anotação no arquivo Capri_notas.txt em Documentos.",
               {"texto": {"type": "string"}}, ["texto"]),
    ferramenta("tirar_print", "Tira um print da tela e salva na pasta Imagens."),
    ferramenta("bloquear_tela", "Bloqueia o computador (tela de login)."),
    ferramenta("desligar_pc", "Agenda o desligamento do PC em 60 segundos (pede permissão)."),
    ferramenta("reiniciar_pc", "Agenda a reinicialização do PC em 60 segundos (pede permissão)."),
    ferramenta("cancelar_desligamento", "Cancela um desligamento ou reinicialização agendados."),
    ferramenta("executar_comando",
               "Executa um comando do Windows (cmd) para qualquer coisa que as outras ferramentas não cobrem. "
               "Sempre pede permissão ao usuário.",
               {"comando": {"type": "string"}}, ["comando"]),
    ferramenta("mover_mouse", "Move o mouse para uma posição da tela.",
               {"x": {"type": "integer"}, "y": {"type": "integer"}}, ["x", "y"]),
    ferramenta("clicar", "Clica com o mouse. botao: esquerdo, direito ou meio.",
               {"botao": {"type": "string", "enum": ["esquerdo", "direito", "meio"]},
                "vezes": {"type": "integer"},
                "x": {"type": "integer"}, "y": {"type": "integer"}}),
    ferramenta("digitar", "Digita um texto na janela que está ativa.",
               {"texto": {"type": "string"}}, ["texto"]),
    ferramenta("apertar_tecla", "Aperta uma tecla ou um atalho, como ctrl+c, alt+f4, enter, esc.",
               {"tecla": {"type": "string"}}, ["tecla"]),
    ferramenta("posicao_mouse", "Diz onde o mouse está agora."),
    ferramenta("lembrar", "Guarda um fato curto sobre o usuário para usar depois.",
               {"fato": {"type": "string"}}, ["fato"]),
    ferramenta("esquecer", "Apaga uma memória que contenha o texto informado.",
               {"texto": {"type": "string"}}, ["texto"]),
    ferramenta("listar_memorias", "Lista o que a Capri lembra do usuário."),
    ferramenta("tamanho_tela", "Informa o tamanho da tela em pixels."),
    ferramenta("abrir_configuracao", "Abre uma página das Configurações do Windows.",
               {"pagina": {"type": "string", "enum": list(PAGINAS_CONFIG)}}, ["pagina"]),
    ferramenta("tema", "Muda o Windows para o tema claro ou escuro.",
               {"modo": {"type": "string", "enum": ["claro", "escuro"]}}, ["modo"]),
    ferramenta("papel_de_parede", "Troca o papel de parede por uma imagem (caminho completo do arquivo).",
               {"caminho": {"type": "string"}}, ["caminho"]),
    ferramenta("plano_energia", "Lista ou troca o plano de energia do Windows.",
               {"acao": {"type": "string", "enum": ["listar", "definir"]},
                "plano": {"type": "string", "enum": list(PLANOS_ENERGIA)}}, ["acao"]),
    ferramenta("tempo_tela_suspensao", "Define em quantos minutos a tela apaga ou o PC suspende por inatividade (0 = nunca).",
               {"item": {"type": "string", "enum": ["tela", "suspensao"]},
                "minutos": {"type": "integer"}}, ["item", "minutos"]),
    ferramenta("velocidade_mouse", "Ajusta a velocidade do ponteiro do mouse, de 1 (lento) a 20 (rápido). O padrão é 10.",
               {"valor": {"type": "integer"}}, ["valor"]),
    ferramenta("brilho", "Ajusta o brilho da tela de 0 a 100 (só funciona em notebooks).",
               {"valor": {"type": "integer"}}, ["valor"]),
    ferramenta("esvaziar_lixeira", "Esvazia a Lixeira (pede permissão)."),
    ferramenta("info_rede", "Mostra as conexões de rede ativas e os endereços IP."),
    ferramenta("registro_ler", "Lê um valor do Registro do Windows (caminho começando por HKCU\\ ou HKLM\\).",
               {"caminho": {"type": "string"}, "valor": {"type": "string"}}, ["caminho", "valor"]),
    ferramenta("registro_escrever",
               "Altera um valor do Registro em HKCU (pede permissão; áreas de inicialização, políticas e serviços são bloqueadas).",
               {"caminho": {"type": "string"}, "valor": {"type": "string"},
                "tipo": {"type": "string", "enum": ["texto", "numero"]},
                "dados": {"type": "string"}}, ["caminho", "valor", "tipo", "dados"]),
    ferramenta("executar_powershell",
               "Executa um comando do PowerShell para configurar o Windows. Sempre pede permissão.",
               {"comando": {"type": "string"}}, ["comando"]),
    ferramenta("ver_tela", "Tira um print da tela agora e responde uma pergunta sobre o que aparece nela "
                           "(ou descreve a tela). Pede permissão na primeira vez.",
               {"pergunta": {"type": "string"}}, []),
    ferramenta("vigiar_tela", "Vigia a tela de tempos em tempos e avisa quando acontecer algo, "
                              "como um download terminar ou uma janela aparecer.",
               {"objetivo": {"type": "string", "description": "O que deve acontecer para avisar, em forma de pergunta de sim ou não."},
                "intervalo_segundos": {"type": "integer", "description": "De 10 a 300. Padrão 15."},
                "duracao_minutos": {"type": "integer", "description": "De 1 a 60. Padrão 10."}}, ["objetivo"]),
    ferramenta("parar_vigia", "Para a vigia da tela."),
]


async def falar(texto):
    arquivo = os.path.join(tempfile.gettempdir(), "capri_app.mp3")
    await edge_tts.Communicate(texto, "pt-BR-FranciscaNeural").save(arquivo)
    playsound(arquivo)


def ouvir_voz(segundos=5):
    taxa = 16000
    audio = sd.rec(int(segundos * taxa), samplerate=taxa, channels=1, dtype="int16")
    sd.wait()
    r = sr.Recognizer()
    try:
        return r.recognize_google(sr.AudioData(audio.tobytes(), taxa, 2), language="pt-BR")
    except Exception:
        return ""


# ---------- identidade visual: calma de rio, pelagem de capivara ----------
FUNDO = "#122B2A"        # água do rio
MARGEM = "#1B3C3A"       # margem: cabeçalho e campo de texto
LINHA = "#2E5A54"        # contornos finos
LINHA_CLARA = "#3A6B64"
BOLHA_CAPRI = "#1F403C"  # fala da Capri
PELAGEM = "#8A5A34"      # fala do usuário
SOL = "#F0B84A"          # destaque: enviar, ligado, atenção
SOL_ESCURO = "#D9A23A"
TEXTO = "#EFE7D6"
SUAVE = "#8FB0A6"        # textos de apoio
PERIGO = "#C65D4B"
FONTE_UI = "Corbel"      # humanista, calma de ler
FONTE_NOME = "Constantia"
MASCOTE_TAM = 72

PELO, PELO_ESCURO, FOCINHO = "#A8703F", "#6F4527", "#C99A66"
NARINA, OLHO, AGUA = "#3A2412", "#1B120A", "#244F4B"


def formas_mascote(estado="parado", quadro=0):
    """Desenho da capivara em uma grade de 72x72. O estado muda o rosto."""
    f = [
        ("oval", (2, 2, 70, 70), AGUA, LINHA, 2),
        ("rrect", (12, 13, 24, 25), 5, PELO_ESCURO, None, 0),   # orelhas pequenas, no alto da cabeça
        ("rrect", (48, 13, 60, 25), 5, PELO_ESCURO, None, 0),
        ("rrect", (10, 17, 62, 58), 17, PELO, None, 0),         # cabeça larga e reta
        ("rrect", (15, 33, 57, 63), 13, FOCINHO, None, 0),      # focinho grande e rombudo
        ("oval", (26, 37, 32, 43), NARINA, None, 0),            # narinas no alto do focinho
        ("oval", (40, 37, 46, 43), NARINA, None, 0),
    ]
    olhos = [(22, 28), (50, 28)]
    if estado == "pensando":
        for cx, cy in olhos:
            f.append(("line", [(cx - 4, cy), (cx + 4, cy)], OLHO, 2))
        ativo = (quadro // 3) % 3
        for i, x in enumerate((29, 36, 43)):
            f.append(("oval", (x - 2, 5, x + 2, 9), SOL if i == ativo else LINHA_CLARA, None, 0))
    elif estado == "ouvindo":
        for cx, cy in olhos:
            f.append(("oval", (cx - 4, cy - 4, cx + 4, cy + 4), OLHO, None, 0))
            f.append(("oval", (cx - 2, cy - 3, cx, cy - 1), "#FFFFFF", None, 0))
        larg = 2 + (quadro // 3) % 2
        f.append(("arc", (3, 20, 15, 44), 135, 225, SOL, larg))
        f.append(("arc", (57, 20, 69, 44), -45, 45, SOL, larg))
    else:
        piscar = estado == "parado" and quadro % 26 in (0, 1)
        for cx, cy in olhos:
            if piscar:
                f.append(("line", [(cx - 4, cy), (cx + 4, cy)], OLHO, 2))
            else:
                f.append(("oval", (cx - 3, cy - 3, cx + 3, cy + 3), OLHO, None, 0))
        if estado == "falando":
            if (quadro // 2) % 2 == 0:
                f.append(("oval", (29, 52, 43, 58), "#3A1F10", None, 0))
            else:
                f.append(("line", [(29, 54), (43, 54)], "#3A1F10", 2))
        if estado == "vendo":
            for cx, cy in olhos:
                f.append(("oval", (cx - 8, cy - 8, cx + 8, cy + 8), None, SOL, 2))
            f.append(("line", [(30, 28), (42, 28)], SOL, 2))
    return f


def renderizar_mascote(estado="parado", quadro=0, tam=MASCOTE_TAM, escala=4):
    """Desenha em tamanho grande e reduz, para as bordas ficarem suaves."""
    S = tam * escala
    k = S / 72
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for p in formas_mascote(estado, quadro):
        if p[0] == "oval":
            _, bb, fill, borda, larg = p
            d.ellipse([c * k for c in bb], fill=fill, outline=borda,
                      width=max(1, int(larg * k)) if borda else 1)
        elif p[0] == "rrect":
            _, bb, raio, fill, borda, larg = p
            d.rounded_rectangle([c * k for c in bb], radius=raio * k, fill=fill, outline=borda,
                                width=max(1, int(larg * k)) if borda else 1)
        elif p[0] == "line":
            _, pts, cor, larg = p
            d.line([(x * k, y * k) for x, y in pts], fill=cor, width=max(1, int(larg * k)))
        elif p[0] == "arc":
            _, bb, a0, a1, cor, larg = p
            d.arc([c * k for c in bb], a0, a1, fill=cor, width=max(1, int(larg * k)))
    return img.resize((tam, tam), Image.Resampling.LANCZOS)


def criar_icone():
    try:
        caminho = os.path.join(tempfile.gettempdir(), "capri_icone.ico")
        renderizar_mascote("parado", 0, tam=256, escala=2).save(
            caminho, format="ICO", sizes=[(256, 256), (64, 64), (48, 48), (32, 32), (16, 16)])
        return caminho
    except Exception:
        return None


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        self.criador = ler_config().get("criador") or CRIADOR_PADRAO
        self.title(f"Capri - Assistente Virtual | criada por {self.criador}")
        self.geometry("860x780")
        self.fila = queue.Queue()
        self.historico = []
        self.ocupado = False
        self.voz_on = True
        self.client = None
        self.controle_ok = False
        self.parar_flag = False
        self.visao_ok = False
        self.ao_vivo = False
        self.vigia_ativa = False

        self.configure(fg_color=FUNDO)
        self.minsize(620, 560)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.msgs_labels = []
        self.largura_msg = 560
        self._job_wrap = None
        self.quadro_mascote = 0
        self._chave_mascote = None

        # cabeçalho: a capivara mostra o que a Capri está fazendo
        topo = ctk.CTkFrame(self, fg_color=MARGEM, corner_radius=0)
        topo.grid(row=0, column=0, sticky="ew")
        self._img_mascote = ctk.CTkImage(light_image=renderizar_mascote("parado", 0),
                                         dark_image=renderizar_mascote("parado", 0),
                                         size=(MASCOTE_TAM, MASCOTE_TAM))
        self.mascote = ctk.CTkLabel(topo, text="", image=self._img_mascote)
        self.mascote.pack(side="left", padx=(18, 12), pady=10)
        nome = ctk.CTkFrame(topo, fg_color="transparent")
        nome.pack(side="left")
        ctk.CTkLabel(nome, text="capri", font=(FONTE_NOME, 30, "bold"), text_color=TEXTO).pack(anchor="w")
        self.lbl_criador = ctk.CTkLabel(nome, text=f"criada por {self.criador}",
                                        font=(FONTE_UI, 13), text_color=SUAVE)
        self.lbl_criador.pack(anchor="w")

        estilo_chave = dict(font=(FONTE_UI, 13), text_color=TEXTO, fg_color=LINHA, progress_color=SOL,
                            button_color=TEXTO, button_hover_color="#FFFFFF")
        self.btn_mais = ctk.CTkButton(topo, text="⋯", width=38, height=34, corner_radius=17,
                                      fg_color=LINHA, hover_color=LINHA_CLARA, text_color=TEXTO,
                                      font=(FONTE_UI, 16, "bold"), command=self.menu_mais)
        self.btn_mais.pack(side="right", padx=(6, 18))
        ctk.CTkButton(topo, text="⏹ Parar", width=88, height=34, corner_radius=17, fg_color=PERIGO,
                      hover_color="#A84636", text_color="#FFF4EC", font=(FONTE_UI, 13, "bold"),
                      command=self.parar).pack(side="right", padx=6)
        self.sw_tela = ctk.CTkSwitch(topo, text="Ver tela", command=self.troca_ao_vivo, **estilo_chave)
        self.sw_tela.pack(side="right", padx=10)
        self.sw_voz = ctk.CTkSwitch(topo, text="Voz", command=self.troca_voz, **estilo_chave)
        self.sw_voz.select()
        self.sw_voz.pack(side="right", padx=10)

        # conversa
        self.chat = ctk.CTkScrollableFrame(self, fg_color=FUNDO, corner_radius=0,
                                           scrollbar_button_color=LINHA,
                                           scrollbar_button_hover_color=LINHA_CLARA)
        self.chat.grid(row=1, column=0, sticky="nsew", padx=(6, 2), pady=(8, 0))

        barra = ctk.CTkFrame(self, fg_color="transparent")
        barra.grid(row=2, column=0, sticky="ew", padx=24, pady=(4, 0))
        self.status = ctk.CTkLabel(barra, text="", height=22, anchor="w",
                                   font=(FONTE_UI, 13, "italic"), text_color=SUAVE)
        self.status.pack(side="left")
        self.lbl_vigia = ctk.CTkLabel(barra, text="", height=22, anchor="e",
                                      font=(FONTE_UI, 13), text_color=SOL)
        self.lbl_vigia.pack(side="right")

        # campo de mensagem
        base = ctk.CTkFrame(self, fg_color="transparent")
        base.grid(row=3, column=0, sticky="ew", padx=18, pady=(6, 16))
        base.grid_columnconfigure(0, weight=1)
        self.entrada = ctk.CTkEntry(base, height=46, corner_radius=23, border_width=1, border_color=LINHA,
                                    fg_color=MARGEM, text_color=TEXTO, font=(FONTE_UI, 15),
                                    placeholder_text="Escreva para a Capri ou use o microfone",
                                    placeholder_text_color=SUAVE)
        self.entrada.grid(row=0, column=0, sticky="ew")
        self.entrada.bind("<Return>", lambda e: self.enviar())
        ctk.CTkButton(base, text="🎤", width=46, height=46, corner_radius=23, fg_color=MARGEM,
                      hover_color=LINHA, border_width=1, border_color=LINHA, text_color=TEXTO,
                      command=self.ouvir).grid(row=0, column=1, padx=(8, 0))
        ctk.CTkButton(base, text="Enviar", width=96, height=46, corner_radius=23, fg_color=SOL,
                      hover_color=SOL_ESCURO, text_color="#20170A", font=(FONTE_UI, 15, "bold"),
                      command=self.enviar).grid(row=0, column=2, padx=(8, 0))

        self.bind("<Configure>", self._ao_redimensionar, add="+")
        self.add("Capri", f"Oi, eu sou a Capri, criada por {self.criador}. Posso abrir programas, mexer nas "
                          "configurações do Windows, controlar mouse e teclado e ver a sua tela. "
                          "Antes de qualquer coisa arriscada, eu peço a sua permissão.\n\n"
                          "Para me chamar de qualquer lugar, aperte Ctrl + Alt + C.")
        self.after(60, self._tick_mascote)
        self.after(400, self._definir_icone)
        self.after(300, self.iniciar)
        self.after(100, self.loop)
        threading.Thread(target=self._atalho_global, daemon=True).start()

    def trazer_frente(self):
        try:
            self.deiconify()
            self.lift()
            self.attributes("-topmost", True)
            self.after(200, lambda: self.attributes("-topmost", False))
            self.entrada.focus_set()
        except Exception:
            pass

    def _atalho_global(self):
        user32 = ctypes.windll.user32
        segurando = False
        while True:
            ctrl = user32.GetAsyncKeyState(0x11) & 0x8000
            alt = user32.GetAsyncKeyState(0x12) & 0x8000
            c = user32.GetAsyncKeyState(0x43) & 0x8000
            if ctrl and alt and c:
                if not segurando:
                    segurando = True
                    self.fila.put(("frente",))
            else:
                segurando = False
            time.sleep(0.05)

    def fazer_atalho(self):
        try:
            caminho = criar_atalho_desktop()
            self.add("Capri", f"Atalho criado: {caminho}. Dá dois cliques nele para me abrir.")
        except Exception as erro:
            self.add("Capri", f"Não consegui criar o atalho: {erro}")

    def garantir_controle(self):
        if self.parar_flag:
            return False
        if posicao_mouse() == (0, 0):
            self.controle_ok = False
            return False
        if self.controle_ok:
            return True
        ok = self.confirmar("A Capri quer controlar o mouse e o teclado nesta sessão.\n\n"
                            "Para interromper: botão ⏹ Parar, ou mova o mouse para o canto "
                            "superior esquerdo da tela.\n\nPermitir?")
        self.controle_ok = bool(ok)
        return self.controle_ok

    # ---------- chave ----------
    def iniciar(self):
        try:
            chave = json.loads(CONFIG.read_text(encoding="utf-8")).get("chave", "")
        except Exception:
            chave = ""
        if chave:
            self.client = Groq(api_key=chave)
        else:
            self.pedir_chave()

    def pedir_chave(self):
        d = ctk.CTkInputDialog(text="Cole sua chave do Groq (gsk_...):", title="Chave de API")
        k = (d.get_input() or "").strip()
        if k:
            salvar_config(chave=k)
            self.client = Groq(api_key=k)

    def troca_voz(self):
        self.voz_on = not self.voz_on

    def parar(self):
        self.parar_flag = True
        self.vigia_ativa = False
        self.status.configure(text="Parando...")
        self.atualizar_indicador()

    def atualizar_indicador(self):
        partes = []
        if self.ao_vivo:
            partes.append("👁 vendo a tela a cada mensagem")
        if self.vigia_ativa:
            partes.append("👁 vigiando a tela")
        self.lbl_vigia.configure(text="  |  ".join(partes))

    AVISO_VISAO = ("A Capri quer VER a tela do seu computador.\n\n"
                   "As capturas de tela são enviadas para a IA (Groq) para serem analisadas. "
                   "Não deixe senhas, dados bancários ou conversas privadas à mostra enquanto isso estiver ligado.\n\n"
                   "Para parar: desligue 👁 Tela ou clique em ⏹ Parar.\n\nPermitir nesta sessão?")

    def troca_ao_vivo(self):
        if self.sw_tela.get():
            if not self.visao_ok:
                self.visao_ok = bool(messagebox.askyesno("A Capri quer ver a tela", self.AVISO_VISAO, parent=self))
            if not self.visao_ok:
                self.sw_tela.deselect()
                return
            self.ao_vivo = True
            self.add("Capri", "Modo 👁 Tela ligado: vou olhar a sua tela a cada mensagem que você mandar.")
        else:
            self.ao_vivo = False
            self.add("Capri", "Modo 👁 Tela desligado.")
        self.atualizar_indicador()

    def garantir_visao(self):
        if self.visao_ok:
            return True
        self.visao_ok = bool(self.confirmar(self.AVISO_VISAO))
        return self.visao_ok

    def perguntar_visao(self, pergunta, b64):
        cfg = ler_config()
        fixo = cfg.get("modelo_visao")
        candidatos = ([fixo] if fixo else []) + [c for c in VISAO_CANDIDATOS if c != fixo]
        erros = []
        for modelo in candidatos:
            base = dict(model=modelo, max_completion_tokens=2000,
                        messages=[{"role": "user", "content": [
                            {"type": "text", "text": pergunta},
                            {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + b64}}]}])
            try:
                try:
                    r = self.client.chat.completions.create(reasoning_effort="low", **base)
                except Exception as e1:
                    if "reasoning" not in str(e1).lower():
                        raise
                    r = self.client.chat.completions.create(**base)
                texto = r.choices[0].message.content or ""
                texto = re.sub(r"<think>.*?</think>", "", texto, flags=re.S).strip()
                if modelo != fixo:
                    salvar_config(modelo_visao=modelo)
                return texto or "O modelo não devolveu texto. Tente de novo."
            except Exception as erro:
                erros.append(f"{modelo}: {str(erro)[:300]}")
        raise RuntimeError(" | ".join(erros))

    def _vigiar(self, objetivo, intervalo, minutos):
        fim = time.time() + minutos * 60
        erros = 0
        motivo = ""
        achou = False
        try:
            while True:
                if not self.vigia_ativa:
                    motivo = "você pediu para parar"
                    break
                if time.time() >= fim:
                    motivo = "o tempo acabou e não vi nada"
                    break
                for _ in range(intervalo):
                    if not self.vigia_ativa:
                        break
                    time.sleep(1)
                if not self.vigia_ativa:
                    continue
                try:
                    resp = self.perguntar_visao(
                        "Olhe esta captura da tela e responda: " + objetivo +
                        "\nComece a resposta com SIM ou NAO e depois escreva uma frase curta dizendo o que você vê.",
                        capturar_tela_b64())
                    erros = 0
                except Exception as erro:
                    erros += 1
                    if erros >= 3:
                        motivo = f"deu erro 3 vezes seguidas ({str(erro)[:120]})"
                        break
                    continue
                if resp.strip().upper().startswith("SIM"):
                    aviso = "👁 Aconteceu! " + resp.strip()[:300]
                    self.fila.put(("add", "Capri", aviso))
                    if self.voz_on:
                        try:
                            asyncio.run(falar(aviso))
                        except Exception:
                            pass
                    achou = True
                    break
        finally:
            self.vigia_ativa = False
            self.fila.put(("indicador",))
        if not achou:
            self.fila.put(("add", "Capri", f"Parei de vigiar a tela: {motivo}."))

    def mudar_criador(self):
        d = ctk.CTkInputDialog(text=f"Criador atual: {self.criador}\nDigite o novo nome:",
                               title="Criador da Capri")
        novo = (d.get_input() or "").strip()[:40]
        if novo:
            self.criador = novo
            salvar_config(criador=novo)
            self.lbl_criador.configure(text=f"criada por {novo}")
            self.title(f"Capri - Assistente Virtual | criada por {novo}")
            self.add("Capri", f"Anotado! Fui criada por {novo}.")

    # ---------- tela ----------
    def _definir_icone(self):
        caminho = criar_icone()
        if caminho:
            try:
                self.iconbitmap(caminho)
            except Exception:
                pass

    def _estado_mascote(self):
        txt = (self.status.cget("text") or "").lower()
        if "pensando" in txt:
            return "pensando"
        if "ouvindo" in txt:
            return "ouvindo"
        if "falando" in txt:
            return "falando"
        if "olhando" in txt:
            return "vendo"
        if self.ao_vivo or self.vigia_ativa:
            return "vendo"
        return "parado"

    def _tick_mascote(self):
        self.quadro_mascote += 1
        q = self.quadro_mascote
        est = self._estado_mascote()
        balde = {"parado": q % 26 in (0, 1), "pensando": (q // 3) % 3, "ouvindo": (q // 3) % 2,
                 "falando": (q // 2) % 2, "vendo": 0}[est]
        chave = (est, balde)
        if chave != self._chave_mascote:
            self._chave_mascote = chave
            try:
                img = renderizar_mascote(est, q)
                self._img_mascote = ctk.CTkImage(light_image=img, dark_image=img,
                                                 size=(MASCOTE_TAM, MASCOTE_TAM))
                self.mascote.configure(image=self._img_mascote)
            except Exception:
                pass
        self.after(140, self._tick_mascote)

    def _ao_redimensionar(self, e):
        if e.widget is not self:
            return
        novo = max(280, min(600, int(e.width * 0.66) - 40))
        if abs(novo - self.largura_msg) < 24:
            return
        self.largura_msg = novo
        if self._job_wrap:
            self.after_cancel(self._job_wrap)
        self._job_wrap = self.after(120, self._aplicar_largura)

    def _aplicar_largura(self):
        for lbl in self.msgs_labels:
            try:
                lbl.configure(wraplength=self.largura_msg)
            except Exception:
                pass

    def rolar_fim(self):
        try:
            self.chat.update_idletasks()
            self.chat._parent_canvas.yview_moveto(1.0)
        except Exception:
            pass

    def _estilo_menu(self):
        return tk.Menu(self, tearoff=0, bg=MARGEM, fg=TEXTO, activebackground=PELAGEM,
                       activeforeground=TEXTO, bd=0, relief="flat", font=(FONTE_UI, 11))

    def menu_mais(self):
        m = self._estilo_menu()
        m.add_command(label="  Criar atalho na Área de Trabalho  ", command=self.fazer_atalho)
        m.add_command(label="  Trocar a chave da API  ", command=self.pedir_chave)
        m.add_command(label="  Mudar o nome do criador  ", command=self.mudar_criador)
        x = self.btn_mais.winfo_rootx()
        y = self.btn_mais.winfo_rooty() + self.btn_mais.winfo_height() + 4
        try:
            m.tk_popup(x, y)
        finally:
            m.grab_release()

    def menu_copiar(self, e, texto):
        m = self._estilo_menu()
        m.add_command(label="  Copiar texto  ", command=lambda: self._copiar(texto))
        try:
            m.tk_popup(e.x_root, e.y_root)
        finally:
            m.grab_release()

    def _copiar(self, texto):
        self.clipboard_clear()
        self.clipboard_append(texto)
        self.update()

    # ---------- tela ----------
    def add(self, quem, texto):
        texto = str(texto)
        linha = ctk.CTkFrame(self.chat, fg_color="transparent")
        linha.pack(fill="x", padx=14, pady=(2, 7))
        bolha = None
        if quem == "⚙️":
            lbl = ctk.CTkLabel(linha, text=texto[:220], font=(FONTE_UI, 12, "italic"), text_color=SUAVE,
                               wraplength=self.largura_msg, justify="left", anchor="w")
            lbl.pack(anchor="w", padx=(8, 0))
        else:
            if quem == "Você":
                lado, cor, borda = "e", PELAGEM, 0
                cor_txt = "#FBF3E6"
            elif quem == "⚠️":
                lado, cor, borda = "w", "#3A2420", 1
                cor_txt = "#FFD9CF"
            else:
                lado, cor, borda = "w", BOLHA_CAPRI, 1
                cor_txt = TEXTO
            bolha = ctk.CTkFrame(linha, fg_color=cor, corner_radius=18, border_width=borda,
                                 border_color=PERIGO if quem == "⚠️" else LINHA)
            bolha.pack(anchor=lado)
            lbl = ctk.CTkLabel(bolha, text=texto, font=(FONTE_UI, 15), text_color=cor_txt,
                               wraplength=self.largura_msg, justify="left", anchor="w")
            lbl.pack(padx=16, pady=11)
        self.msgs_labels.append(lbl)
        for w in (linha, lbl, bolha):
            if w is not None:
                w.bind("<Button-3>", lambda e, tx=texto: self.menu_copiar(e, tx))
        self.after(40, self.rolar_fim)

    def loop(self):
        try:
            while True:
                item = self.fila.get_nowait()
                if item[0] == "add":
                    self.add(item[1], item[2])
                elif item[0] == "status":
                    self.status.configure(text=item[1])
                elif item[0] == "livre":
                    self.ocupado = False
                    self.status.configure(text="")
                elif item[0] == "indicador":
                    self.atualizar_indicador()
                elif item[0] == "frente":
                    self.trazer_frente()
                elif item[0] == "confirmar":
                    self.lift()
                    item[3]["ok"] = messagebox.askyesno("A Capri pede permissão", item[1], parent=self)
                    item[2].set()
        except queue.Empty:
            pass
        self.after(100, self.loop)

    # ---------- entrada ----------
    def enviar(self):
        texto = self.entrada.get().strip()
        if not texto or self.ocupado:
            return
        if not self.client:
            self.pedir_chave()
            if not self.client:
                return
        self.entrada.delete(0, "end")
        self.add("Você", texto)
        self.ocupado = True
        self.parar_flag = False
        self.status.configure(text="Pensando...")
        threading.Thread(target=self._pensar, args=(texto,), daemon=True).start()

    def ouvir(self):
        if self.ocupado:
            return
        if not self.client:
            self.pedir_chave()
            if not self.client:
                return
        self.ocupado = True
        self.parar_flag = False
        self.status.configure(text="Ouvindo... fale agora!")
        threading.Thread(target=self._ouvir, daemon=True).start()

    def _ouvir(self):
        texto = ouvir_voz()
        if not texto:
            self.fila.put(("add", "Capri", "Não entendi, tenta de novo."))
            self.fila.put(("livre",))
            return
        self.fila.put(("add", "Você", texto))
        self.fila.put(("status", "Pensando..."))
        self._pensar(texto)

    # ---------- cérebro ----------
    def _pensar(self, texto):
        try:
            resposta = self.conversar(texto)
        except Exception as erro:
            self.fila.put(("add", "Capri", f"Ops, deu erro: {str(erro)[:250]}"))
            self.fila.put(("livre",))
            return
        self.fila.put(("add", "Capri", resposta))
        if self.voz_on:
            self.fila.put(("status", "Falando..."))
            try:
                asyncio.run(falar(resposta))
            except Exception as erro:
                print("Erro na voz:", erro)
        self.fila.put(("livre",))

    def conversar(self, texto):
        self.historico.append({"role": "user", "content": texto})
        mem = carregar_memoria()
        sistema = PERSONA + f" Você foi criada por {self.criador}. Se perguntarem quem te criou, diga isso."
        if mem:
            sistema += "\n\nO que você lembra do usuário:\n" + "\n".join(f"- {m}" for m in mem)
        if self.ao_vivo and not self.parar_flag:
            try:
                self.fila.put(("status", "👁 Olhando a tela..."))
                desc = self.perguntar_visao(
                    f'O usuário disse: "{texto}". Descreva de forma objetiva o que aparece na tela e é relevante '
                    "para isso (programas abertos, textos importantes, botões e campos visíveis). No máximo 10 linhas.",
                    capturar_tela_b64())
                sistema += "\n\nO que está na tela do usuário agora (captura feita neste instante):\n" + desc
            except Exception as erro:
                self.fila.put(("add", "⚠️", f"Falha ao ver a tela: {erro}"))
                sistema += "\n\n(A captura da tela falhou nesta mensagem; diga isso se for relevante.)"
        msgs = [{"role": "system", "content": sistema}] + self.historico[-12:]
        for tentativa in range(8):
            if self.parar_flag:
                return "Parei! Interrompi o que estava fazendo."
            try:
                r = self.client.chat.completions.create(
                    model=MODELO, messages=msgs, tools=TOOLS, tool_choice="auto")
            except Exception as e:
                if tentativa < 2 and "tool" in str(e).lower():
                    continue
                raise
            m = r.choices[0].message
            if not m.tool_calls:
                final = m.content or "Pronto!"
                self.historico.append({"role": "assistant", "content": final})
                return final
            msgs.append({"role": "assistant", "content": m.content or "", "tool_calls": [
                {"id": tc.id, "type": "function",
                 "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in m.tool_calls]})
            for tc in m.tool_calls:
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except Exception:
                    args = {}
                msgs.append({"role": "tool", "tool_call_id": tc.id,
                             "content": str(self.executar(tc.function.name, args))})
        return "Não consegui terminar essa tarefa."

    # ---------- ferramentas (acesso ao PC) ----------
    def confirmar(self, pergunta):
        ev, res = threading.Event(), {"ok": False}
        self.fila.put(("confirmar", pergunta, ev, res))
        ev.wait(timeout=60)
        return res["ok"]

    def executar(self, nome, a):
        self.fila.put(("add", "⚙️", f"{nome} {a if a else ''}"))
        try:
            if nome == "abrir_programa":
                app_nome = a.get("nome")
                if app_nome == "firefox":
                    if not FIREFOX:
                        return "Não encontrei o Firefox neste PC."
                    subprocess.Popen([FIREFOX])
                    return "Firefox aberto."
                if app_nome == "navegador padrão":
                    abrir_url("https://www.google.com")
                    return "Navegador aberto."
                cmd = APPS.get(app_nome)
                if not cmd:
                    return "Programa não permitido."
                r = subprocess.run(f'start "" {cmd}', shell=True, capture_output=True)
                if r.returncode != 0:
                    return f"Não encontrei {app_nome} neste PC."
                return "Programa aberto."
            if nome == "abrir_site":
                url = a.get("url", "")
                if not url.startswith("http"):
                    url = "https://" + url
                abrir_url(url)
                return "Site aberto."
            if nome == "pesquisar_web":
                abrir_url("https://www.google.com/search?q=" + quote_plus(a.get("consulta", "")))
                return "Pesquisa aberta no navegador."
            if nome == "abrir_pasta":
                p = PASTAS.get(a.get("pasta"))
                if not p or not p.exists():
                    return "Pasta não encontrada."
                os.startfile(p)
                return "Pasta aberta."
            if nome == "listar_arquivos":
                p = PASTAS.get(a.get("pasta"))
                if not p or not p.exists():
                    return "Pasta não encontrada."
                nomes = sorted(x.name for x in p.iterdir())
                if not nomes:
                    return "Pasta vazia."
                return ", ".join(nomes[:40]) + (" ... (e mais)" if len(nomes) > 40 else "")
            if nome == "abrir_arquivo":
                p = Path(a.get("caminho", "")).expanduser()
                if not p.exists():
                    return "Esse caminho não existe."
                if p.suffix.lower() in EXTENSOES_PERIGOSAS:
                    if not self.confirmar(f"A Capri quer abrir/executar este programa:\n\n{p}\n\nPermitir?"):
                        return "O usuário negou o pedido."
                os.startfile(str(p))
                return "Aberto."
            if nome == "volume":
                acao = a.get("acao")
                try:
                    v = int(a.get("valor"))
                except (TypeError, ValueError):
                    v = 10 if acao in ("aumentar", "diminuir") else 50
                v = max(0, min(100, v))
                if acao == "mutar":
                    tecla(VK_MUDO)
                    return "Mudo alternado (ligado/desligado)."
                if acao == "aumentar":
                    tecla(VK_CIMA, max(1, round(v / 2)))
                    return f"Aumentei o volume em cerca de {v}%."
                if acao == "diminuir":
                    tecla(VK_BAIXO, max(1, round(v / 2)))
                    return f"Diminuí o volume em cerca de {v}%."
                if acao == "definir":
                    tecla(VK_BAIXO, 50)
                    if v > 0:
                        tecla(VK_CIMA, round(v / 2))
                    return f"Volume ajustado para cerca de {v}%."
                return "Ação de volume desconhecida."
            if nome == "controle_midia":
                vk = VK_MIDIA.get(a.get("acao"))
                if not vk:
                    return "Ação desconhecida."
                tecla(vk)
                return "Feito."
            if nome == "listar_programas_abertos":
                lista = sorted(set(janelas_abertas()))
                return "\n".join(lista[:40]) if lista else "Nenhuma janela encontrada."
            if nome == "fechar_programa":
                proc = a.get("processo", "").strip()
                if not re.fullmatch(r"[\w .\-]{1,60}", proc):
                    return "Nome de processo inválido."
                if not proc.lower().endswith(".exe"):
                    proc += ".exe"
                if not self.confirmar(f"A Capri quer FECHAR o programa:\n\n{proc}\n\n"
                                      "Trabalho não salvo pode ser perdido. Permitir?"):
                    return "O usuário negou o pedido."
                r = subprocess.run(["taskkill", "/IM", proc, "/F"], capture_output=True)
                return "Programa fechado." if r.returncode == 0 else "Não consegui fechar (talvez não esteja aberto)."
            if nome == "info_sistema":
                vm = psutil.virtual_memory()
                du = psutil.disk_usage(HOME.anchor or "C:\\")
                return (f"CPU {psutil.cpu_percent(interval=0.5)}%, "
                        f"RAM {vm.percent}% usada ({vm.used / 1e9:.1f} de {vm.total / 1e9:.1f} GB), "
                        f"disco {du.percent}% usado ({du.free / 1e9:.0f} GB livres)")
            if nome == "hora_data":
                return datetime.datetime.now().strftime("%d/%m/%Y, %H:%M")
            if nome == "criar_nota":
                arq = PASTAS["documentos"] / "Capri_notas.txt"
                with open(arq, "a", encoding="utf-8") as f:
                    f.write(f"[{datetime.datetime.now():%d/%m/%Y %H:%M}] {a.get('texto', '')}\n")
                return "Nota salva em Documentos/Capri_notas.txt."
            if nome == "tirar_print":
                PASTAS["imagens"].mkdir(exist_ok=True)
                arq = PASTAS["imagens"] / f"capri_print_{datetime.datetime.now():%Y%m%d_%H%M%S}.png"
                ImageGrab.grab().save(arq)
                return f"Print salvo em {arq}"
            if nome == "bloquear_tela":
                ctypes.windll.user32.LockWorkStation()
                return "Tela bloqueada."
            if nome == "desligar_pc":
                if not self.confirmar("A Capri quer desligar o computador em 60 segundos. Permitir?"):
                    return "O usuário negou o pedido."
                subprocess.run(["shutdown", "/s", "/t", "60"])
                return "Desligamento agendado para daqui a 60 segundos."
            if nome == "reiniciar_pc":
                if not self.confirmar("A Capri quer reiniciar o computador em 60 segundos. Permitir?"):
                    return "O usuário negou o pedido."
                subprocess.run(["shutdown", "/r", "/t", "60"])
                return "Reinicialização agendada para daqui a 60 segundos."
            if nome == "cancelar_desligamento":
                subprocess.run(["shutdown", "/a"])
                return "Desligamento/reinicialização cancelados."
            if nome == "executar_comando":
                cmd = a.get("comando", "").strip()
                if not cmd:
                    return "Comando vazio."
                if not self.confirmar("A Capri quer executar este comando no PC:\n\n"
                                      f"{cmd}\n\nLeia com atenção. Permitir?"):
                    return "O usuário negou o pedido."
                registrar_alteracao(f"comando aprovado: {cmd}")
                try:
                    r = subprocess.run(cmd, shell=True, capture_output=True, timeout=30)
                except subprocess.TimeoutExpired:
                    return "O comando demorou demais e foi interrompido."
                enc = f"cp{ctypes.windll.kernel32.GetOEMCP()}"
                saida = (r.stdout + r.stderr).decode(enc, errors="replace").strip()
                return saida[:1500] if saida else "Comando executado, sem saída."
            if nome == "posicao_mouse":
                x, y = posicao_mouse()
                return f"Mouse em x={x}, y={y}."
            if nome in ("mover_mouse", "clicar", "digitar", "apertar_tecla"):
                if not self.garantir_controle():
                    return ("Controle de mouse e teclado não autorizado ou interrompido "
                        "(botão Parar ou mouse no canto superior esquerdo).")
            if nome == "mover_mouse":
                mover_mouse(a.get("x", 0), a.get("y", 0))
                return "Mouse movido."
            if nome == "clicar":
                if a.get("x") is not None and a.get("y") is not None:
                    mover_mouse(a.get("x"), a.get("y"))
                vezes = int(a.get("vezes") or 1)
                clicar_mouse(a.get("botao") or "esquerdo", vezes)
                return "Clique feito."
            if nome == "digitar":
                digitar_texto(a.get("texto") or "")
                return "Texto digitado."
            if nome == "apertar_tecla":
                partes = [p.strip().lower() for p in str(a.get("tecla", "")).replace(" ", "").split("+") if p.strip()][:5]
                if not partes:
                    return "Tecla vazia."
                vks = []
                for p in partes:
                    vk = vk_de(p)
                    if vk is None:
                        return f"Não conheço a tecla {p}."
                    vks.append(vk)
                sensivel = (any(p in ("win", "windows", "delete", "del") for p in partes)
                            or ("alt" in partes and "f4" in partes))
                if sensivel and not self.confirmar("A Capri quer apertar este atalho:\n\n"
                                                   f"{' + '.join(partes)}\n\nPermitir?"):
                    return "O usuário negou o pedido."
                atalho(vks)
                return "Tecla apertada."
            if nome == "tamanho_tela":
                w = ctypes.windll.user32.GetSystemMetrics(0)
                h = ctypes.windll.user32.GetSystemMetrics(1)
                return f"A tela tem {w}x{h} pixels."
            if nome == "abrir_configuracao":
                uri = PAGINAS_CONFIG.get(a.get("pagina"))
                if not uri:
                    return "Página de configurações desconhecida."
                os.startfile(uri)
                return "Página de configurações aberta."
            if nome == "tema":
                modo = a.get("modo")
                if modo not in ("claro", "escuro"):
                    return "Modo inválido."
                chave = r"HKCU\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
                for v in ("AppsUseLightTheme", "SystemUsesLightTheme"):
                    reg_escrever(chave, v, "numero", 1 if modo == "claro" else 0)
                return f"Tema {modo} aplicado."
            if nome == "papel_de_parede":
                p = Path(a.get("caminho", "")).expanduser()
                if not p.is_file() or p.suffix.lower() not in (".jpg", ".jpeg", ".png", ".bmp"):
                    return "Informe o caminho completo de uma imagem (jpg, png ou bmp)."
                ok = ctypes.windll.user32.SystemParametersInfoW(0x0014, 0, str(p.resolve()), 3)
                registrar_alteracao(f"papel de parede -> {p}")
                return "Papel de parede trocado." if ok else "O Windows recusou a troca."
            if nome == "plano_energia":
                if a.get("acao") == "listar":
                    r = subprocess.run(["powercfg", "/list"], capture_output=True)
                    return texto_oem(r.stdout + r.stderr)[:1200]
                guid = PLANOS_ENERGIA.get(a.get("plano"))
                if not guid:
                    return "Plano inválido."
                r = subprocess.run(["powercfg", "/setactive", guid], capture_output=True)
                registrar_alteracao(f"plano de energia -> {a.get('plano')}")
                if r.returncode == 0:
                    return f"Plano de energia alterado para {a.get('plano')}."
                return "Esse plano não existe neste PC. Tente 'equilibrado'."
            if nome == "tempo_tela_suspensao":
                if a.get("item") not in ("tela", "suspensao"):
                    return "Item inválido."
                item = "monitor" if a.get("item") == "tela" else "standby"
                minutos = max(0, min(600, int(a.get("minutos") or 0)))
                for fonte in ("ac", "dc"):
                    subprocess.run(["powercfg", "/change", f"{item}-timeout-{fonte}", str(minutos)],
                                   capture_output=True)
                registrar_alteracao(f"tempo de {a.get('item')} -> {minutos} min")
                return f"Configurado: {a.get('item')} após {minutos} minutos (0 = nunca)."
            if nome == "velocidade_mouse":
                v = max(1, min(20, int(a.get("valor") or 10)))
                ctypes.windll.user32.SystemParametersInfoW(0x0071, 0, ctypes.c_void_p(v), 3)
                registrar_alteracao(f"velocidade do mouse -> {v}")
                return f"Velocidade do mouse ajustada para {v}."
            if nome == "brilho":
                v = max(0, min(100, int(a.get("valor") or 50)))
                cmd_ps = ("(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods)"
                          f".WmiSetBrightness(1,{v})")
                r = subprocess.run(["powershell", "-NoProfile", "-Command", cmd_ps],
                                   capture_output=True, timeout=20)
                if r.returncode == 0 and not r.stderr.strip():
                    registrar_alteracao(f"brilho -> {v}")
                    return f"Brilho ajustado para {v}%."
                return ("Não consegui mudar o brilho. Isso costuma funcionar só em notebooks; "
                        "em monitor comum use os botões do próprio monitor.")
            if nome == "esvaziar_lixeira":
                if not self.confirmar("A Capri quer ESVAZIAR a Lixeira. Os arquivos não poderão "
                                      "ser recuperados.\n\nPermitir?"):
                    return "O usuário negou o pedido."
                registrar_alteracao("lixeira esvaziada")
                subprocess.run(["powershell", "-NoProfile", "-Command",
                                "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"],
                               capture_output=True, timeout=60)
                return "Lixeira esvaziada."
            if nome == "info_rede":
                linhas = []
                stats = psutil.net_if_stats()
                for nome_if, addrs in psutil.net_if_addrs().items():
                    if nome_if in stats and stats[nome_if].isup:
                        for ad in addrs:
                            if ad.family.name == "AF_INET":
                                linhas.append(f"{nome_if}: {ad.address}")
                return "\n".join(linhas) if linhas else "Nenhuma conexão ativa encontrada."
            if nome == "registro_ler":
                try:
                    return f"{a.get('valor')} = {reg_ler(a.get('caminho', ''), a.get('valor', ''))!r}"
                except FileNotFoundError:
                    return "Chave ou valor não encontrado."
            if nome == "registro_escrever":
                caminho, valor = a.get("caminho", ""), a.get("valor", "")
                tipo, dados = a.get("tipo", "texto"), a.get("dados", "")
                raiz, _h, _s = reg_dividir(caminho)
                if raiz not in ("HKCU", "HKEY_CURRENT_USER"):
                    return "Só é permitido escrever em HKCU."
                if reg_bloqueado(caminho):
                    return "Essa área do Registro é protegida (inicialização, políticas, serviços)."
                try:
                    atual = reg_ler(caminho, valor)
                except Exception:
                    atual = "(não existe)"
                if not self.confirmar("A Capri quer ALTERAR o Registro do Windows:\n\n"
                                      f"Chave: {caminho}\nValor: {valor}\n"
                                      f"Valor atual: {atual}\nNovo valor: {dados} ({tipo})\n\nPermitir?"):
                    return "O usuário negou o pedido."
                antigo = reg_escrever(caminho, valor, tipo, dados)
                return f"Registro alterado. Valor anterior: {antigo!r}"
            if nome == "executar_powershell":
                cmd_ps = a.get("comando", "").strip()
                if not cmd_ps:
                    return "Comando vazio."
                if not self.confirmar("A Capri quer executar este comando no POWERSHELL:\n\n"
                                      f"{cmd_ps}\n\nLeia com atenção. Permitir?"):
                    return "O usuário negou o pedido."
                registrar_alteracao(f"powershell aprovado: {cmd_ps}")
                try:
                    r = subprocess.run(["powershell", "-NoProfile", "-Command", cmd_ps],
                                       capture_output=True, timeout=30)
                except subprocess.TimeoutExpired:
                    return "O comando demorou demais e foi interrompido."
                saida = texto_oem(r.stdout + r.stderr)
                return saida[:1500] if saida else "Comando executado, sem saída."
            if nome == "ver_tela":
                if self.parar_flag:
                    return "Interrompido pelo usuário."
                if not self.garantir_visao():
                    return "O usuário não autorizou a Capri a ver a tela."
                self.fila.put(("status", "👁 Olhando a tela..."))
                pergunta = (a.get("pergunta") or "Descreva o que aparece na tela.").strip()
                try:
                    return self.perguntar_visao(
                        pergunta + "\n\nResponda em português, de forma objetiva, citando os textos importantes que aparecerem.",
                        capturar_tela_b64())
                except Exception as erro:
                    self.fila.put(("add", "⚠️", f"Falha ao ver a tela: {erro}"))
                    return f"Erro ao ver a tela: {str(erro)[:300]}"
            if nome == "vigiar_tela":
                objetivo = (a.get("objetivo") or "").strip()
                if not objetivo:
                    return "Diga o que devo vigiar."
                if self.vigia_ativa:
                    return "Já estou vigiando a tela. Peça para parar antes de começar outra vigia."
                if not self.garantir_visao():
                    return "O usuário não autorizou a Capri a ver a tela."
                intervalo = max(10, min(300, int(a.get("intervalo_segundos") or 15)))
                minutos = max(1, min(60, int(a.get("duracao_minutos") or 10)))
                self.vigia_ativa = True
                self.fila.put(("indicador",))
                threading.Thread(target=self._vigiar, args=(objetivo, intervalo, minutos), daemon=True).start()
                return f"Vigiando a tela a cada {intervalo} segundos, por até {minutos} minutos."
            if nome == "parar_vigia":
                self.vigia_ativa = False
                self.fila.put(("indicador",))
                return "Vigia parada."
            if nome == "lembrar":
                fato = (a.get("fato") or "").strip()
                if not fato:
                    return "Nada para lembrar."
                itens = carregar_memoria()
                if fato not in itens:
                    itens.append(fato)
                salvar_memoria(itens)
                return "Memória salva."
            if nome == "esquecer":
                texto_mem = (a.get("texto") or "").strip().lower()
                itens = [m for m in carregar_memoria() if texto_mem not in m.lower()]
                salvar_memoria(itens)
                return "Memória atualizada."
            if nome == "listar_memorias":
                itens = carregar_memoria()
                return "\n".join(itens) if itens else "Ainda não lembro de nada."
            return "Ferramenta desconhecida."
        except Exception as erro:
            return f"Erro ao executar: {erro}"


if __name__ == "__main__":
    try:
        App().mainloop()
    except Exception:
        import traceback
        try:
            (Path.home() / "capri_erro.txt").write_text(traceback.format_exc(), encoding="utf-8")
        except Exception:
            pass
        try:
            traceback.print_exc()
            input("\nDeu erro (também salvo em capri_erro.txt). Aperte Enter para fechar...")
        except Exception:
            pass
