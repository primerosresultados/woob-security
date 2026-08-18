#!/usr/bin/env python3
"""
Guardrail Woob — advierte antes de tocar cualquier cosa fuera de la zona segura.

Modelo: LISTA BLANCA. Solo pasan sin aviso los archivos que sabemos que son
seguros (UI, estilos, textos, imágenes, tests, documentación). Todo lo demás
avisa — incluso lo que no sabemos clasificar. Es al revés de una lista negra:
lo desconocido se trata como riesgoso, no como inofensivo.

NO bloquea nunca. Devuelve permissionDecision="ask": Claude Code muestra la
advertencia y pide confirmación. Si la persona acepta, el cambio se hace igual.

Una sola aprobación por pedido. No se pregunta paso a paso: la primera vez que
el trabajo sale de la zona segura se pide una aprobación que cubre todo lo que
venga después, hasta el próximo mensaje de la persona.

Eventos:
  UserPromptSubmit -> mensaje nuevo: se borra la aprobación anterior.
  PreToolUse       -> si ya hay aprobación en este pedido, pasa callado.
                      Si no, pide UNA aprobación para todo el trabajo.
  PostToolUse      -> anota qué se tocó, para el informe final.
"""

import json
import os
import re
import sys
import tempfile

CONTACTO = "Equipo de Woob"

# En los tres niveles: una sola aprobación por pedido, y borrar prohibido.
# Lo que cambia es qué dispara esa aprobación.
#   "equilibrado" (por defecto): base de datos, llaves, permisos, dinero,
#     herramientas externas que escriben, y archivos fuera de la zona segura.
#     Los comandos que no reconoce pasan.
#   "estricto": además, cualquier comando que no sea claramente de solo lectura.
#   "relajado": deja pasar las herramientas externas que escriben y los nombres
#     sospechosos dentro de carpetas seguras.
NIVEL = os.environ.get("WOOB_GUARDRAIL_NIVEL", "equilibrado").strip().lower()
if NIVEL in ("normal", "relajado"):
    NIVEL = "relajado"
elif NIVEL != "estricto":
    NIVEL = "equilibrado"

ESTRICTO = NIVEL == "estricto"          # también avisa en comandos desconocidos
PROTEGE_DATOS = NIVEL != "relajado"     # herramientas externas y nombres sospechosos

# Zonas cuya aceptación NO se recuerda: cada vez vuelve a preguntar.
# ---------------------------------------------------------------- lista negra
# Se revisa PRIMERO. Gana sobre la lista blanca: un .md dentro de .claude/
# sigue siendo sensible aunque los .md sean seguros.
# (clave, etiqueta, regex sobre la ruta, riesgos)
ZONAS_ARCHIVO = [
    (
        "guardrail",
        "los avisos de seguridad que te protegen",
        r"(^|/)\.claude/|(^|/)(CLAUDE|AGENTS)\.md$|(^|/)\.cursorrules$|(^|/)\.mcp\.json$",
        [
            "estarías apagando los avisos que te protegen",
            "esto le cambia las reglas a todos, no solo a ti",
        ],
    ),
    (
        "db",
        "dónde se guarda la información de los clientes",
        r"(^|/)(migrations?|migraciones)/|(^|/)seeds?(/|\.)|\.sql$|(^|/)alembic/|"
        r"(^|/)(knex|drizzle|sequelize)\b|supabase/|(^|/)(db|database|datos)/|"
        r"(^|/|_|-)(db|database|supabase|firestore|mongo|postgres)($|/|_|-|\.)",
        [
            "puede borrar o dañar información real de clientes",
            "una vez hecho, muchas veces ya no se puede deshacer",
        ],
    ),
    (
        "schema",
        "cómo está organizada la información",
        r"schema\.[a-z]+$|(^|/)(models?|entities|entidades|schemas?)/|\.graphql$|"
        r"(^|/)prisma/|\.prisma$|(^|/)types?/api",
        [
            "pantallas que hoy funcionan pueden dejar de cargar",
            "casi nunca falla en tu computador: falla en el sitio de verdad",
        ],
    ),
    (
        "auth",
        "quién puede entrar y qué puede ver cada persona",
        r"(^|/|_|-)(auth|autenticacion|login|session|sesion|jwt|oauth|rbac|rls|permis|"
        r"policy|policies|politicas|guard|middleware|roles?)(s)?($|/|_|-|\.)|"
        r"\.rules$|firestore\.rules|storage\.rules",
        [
            "un error acá deja que un cliente vea la información de otro",
            "no se nota que está mal hasta que alguien se aprovecha",
        ],
    ),
    (
        "secretos",
        "las llaves de acceso del sistema",
        r"(^|/)\.env|(^|/|_|-)(secrets?|credentials?|credenciales|apikeys?)($|/|_|-|\.)|"
        r"\.(pem|key|p12|pfx|jks|keystore)$|serviceAccount.*\.json$|"
        r"(^|/)\.(gitignore|dockerignore|npmrc)$",
        [
            "una llave que entra al proyecto queda a la vista para siempre, aunque después la borres",
            "puede hacer que se publique algo que estaba escondido",
        ],
    ),
    (
        "pagos",
        "los cobros y el dinero",
        r"(^|/|_|-)(stripe|mercadopago|transbank|webpay|khipu|flow|paypal|payment|pagos?|"
        r"checkout|billing|facturacion|webhooks?|twilio|sendgrid|resend)($|/|_|-|\.)",
        [
            "acá se mueve plata real",
            "si un cobro falla, no siempre se puede repetir",
        ],
    ),
    (
        "infra",
        "lo que mantiene el sitio en línea",
        r"(^|/)Dockerfile|docker-compose|(^|/)\.github/|(^|/)\.gitlab-ci|"
        r"(vercel|firebase|now|turbo|nx|angular|app|render|railway)\.json$|"
        r"(netlify|fly|wrangler|serverless|render|app|pnpm-workspace)\.(toml|yml|yaml)$|"
        r"\.tf$|nginx|(^|/)(k8s|infra|deploy|ops|terraform|ansible)/|"
        r"(^|/)(Procfile|Makefile|justfile)$",
        [
            "puede dejar el sitio caído sin forma rápida de volver atrás",
        ],
    ),
    (
        "backend",
        "el motor que hace funcionar todo por detrás",
        r"(^|/)(api|server|servidor|backend|routes?|rutas|controllers?|handlers?|resolvers?|"
        r"services|servicios|functions|lambdas?|edge-functions|jobs|workers?|queues?|colas|"
        r"actions|server-actions|trpc|convex|graphql|rpc|cron|scripts?)/|"
        r"\.server\.[a-z]+$|(^|/)route\.[a-z]+$|(^|/)server\.[a-z]+$",
        [
            "otras pantallas y otros servicios dejan de funcionar",
            "se rompen pantallas que no estás mirando",
        ],
    ),
    (
        "build",
        "las piezas que el proyecto necesita para armarse",
        r"(^|/)(package\.json|package-lock\.json|pnpm-lock\.yaml|yarn\.lock|bun\.lockb|"
        r"requirements.*\.txt|pyproject\.toml|poetry\.lock|Pipfile.*|Gemfile.*|go\.(mod|sum)|"
        r"Cargo\.(toml|lock)|composer\.(json|lock))$|"
        r"(^|/)(tsconfig|jsconfig).*\.json$|"
        r"(^|/)(next|vite|webpack|rollup|astro|nuxt|svelte|remix|tailwind|postcss|babel|"
        r"eslint|jest|vitest|playwright|cypress|metro)\.config\.[a-z]+$",
        [
            "el proyecto puede dejar de armarse para todo el equipo, no solo para ti",
        ],
    ),
]

# --------------------------------------------------------------- lista blanca
# Solo esto pasa sin aviso. Si no calza acá, se avisa igual.
SEGURA_CARPETA = re.compile(
    r"(^|/)(components?|componentes|ui|views?|vistas?|pages(?!/api)|paginas|layouts?|"
    r"widgets?|sections?|secciones|blocks?|bloques|styles?|estilos|css|sass|scss|theme|temas?|"
    r"assets|static|img|images|imagenes|icons?|iconos?|fonts?|fuentes|media|"
    r"locales?|i18n|intl|translations?|traducciones|lang|idiomas|"
    r"content|contenido|copy|textos?|posts?|blog|"
    r"stories|storybook|__tests__|__mocks__|tests?|test|spec|specs|e2e|cypress/integration|"
    r"docs?|documentacion|examples?|ejemplos?)/",
    re.IGNORECASE,
)

SEGURA_EXTENSION = re.compile(
    r"\.(css|scss|sass|less|styl|pcss|"
    r"md|mdx|markdown|txt|rst|"
    r"svg|png|jpe?g|gif|webp|avif|ico|bmp|"
    r"woff2?|ttf|otf|eot|"
    r"mp4|webm|mov|mp3|wav|"
    r"csv|po|pot|xliff)$",
    re.IGNORECASE,
)

SEGURA_NOMBRE = re.compile(
    r"(^|/)(README|CHANGELOG|CONTRIBUTING|LICENSE|CODE_OF_CONDUCT|TODO|NOTES)"
    r"(\.[a-z]+)?$|"
    r"(^|/)(page|layout|template|loading|error|not-found|global-error|default)\.[jt]sx?$",
    re.IGNORECASE,
)

SEGURA_SUFIJO = re.compile(r"\.(test|spec|stories|story|mock|fixture)\.[a-z]+$", re.IGNORECASE)

# Un archivo con estos nombres es sospechoso aunque viva en una carpeta segura:
# `src/ui/config.ts` o `src/components/cliente-db.ts` no son "pantallas".
NOMBRE_SOSPECHOSO = re.compile(
    r"(^|/|_|-)(config|configuracion|settings|client|cliente|conexion|connection|"
    r"db|database|api|admin|token|key|llave|secret|password|clave|env|"
    r"payment|pago|checkout|upload|email|correo|sms)($|_|-|\.)",
    re.IGNORECASE,
)

# ------------------------------------------------------ contenido peligroso
# Un archivo "seguro" puede volverse sensible por lo que se le escribe adentro.
CONTENIDO_RIESGOSO = [
    (
        "backend",
        "una pantalla a la que le estás dando permisos que no tenía",
        re.compile(r"""^\s*['"]use server['"]|\bcreateServerClient\b|\bSERVICE_ROLE\b""", re.M),
        ["esa pantalla pasa a tener permisos que antes no tenía"],
    ),
    (
        "secretos",
        "una llave de acceso escrita a mano dentro del proyecto",
        re.compile(
            r"(sk_live_|rk_live_|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{20,}|xox[baprs]-|"
            r"-----BEGIN [A-Z ]*PRIVATE KEY-----|eyJhbGciOi[A-Za-z0-9_-]{20,}|"
            r"service_role[\"'\s:=]+ey)"
        ),
        ["una credencial en el repo queda expuesta para siempre, aunque la borres después"],
    ),
    (
        "db",
        "una orden que borra o cambia información de verdad",
        re.compile(
            r"\b(drop|truncate)\s+(table|database|schema|column)\b|\balter\s+table\b|"
            r"\bdelete\s+from\b(?!.*\bwhere\b)",
            re.I,
        ),
        ["puede borrar información real sin poder recuperarla"],
    ),
]

# ----------------------------------------------------------------- eliminación
# ÚNICA excepción a "nunca bloquear": borrar está prohibido, no se puede
# aceptar. Se devuelve "deny", no "ask". Lo pedido explícitamente por Woob.
BORRADO_COMANDO = [
    (
        r"\brm\b|\brmdir\b|\bunlink\b|\bshred\b|\bfind\b[^|]*-delete\b|"
        r"\bgit\s+(rm\b|clean\s+-[a-z]*f)|\bgit\s+branch\s+-D\b|"
        r"\bgit\s+push\b[^|]*--delete\b|\btruncate\b|\bdd\s+of=",
        "borrar archivos",
    ),
    (
        r"\b(drop|truncate)\s+(table|database|schema|column|index|view)\b|"
        r"\bdelete\s+from\b|\bdrop\s+if\s+exists\b|"
        r"(prisma|supabase|rails|artisan)\s+.*\b(reset|drop|wipe)\b|"
        r"\bdb:(drop|reset|purge)\b|\bflushall\b|\bflushdb\b|\bdropdb\b",
        "borrar información de clientes",
    ),
    (
        r"\bterraform\s+destroy\b|\bkubectl\s+delete\b|"
        r"\b(docker)\s+(rm|rmi|system\s+prune|volume\s+rm|container\s+prune)\b|"
        r"\baws\s+s3\s+(rm|rb)\b|\bgcloud\s+.*\bdelete\b|\baz\s+.*\bdelete\b|"
        r"\b(vercel|netlify|fly|heroku|railway)\s+.*\b(remove|rm|destroy|delete)\b|"
        r"\bgh\s+(repo|release|secret)\s+delete\b|\bsupabase\s+projects\s+delete\b",
        "borrar cosas del sitio en línea",
    ),
    (
        r"\b(npm|pnpm|yarn|bun)\s+(uninstall|remove|rm)\b|\bpip\s+uninstall\b|"
        r"\b(gem|composer|cargo)\s+(uninstall|remove)\b",
        "sacar piezas que el proyecto necesita",
    ),
]

BORRADO_MCP = re.compile(
    r"(^|_)(delete|remove|destroy|drop|purge|clear|wipe|"
    r"eliminar|borrar|quitar|limpiar|vaciar)($|_)",
    re.IGNORECASE,
)

RIESGO_BORRADO = [
    "lo que se borra no siempre se puede recuperar",
    "no hay forma de saber desde acá qué más dependía de eso",
]


def revisar_borrado_comando(cmd):
    for patron, que in BORRADO_COMANDO:
        if re.search(patron, cmd, re.IGNORECASE):
            corto = cmd if len(cmd) <= 90 else cmd[:87] + "..."
            return "borrado", que, corto, RIESGO_BORRADO
    return None


# ------------------------------------------------------------------- comandos
ZONAS_COMANDO = [
    (
        "db",
        "la información de los clientes, en vivo",
        r"\b(drop|truncate)\s+(table|database|schema)\b|\balter\s+table\b|\bdelete\s+from\b|"
        r"\bpsql\b|\bmysql\b|\bmongo(sh|dump|restore)?\b|\bredis-cli\b|"
        r"prisma\s+(migrate|db\s+push|db\s+seed)|supabase\s+db|\bpg_(dump|restore)\b|"
        r"\b(alembic|knex|sequelize|drizzle-kit|typeorm)\b|"
        r"(rails|php artisan|django-admin|manage\.py)\s+.*(migrat|db)",
        ["puede borrar información real sin poder recuperarla"],
    ),
    (
        "infra",
        "el sitio que están usando los clientes ahora mismo",
        r"\b(vercel|netlify|fly|heroku|railway|wrangler|firebase|gcloud|aws|eb)\s+\w*\s*deploy|"
        r"\bdocker\s+push\b|\bterraform\s+(apply|destroy)\b|\bkubectl\s+(apply|delete|scale)\b|"
        r"\bpm2\s+(restart|reload|delete)\b|\bsystemctl\b|--prod\b|--production\b|"
        r"\bfirebase\s+deploy\b|\bserverless\s+deploy\b",
        ["afecta el sitio que están usando los clientes ahora mismo"],
    ),
    (
        "eval",
        "una forma de escribir archivos sin decir cuáles",
        r"\b(python3?|node|ruby|perl|php)\s+-(c|e)\b|\beval\b|"
        r"<<\s*[\'\"]?(EOF|PY|SH|JSON)[\'\"]?|\bbase64\s+-[dD]\b|\bxargs\b",
        [
            "por esta vía se puede escribir cualquier archivo sin que se note cuál",
            "no podemos saber qué archivo toca hasta que ya lo tocó",
        ],
    ),
    (
        "destructivo",
        "un comando que borra cosas sin vuelta atrás",
        r"\brm\s+-[a-zA-Z]*[rf]|\bgit\s+push\b.*(--force|-f\b)|\bgit\s+reset\s+--hard\b|"
        r"\bgit\s+clean\s+-[a-z]*f|\bgit\s+(checkout|restore)\s+\.|\bgit\s+branch\s+-D\b|"
        r"\bfind\b.*-delete\b|\bshred\b|\bmkfs\b|\bdd\s+of=",
        ["borra trabajo sin papelera de reciclaje"],
    ),
    (
        "secretos",
        "las llaves de acceso del sistema",
        r"\b(export|set)\s+[A-Z_]*(KEY|TOKEN|SECRET|PASSWORD|PASSWD|DSN)\b|\bgh\s+secret\b|"
        r"\b(vercel|fly|heroku|railway)\s+(env|secrets)\b|\bsupabase\s+secrets\b|"
        r"\bopenssl\s+(genrsa|rsa|req)\b",
        ["una llave mal puesta queda registrada y a la vista"],
    ),
    (
        "script",
        "un atajo que puede hacer varias cosas de golpe",
        r"\b(npm|pnpm|yarn|bun)\s+run\s+(?!dev\b|start\b|test\b|lint\b|format\b|"
        r"typecheck\b|check\b|build\b|storybook\b)\S+|"
        r"\b(make|just)\s+\S+|\b(bash|sh|zsh|source)\s+\S+\.(sh|bash|zsh)\b|(^|\s)\./\S+\.(sh|py|js)\b|"
        r"\bcurl\b[^|]*\|\s*(bash|sh|zsh)\b",
        [
            "un atajo así puede tocar la información de los clientes o el sitio en vivo sin avisar",
            "no se ve desde afuera qué es lo que va a hacer",
        ],
    ),
    (
        "build",
        "las piezas que el proyecto necesita para armarse",
        r"\b(npm|pnpm|yarn|bun)\s+(i|install|add|remove|uninstall|update|upgrade)\b|"
        r"\bpip\s+(install|uninstall)\b|\b(gem|composer|cargo|go)\s+(install|get|add|remove)\b",
        ["cambia las piezas del proyecto para todo el equipo"],
    ),
]

# Comandos de solo lectura: pasan sin aviso.
COMANDO_SEGURO = re.compile(
    r"^\s*(ls|ll|pwd|cd|cat|head|tail|less|more|wc|file|stat|tree|du|df|which|type|whoami|"
    r"echo|printf|date|env|grep|rg|ag|ack|find|fd|sort|uniq|cut|awk|sed(?!\s+-[a-z]*i)|jq|"
    r"diff|open|code|node\s+-v|"
    r"(npm|pnpm|yarn|bun)\s+(run\s+)?(dev|start|test|lint|format|typecheck|check|"
    r"build|storybook|ls|list|outdated|why|-v|--version)\b|"
    r"python3?\s+-(m\s+)?(json|-version)|"
    r"git\s+(status|log|diff|show|branch(?!\s+-D)|remote|blame|stash\s+list|fetch|ls-files)|"
    r"gh\s+(pr\s+(list|view|diff)|issue\s+(list|view)|repo\s+view)|"
    r"curl\s+-[a-zA-Z]*[Is]\b|ping|host|dig|nslookup)\b",
    re.IGNORECASE,
)

# Escrituras por shell: capturan el archivo destino y lo evalúan como archivo.
ESCRITURA_SHELL = re.compile(
    r"(?:>>?|\btee\b(?:\s+-a)?|\bsed\s+-[a-z]*i[a-z]*\b(?:\s+\S+)?|\btruncate\b|"
    r"\b(?:mv|cp|install|touch|chmod|chown|rm)\b(?:\s+-\S+)*)\s+([^\s;|&><]+)"
)


def leer_entrada():
    try:
        return json.load(sys.stdin)
    except Exception:
        return {}


def archivo_de(tool_input):
    for k in ("file_path", "notebook_path", "path", "filePath", "target_file"):
        v = tool_input.get(k)
        if isinstance(v, str) and v:
            return v
    return ""


def contenido_de(tool_input):
    partes = []
    for k in ("content", "new_string", "new_source", "edits"):
        v = tool_input.get(k)
        if isinstance(v, str):
            partes.append(v)
        elif isinstance(v, list):
            for e in v:
                if isinstance(e, dict):
                    partes.append(str(e.get("new_string", "")))
    return "\n".join(partes)


def relativizar(ruta):
    rel = (ruta or "").replace(os.sep, "/")
    proyecto = (os.environ.get("CLAUDE_PROJECT_DIR") or "").replace(os.sep, "/").rstrip("/")
    if proyecto and rel.startswith(proyecto + "/"):
        rel = rel[len(proyecto) + 1:]
    while rel.startswith("./"):
        rel = rel[2:]
    return rel.lstrip("/")


def es_segura(rel):
    if SEGURA_SUFIJO.search(rel) or SEGURA_NOMBRE.search(rel):
        return True
    if SEGURA_EXTENSION.search(rel):
        return True
    if not SEGURA_CARPETA.search(rel):
        return False
    # Está en carpeta segura, pero el nombre delata que no es solo pantalla.
    return not (PROTEGE_DATOS and NOMBRE_SOSPECHOSO.search(rel))


def revisar_archivo(ruta, contenido="", vaciando=False):
    """(clave, etiqueta, objetivo, riesgos) o None."""
    rel = relativizar(ruta)
    if not rel:
        return None

    if vaciando:
        return ("borrado", "dejar vacío un archivo que ya existe", rel,
                ["se pierde todo lo que tenía adentro", "no siempre se puede recuperar"])

    for clave, etiqueta, patron, riesgos in ZONAS_ARCHIVO:
        if re.search(patron, rel, re.IGNORECASE):
            return clave, etiqueta, rel, riesgos

    if contenido:
        for clave, etiqueta, patron, riesgos in CONTENIDO_RIESGOSO:
            if patron.search(contenido):
                return clave, etiqueta, rel, riesgos

    if es_segura(rel):
        return None

    return (
        "desconocida",
        "un archivo que está fuera de la zona segura",
        rel,
        [
            "la zona segura es: pantallas, colores, textos, imágenes, pruebas y documentación",
            "este archivo no está ahí, así que puede tener algo de lo que dependen otras partes",
        ],
    )


def revisar_comando(cmd):
    if not cmd:
        return None

    prohibido = revisar_borrado_comando(cmd)
    if prohibido:
        return prohibido

    for clave, etiqueta, patron, riesgos in ZONAS_COMANDO:
        if re.search(patron, cmd, re.IGNORECASE):
            corto = cmd if len(cmd) <= 90 else cmd[:87] + "..."
            return clave, etiqueta, corto, riesgos

    # Escritura por shell sobre un archivo: se evalúa como si fuera un Edit.
    for destino in ESCRITURA_SHELL.findall(cmd):
        if destino.startswith("/dev/") or destino in ("-", "&1", "&2"):
            continue
        hallazgo = revisar_archivo(destino)
        if hallazgo:
            clave, etiqueta, rel, riesgos = hallazgo
            return clave, etiqueta, f"{rel} (por shell)", riesgos

    # Cada tramo por separado: "cat x && npm run migrate" no es seguro solo
    # porque empiece con `cat`.
    tramos = [t.strip() for t in re.split(r"&&|\|\||;|\||\n", cmd) if t.strip()]
    if tramos and all(COMANDO_SEGURO.match(t) for t in tramos):
        return None

    if not ESTRICTO:
        return None

    corto = cmd if len(cmd) <= 90 else cmd[:87] + "..."
    return (
        "comando",
        "un comando que no reconocemos",
        corto,
        [
            "no sabemos qué hace, así que no podemos decirte qué puede romper",
            "si solo lee o muestra cosas, es inofensivo; si escribe, publica o "
            "borra, no lo es",
        ],
    )


# Herramientas externas que solo consultan: pasan sin aviso.
MCP_SOLO_LEE = re.compile(
    r"(^|_)(get|list|read|search|find|fetch|query|show|view|describe|check|"
    r"listar|detalle|resumen|buscar|ver|obtener|consultar)($|_)|"
    r"(_(list|get|detail|search)$)",
    re.IGNORECASE,
)


def revisar_mcp(tool_name, tool_input):
    corto_nombre = tool_name.split("__")[-1]
    if BORRADO_MCP.search(corto_nombre):
        return ("borrado", "borrar información real de clientes", corto_nombre,
                ["esto borra de verdad, en vivo, y no queda registro",
                 "no hay forma de volver atrás"])
    if MCP_SOLO_LEE.search(corto_nombre):
        return None
    if not PROTEGE_DATOS and not re.search(
        r"(write|create|update|delete|insert|upsert|remove|execute|sql|migrat|"
        r"deploy|push|set_|guardar|eliminar|registrar|actualizar|agregar)",
        tool_name,
        re.IGNORECASE,
    ):
        return None
    corto = tool_name.split("__")[-1]
    return (
        "mcp",
        "información real de clientes, en vivo",
        corto,
        [
            "esto no toca archivos: cambia información real de clientes, en vivo",
            "no queda registro y no hay forma de volver atrás",
        ],
    )


def ruta_estado(session_id):
    nombre = re.sub(r"[^A-Za-z0-9_.-]", "_", session_id or "sin-sesion")
    return os.path.join(tempfile.gettempdir(), f"woob-guardrail-{nombre}.json")


def estado(session_id):
    try:
        with open(ruta_estado(session_id), "r", encoding="utf-8") as f:
            datos = json.load(f)
        if isinstance(datos, dict):
            return datos
    except Exception:
        pass
    return {"aprobado": False, "bitacora": []}


def guardar_estado(session_id, datos):
    try:
        with open(ruta_estado(session_id), "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False)
    except Exception:
        pass


def nuevo_pedido(session_id):
    """Mensaje nuevo de la persona: la aprobación anterior ya no vale."""
    try:
        os.remove(ruta_estado(session_id))
    except OSError:
        pass


def anotar(session_id, clave, objetivo):
    datos = estado(session_id)
    datos["aprobado"] = True
    entrada = {"zona": clave, "que": objetivo}
    if entrada not in datos["bitacora"]:
        datos["bitacora"].append(entrada)
    guardar_estado(session_id, datos)


def mensaje(etiqueta, objetivo, riesgos):
    lineas = [
        "⚠️  Este trabajo sale de la zona segura",
        "",
        f"Mejor solicítaselo al {CONTACTO}, porque estas tocando: "
        f"{etiqueta} ({objetivo}).",
        "",
        "Qué puede salir mal:",
    ]
    lineas += [f"  • {r}" for r in riesgos]
    lineas += [
        "",
        "Esta aprobación cubre TODO este pedido: si dices que sí, sigo hasta el",
        "final sin volver a interrumpirte, y al terminar te digo exactamente qué",
        "cambié y qué conviene revisar.",
        "",
        f"Si prefieres ir a la segura, pídeselo al {CONTACTO} y no toco nada.",
        "Si asumes la responsabilidad, apruébalo: la decisión es tuya.",
    ]
    return "\n".join(lineas)


def mensaje_prohibido(etiqueta, objetivo, riesgos):
    lineas = [
        "⛔  Esto no se puede hacer",
        "",
        f"Borrar está prohibido en este proyecto. Estabas por {etiqueta} "
        f"({objetivo}).",
        "",
        "Por qué:",
    ]
    lineas += [f"  • {r}" for r in riesgos]
    lineas += [
        "",
        f"Esto no se puede aceptar ni saltar: tiene que hacerlo el {CONTACTO}.",
        "Escríbeles qué querías borrar y por qué, y ellos lo revisan.",
        "",
        "Si lo que necesitas es cambiar o reemplazar algo en vez de borrarlo, "
        "eso sí se puede: pídelo así.",
    ]
    return "\n".join(lineas)


def main():
    datos = leer_entrada()
    evento = datos.get("hook_event_name", "PreToolUse")
    tool_name = datos.get("tool_name", "") or ""
    tool_input = datos.get("tool_input", {}) or {}
    session_id = datos.get("session_id", "")

    # Mensaje nuevo: la aprobación del pedido anterior deja de valer.
    if evento == "UserPromptSubmit":
        nuevo_pedido(session_id)
        sys.exit(0)

    if tool_name == "Bash":
        hallazgo = revisar_comando(tool_input.get("command", "") or "")
    elif tool_name.startswith("mcp__"):
        hallazgo = revisar_mcp(tool_name, tool_input)
    elif archivo_de(tool_input):
        ruta = archivo_de(tool_input)
        cont = contenido_de(tool_input)
        vaciando = (
            tool_name == "Write"
            and not cont.strip()
            and os.path.exists(ruta)
            and os.path.getsize(ruta) > 0
        )
        hallazgo = revisar_archivo(ruta, cont, vaciando)
    else:
        hallazgo = None

    if not hallazgo:
        sys.exit(0)

    clave, etiqueta, objetivo, riesgos = hallazgo

    # Eliminación: prohibida. No se pregunta, no se puede aceptar.
    if clave == "borrado":
        if evento == "PostToolUse":
            sys.exit(0)
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "deny",
                        "permissionDecisionReason": mensaje_prohibido(etiqueta, objetivo, riesgos),
                    }
                }
            )
        )
        sys.exit(0)

    if evento == "PostToolUse":
        anotar(session_id, clave, objetivo)
        sys.exit(0)

    # Ya aprobaron este pedido: se trabaja sin interrumpir.
    if estado(session_id).get("aprobado"):
        sys.exit(0)

    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "ask",
                    "permissionDecisionReason": mensaje(etiqueta, objetivo, riesgos),
                }
            }
        )
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
