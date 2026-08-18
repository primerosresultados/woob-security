#!/usr/bin/env python3
"""
Guardrail Woob — advierte antes de tocar cualquier cosa fuera de la zona segura.

Modelo: LISTA BLANCA. Solo pasan sin aviso los archivos que sabemos que son
seguros (UI, estilos, textos, imágenes, tests, documentación). Todo lo demás
avisa — incluso lo que no sabemos clasificar. Es al revés de una lista negra:
lo desconocido se trata como riesgoso, no como inofensivo.

NO bloquea nunca. Devuelve permissionDecision="ask": Claude Code muestra la
advertencia y pide confirmación. Si la persona acepta, el cambio se hace igual.

Eventos:
  PreToolUse   -> detecta y pide confirmación.
  PostToolUse  -> la herramienta corrió, o sea que aceptaron esa zona:
                  se recuerda para no repetir el aviso toda la sesión.
                  (Las zonas de SIEMPRE_PREGUNTAR nunca se recuerdan.)
"""

import json
import os
import re
import sys
import tempfile

CONTACTO = "Equipo de Woob"

# Zonas cuya aceptación NO se recuerda: cada vez vuelve a preguntar.
SIEMPRE_PREGUNTAR = {"destructivo", "guardrail", "secretos", "infra", "eval", "mcp"}

# ---------------------------------------------------------------- lista negra
# Se revisa PRIMERO. Gana sobre la lista blanca: un .md dentro de .claude/
# sigue siendo sensible aunque los .md sean seguros.
# (clave, etiqueta, regex sobre la ruta, riesgos)
ZONAS_ARCHIVO = [
    (
        "guardrail",
        "la configuración de Claude Code y de este mismo guardrail",
        r"(^|/)\.claude/|(^|/)(CLAUDE|AGENTS)\.md$|(^|/)\.cursorrules$|(^|/)\.mcp\.json$",
        [
            "estarías desactivando o alterando las advertencias que te protegen",
            "un cambio acá afecta a todo el que trabaje en el repo, no solo a ti",
        ],
    ),
    (
        "db",
        "base de datos y migraciones",
        r"(^|/)(migrations?|migraciones)/|(^|/)seeds?(/|\.)|\.sql$|(^|/)alembic/|"
        r"(^|/)(knex|drizzle|sequelize)\b|supabase/|(^|/)(db|database|datos)/|"
        r"(^|/|_|-)(db|database|supabase|firestore|mongo|postgres)($|/|_|-|\.)",
        [
            "puede borrar o corromper datos reales de clientes",
            "muchas migraciones no se pueden deshacer una vez corridas",
        ],
    ),
    (
        "schema",
        "el schema y los modelos de datos",
        r"schema\.[a-z]+$|(^|/)(models?|entities|entidades|schemas?)/|\.graphql$|"
        r"(^|/)prisma/|\.prisma$|(^|/)types?/api",
        [
            "rompe todo el código que asume la forma vieja de los datos",
            "suele fallar en producción, no en local",
        ],
    ),
    (
        "auth",
        "autenticación, sesiones y permisos",
        r"(^|/|_|-)(auth|autenticacion|login|session|sesion|jwt|oauth|rbac|rls|permis|"
        r"policy|policies|politicas|guard|middleware|roles?)(s)?($|/|_|-|\.)|"
        r"\.rules$|firestore\.rules|storage\.rules",
        [
            "un error acá deja datos de un cliente visibles para otro",
            "los agujeros de permisos no se ven hasta que alguien los usa",
        ],
    ),
    (
        "secretos",
        "secretos y credenciales",
        r"(^|/)\.env|(^|/|_|-)(secrets?|credentials?|credenciales|apikeys?)($|/|_|-|\.)|"
        r"\.(pem|key|p12|pfx|jks|keystore)$|serviceAccount.*\.json$|"
        r"(^|/)\.(gitignore|dockerignore|npmrc)$",
        [
            "una credencial que entra al repo queda expuesta para siempre, aunque la borres después",
            "tocar .gitignore puede hacer que se suba al repo algo que estaba protegido",
        ],
    ),
    (
        "pagos",
        "pagos e integraciones externas",
        r"(^|/|_|-)(stripe|mercadopago|transbank|webpay|khipu|flow|paypal|payment|pagos?|"
        r"checkout|billing|facturacion|webhooks?|twilio|sendgrid|resend)($|/|_|-|\.)",
        [
            "acá se mueve plata real",
            "los webhooks fallidos no siempre se pueden reintentar",
        ],
    ),
    (
        "infra",
        "infraestructura y deploy",
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
        "el backend y la API",
        r"(^|/)(api|server|servidor|backend|routes?|rutas|controllers?|handlers?|resolvers?|"
        r"services|servicios|functions|lambdas?|edge-functions|jobs|workers?|queues?|colas|"
        r"actions|server-actions|trpc|convex|graphql|rpc|cron|scripts?)/|"
        r"\.server\.[a-z]+$|(^|/)route\.[a-z]+$|(^|/)server\.[a-z]+$",
        [
            "cambia el contrato que consumen el front y las integraciones",
            "se rompen pantallas que no estás mirando",
        ],
    ),
    (
        "build",
        "dependencias y configuración de build",
        r"(^|/)(package\.json|package-lock\.json|pnpm-lock\.yaml|yarn\.lock|bun\.lockb|"
        r"requirements.*\.txt|pyproject\.toml|poetry\.lock|Pipfile.*|Gemfile.*|go\.(mod|sum)|"
        r"Cargo\.(toml|lock)|composer\.(json|lock))$|"
        r"(^|/)(tsconfig|jsconfig).*\.json$|"
        r"(^|/)(next|vite|webpack|rollup|astro|nuxt|svelte|remix|tailwind|postcss|babel|"
        r"eslint|jest|vitest|playwright|cypress|metro)\.config\.[a-z]+$",
        [
            "puede romper el build de todo el equipo, no solo el tuyo",
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

# ------------------------------------------------------ contenido peligroso
# Un archivo "seguro" puede volverse sensible por lo que se le escribe adentro.
CONTENIDO_RIESGOSO = [
    (
        "backend",
        "código de servidor dentro de un archivo de interfaz",
        re.compile(r"""^\s*['"]use server['"]|\bcreateServerClient\b|\bSERVICE_ROLE\b""", re.M),
        ["ese archivo deja de ser front y pasa a correr en el servidor con permisos altos"],
    ),
    (
        "secretos",
        "una credencial escrita directamente en el código",
        re.compile(
            r"(sk_live_|rk_live_|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{20,}|xox[baprs]-|"
            r"-----BEGIN [A-Z ]*PRIVATE KEY-----|eyJhbGciOi[A-Za-z0-9_-]{20,}|"
            r"service_role[\"'\s:=]+ey)"
        ),
        ["una credencial en el repo queda expuesta para siempre, aunque la borres después"],
    ),
    (
        "db",
        "SQL que modifica la base de datos",
        re.compile(
            r"\b(drop|truncate)\s+(table|database|schema|column)\b|\balter\s+table\b|"
            r"\bdelete\s+from\b(?!.*\bwhere\b)",
            re.I,
        ),
        ["puede borrar datos reales de forma irreversible"],
    ),
]

# ------------------------------------------------------------------- comandos
ZONAS_COMANDO = [
    (
        "db",
        "la base de datos",
        r"\b(drop|truncate)\s+(table|database|schema)\b|\balter\s+table\b|\bdelete\s+from\b|"
        r"\bpsql\b|\bmysql\b|\bmongo(sh|dump|restore)?\b|\bredis-cli\b|"
        r"prisma\s+(migrate|db\s+push|db\s+seed)|supabase\s+db|\bpg_(dump|restore)\b|"
        r"\b(alembic|knex|sequelize|drizzle-kit|typeorm)\b|"
        r"(rails|php artisan|django-admin|manage\.py)\s+.*(migrat|db)",
        ["puede borrar datos reales de forma irreversible"],
    ),
    (
        "infra",
        "el deploy a producción",
        r"\b(vercel|netlify|fly|heroku|railway|wrangler|firebase|gcloud|aws|eb)\s+\w*\s*deploy|"
        r"\bdocker\s+push\b|\bterraform\s+(apply|destroy)\b|\bkubectl\s+(apply|delete|scale)\b|"
        r"\bpm2\s+(restart|reload|delete)\b|\bsystemctl\b|--prod\b|--production\b|"
        r"\bfirebase\s+deploy\b|\bserverless\s+deploy\b",
        ["afecta el sitio que están usando los clientes ahora mismo"],
    ),
    (
        "eval",
        "un comando que escribe archivos por un intérprete embebido",
        r"\b(python3?|node|ruby|perl|php)\s+-(c|e)\b|\beval\b|"
        r"<<\s*[\'\"]?(EOF|PY|SH|JSON)[\'\"]?|\bbase64\s+-[dD]\b|\bxargs\b",
        [
            "por esta vía se puede escribir cualquier archivo sin que se note cuál",
            "no podemos saber qué archivo toca hasta que ya lo tocó",
        ],
    ),
    (
        "destructivo",
        "un comando destructivo",
        r"\brm\s+-[a-zA-Z]*[rf]|\bgit\s+push\b.*(--force|-f\b)|\bgit\s+reset\s+--hard\b|"
        r"\bgit\s+clean\s+-[a-z]*f|\bgit\s+(checkout|restore)\s+\.|\bgit\s+branch\s+-D\b|"
        r"\bfind\b.*-delete\b|\bshred\b|\bmkfs\b|\bdd\s+of=",
        ["borra trabajo sin papelera de reciclaje"],
    ),
    (
        "secretos",
        "secretos y credenciales",
        r"\b(export|set)\s+[A-Z_]*(KEY|TOKEN|SECRET|PASSWORD|PASSWD|DSN)\b|\bgh\s+secret\b|"
        r"\b(vercel|fly|heroku|railway)\s+(env|secrets)\b|\bsupabase\s+secrets\b|"
        r"\bopenssl\s+(genrsa|rsa|req)\b",
        ["una credencial mal puesta se filtra en logs e historial"],
    ),
    (
        "script",
        "un script del proyecto que no sabemos qué hace por dentro",
        r"\b(npm|pnpm|yarn|bun)\s+run\s+(?!dev\b|start\b|test\b|lint\b|format\b|"
        r"typecheck\b|check\b|build\b|storybook\b)\S+|"
        r"\b(make|just)\s+\S+|\b(bash|sh|zsh|source)\s+\S+\.(sh|bash|zsh)\b|(^|\s)\./\S+\.(sh|py|js)\b|"
        r"\bcurl\b[^|]*\|\s*(bash|sh|zsh)\b",
        [
            "un script del package.json o un .sh puede correr migraciones o deploys por dentro",
            "abre el script y mira qué hace antes de aceptar",
        ],
    ),
    (
        "build",
        "las dependencias del proyecto",
        r"\b(npm|pnpm|yarn|bun)\s+(i|install|add|remove|uninstall|update|upgrade)\b|"
        r"\bpip\s+(install|uninstall)\b|\b(gem|composer|cargo|go)\s+(install|get|add|remove)\b",
        ["cambia el árbol de dependencias para todo el equipo"],
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
    return bool(
        SEGURA_SUFIJO.search(rel)
        or SEGURA_NOMBRE.search(rel)
        or SEGURA_EXTENSION.search(rel)
        or SEGURA_CARPETA.search(rel)
    )


def revisar_archivo(ruta, contenido=""):
    """(clave, etiqueta, objetivo, riesgos) o None."""
    rel = relativizar(ruta)
    if not rel:
        return None

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
            "la zona segura es interfaz, estilos, textos, imágenes, tests y documentación",
            "este archivo no está ahí, así que puede tener lógica de la que dependen otras partes",
        ],
    )


def revisar_comando(cmd):
    if not cmd:
        return None

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

    if COMANDO_SEGURO.match(cmd.strip()):
        return None

    return None  # comando no clasificado: se deja pasar, ver RIESGOS.md


def revisar_mcp(tool_name, tool_input):
    if not re.search(
        r"(write|create|update|delete|insert|upsert|remove|execute|sql|query|migrat|"
        r"deploy|push|set_|guardar|eliminar|registrar|actualizar|agregar)",
        tool_name,
        re.IGNORECASE,
    ):
        return None
    corto = tool_name.split("__")[-1]
    return (
        "mcp",
        "datos reales a través de una herramienta externa (MCP)",
        corto,
        [
            "esto no toca archivos: escribe directamente sobre datos de producción",
            "no hay control de versiones ni forma de revertirlo con git",
        ],
    )


def ruta_memoria(session_id):
    nombre = re.sub(r"[^A-Za-z0-9_.-]", "_", session_id or "sin-sesion")
    return os.path.join(tempfile.gettempdir(), f"woob-guardrail-{nombre}.json")


def aceptadas(session_id):
    try:
        with open(ruta_memoria(session_id), "r", encoding="utf-8") as f:
            datos = json.load(f)
            return set(datos) if isinstance(datos, list) else set()
    except Exception:
        return set()


def recordar(session_id, clave):
    if clave in SIEMPRE_PREGUNTAR:
        return
    ya = aceptadas(session_id)
    if clave in ya:
        return
    ya.add(clave)
    try:
        with open(ruta_memoria(session_id), "w", encoding="utf-8") as f:
            json.dump(sorted(ya), f)
    except Exception:
        pass


def mensaje(etiqueta, objetivo, riesgos):
    lineas = [
        "⚠️  Fuera de la zona segura",
        "",
        f"Mejor solicita este cambio al {CONTACTO}, porque estas tocando: "
        f"{etiqueta} ({objetivo}).",
        "",
        "Qué puede salir mal:",
    ]
    lineas += [f"  • {r}" for r in riesgos]
    lineas += [
        "",
        f"Si prefieres ir a la segura, pídeselo al {CONTACTO} y no toques nada.",
        "Si aceptas la responsabilidad de este cambio, apruébalo y sigue: "
        "nadie te está bloqueando, la decisión es tuya.",
    ]
    return "\n".join(lineas)


def main():
    datos = leer_entrada()
    evento = datos.get("hook_event_name", "PreToolUse")
    tool_name = datos.get("tool_name", "") or ""
    tool_input = datos.get("tool_input", {}) or {}
    session_id = datos.get("session_id", "")

    if tool_name == "Bash":
        hallazgo = revisar_comando(tool_input.get("command", "") or "")
    elif tool_name.startswith("mcp__"):
        hallazgo = revisar_mcp(tool_name, tool_input)
    elif archivo_de(tool_input):
        hallazgo = revisar_archivo(archivo_de(tool_input), contenido_de(tool_input))
    else:
        hallazgo = None

    if not hallazgo:
        sys.exit(0)

    clave, etiqueta, objetivo, riesgos = hallazgo

    if evento == "PostToolUse":
        recordar(session_id, clave)
        sys.exit(0)

    if clave in aceptadas(session_id):
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
