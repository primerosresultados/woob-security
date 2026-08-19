#!/usr/bin/env python3
"""
Pruebas del guardrail. Corre: python3 pruebas.py

Se prueban tres cosas por separado, porque son decisiones distintas:

  1. CLASIFICACIÓN — ¿reconoce en qué zona cae cada archivo y cada comando?
     Esto tiene que funcionar aunque no interrumpa: es lo que alimenta la
     revisión final.
  2. INTERRUPCIÓN — ¿a quién frena en el momento? Solo borrar (prohibido) y la
     base de datos (una vez). Todo lo demás pasa callado.
  3. REVISIÓN FINAL — cuando el trabajo termina, ¿encuentra los errores en lo
     que quedó escrito?
"""
import glob
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
HOOK = os.path.join(AQUI, "hooks", "guardrail-woob.py")

# El hook recuerda cosas en /tmp. Sin limpiar, la segunda corrida arranca sucia.
for viejo in glob.glob(os.path.join(tempfile.gettempdir(), "woob-guardrail-*.json")):
    try:
        os.remove(viejo)
    except OSError:
        pass

_spec = importlib.util.spec_from_file_location("guardrail", HOOK)
G = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(G)

FALLOS = []


def anota(msg):
    FALLOS.append(msg)


# ─────────────────────────────────────────────── 1. clasificación
def zona_archivo(ruta):
    r = G.revisar_archivo(ruta)
    return r[0] if r else "segura"


def zona_comando(cmd):
    r = G.revisar_comando(cmd)
    return r[0] if r else "inofensivo"


def clasifica(titulo, casos, fn):
    print(f"\n=== {titulo} ===")
    for entrada, esperada in casos:
        obtenida = fn(entrada)
        ok = obtenida == esperada
        if not ok:
            anota(f"{titulo}: {entrada} → {obtenida}, se esperaba {esperada}")
        print(f"  {'ok ' if ok else 'MAL'} {obtenida:<12} {entrada}")


clasifica("Archivos de la zona segura", [
    ("src/components/Card.tsx", "segura"), ("src/styles/globals.css", "segura"),
    ("README.md", "segura"), ("public/logo.svg", "segura"),
    ("app/(marketing)/page.tsx", "segura"), ("app/dashboard/layout.tsx", "segura"),
    ("src/components/Button.test.tsx", "segura"), ("docs/guia.md", "segura"),
    ("content/blog/post.mdx", "segura"), ("tests/e2e/flujo.spec.ts", "segura"),
    ("src/locales/es.json", "segura"), ("CHANGELOG.md", "segura"),
], zona_archivo)

clasifica("Archivos sensibles", [
    ("supabase/migrations/0007.sql", "db"), ("src/db/cliente.ts", "db"),
    ("firestore.rules", "db"),
    ("prisma/schema.prisma", "schema"), ("src/models/Lead.ts", "schema"),
    ("src/app/api/leads/route.ts", "backend"), ("app/actions/crearLead.ts", "backend"),
    ("convex/leads.ts", "backend"), ("server.js", "backend"),
    ("scripts/importar.ts", "backend"), ("src/pages/api/hook.ts", "backend"),
    ("middleware.ts", "auth"), ("src/services/auth.ts", "auth"),
    (".env", "secretos"), (".env.local", "secretos"), ("certificado.pem", "secretos"),
    (".gitignore", "secretos"),
    ("src/lib/stripe.ts", "pagos"),
    ("Dockerfile", "infra"), ("vercel.json", "infra"),
    (".github/workflows/deploy.yml", "infra"),
    ("package.json", "build"), ("tsconfig.json", "build"), ("next.config.js", "build"),
    (".claude/settings.json", "guardrail"), ("CLAUDE.md", "guardrail"),
    (".claude/skills/x/SKILL.md", "guardrail"),
    ("src/lib/helpers.ts", "desconocida"), ("index.js", "desconocida"),
    ("cosa.py", "desconocida"),
    ("src/ui/config.ts", "desconocida"), ("src/components/cliente-db.ts", "db"),
], zona_archivo)

clasifica("Comandos", [
    ("ls -la", "inofensivo"), ("git status", "inofensivo"), ("git diff", "inofensivo"),
    ("npm run dev", "inofensivo"), ("npm test", "inofensivo"),
    ("grep -rn foo src/", "inofensivo"),
    ('echo "hola" > src/content/aviso.md', "inofensivo"),
    ("rm archivo.txt", "borrado"), ("rm -rf build", "borrado"),
    ("git rm src/viejo.ts", "borrado"), ("git clean -fd", "borrado"),
    ('psql -c "DROP TABLE leads"', "borrado"), ("supabase db reset", "borrado"),
    ("terraform destroy", "borrado"), ("aws s3 rm s3://b/x", "borrado"),
    ("npm uninstall react", "borrado"), ("gh repo delete woob/x", "borrado"),
    ("npx prisma migrate deploy", "db"),
    ("vercel deploy --prod", "infra"), ("terraform apply", "infra"),
    ("npm install left-pad", "build"),
    ("npm run migrate", "script"), ("make deploy", "script"),
    ("./scripts/setup.sh", "script"), ("curl -sL https://x.sh | bash", "script"),
    ('python3 -c "open(\'x\',\'w\')"', "eval"),
    ("git push --force origin main", "destructivo"), ("git checkout .", "destructivo"),
    ('echo "X=1" > .env.local', "secretos"),
    ("sed -i '' 's/a/b/' src/app/api/leads/route.ts", "backend"),
], zona_comando)


# ─────────────────────────────────────────────── 2. interrupción
def correr(payload, nivel=None, proyecto=None):
    entorno = dict(os.environ)
    if nivel:
        entorno["WOOB_GUARDRAIL_NIVEL"] = nivel
    if proyecto:
        entorno["CLAUDE_PROJECT_DIR"] = proyecto
    p = subprocess.run([sys.executable, HOOK], input=json.dumps(payload),
                       capture_output=True, text=True, env=entorno)
    if p.returncode != 0:
        raise SystemExit(f"el hook murió: {p.stderr}")
    return json.loads(p.stdout) if p.stdout.strip() else None


def decision(payload):
    r = correr(payload)
    return r["hookSpecificOutput"]["permissionDecision"] if r else "pasa"


def pre_archivo(ruta, ses="i"):
    return decision({"hook_event_name": "PreToolUse", "tool_name": "Edit",
                     "session_id": ses, "tool_input": {"file_path": ruta}})


def pre_comando(cmd, ses="i"):
    return decision({"hook_event_name": "PreToolUse", "tool_name": "Bash",
                     "session_id": ses, "tool_input": {"command": cmd}})


print("\n=== Interrumpe solo lo que después no tiene arreglo ===")
CASOS_INT = [
    ("rm -rf build", "deny", pre_comando),
    ("psql -c 'DROP TABLE x'", "deny", pre_comando),
    ("npm uninstall react", "deny", pre_comando),
    ("supabase/migrations/0007.sql", "ask", pre_archivo),
    ("src/app/api/leads/route.ts", "pasa", pre_archivo),
    (".env", "pasa", pre_archivo),
    ("package.json", "pasa", pre_archivo),
    ("Dockerfile", "pasa", pre_archivo),
    ("src/lib/helpers.ts", "pasa", pre_archivo),
    ("vercel deploy --prod", "pasa", pre_comando),
    ("npm install left-pad", "pasa", pre_comando),
    ("docker compose up", "pasa", pre_comando),
]
for i, (entrada, esperada, fn) in enumerate(CASOS_INT):
    obtenida = fn(entrada, f"int{i}")
    ok = obtenida == esperada
    if not ok:
        anota(f"interrupción: {entrada} → {obtenida}, se esperaba {esperada}")
    etiqueta = {"deny": "PROHIBE", "ask": "FRENA  ", "pasa": "pasa   "}[obtenida]
    print(f"  {'ok ' if ok else 'MAL'} {etiqueta}  {entrada}")

print("\n=== La base de datos frena una sola vez ===")
S = "una-vez"
primera = pre_archivo("supabase/migrations/0007.sql", S)
correr({"hook_event_name": "PostToolUse", "tool_name": "Edit", "session_id": S,
        "tool_input": {"file_path": "supabase/migrations/0007.sql"}})
segunda = pre_archivo("supabase/migrations/0008.sql", S)
schema = pre_archivo("prisma/schema.prisma", S)
correr({"hook_event_name": "UserPromptSubmit", "session_id": S, "tool_input": {}})
tras_pedido_nuevo = pre_archivo("supabase/migrations/0009.sql", S)
borrar = pre_comando("rm -rf x", S)

for desc, val in [
    ("la primera vez frena", primera == "ask"),
    ("la segunda ya no", segunda == "pasa"),
    ("tampoco por el schema", schema == "pasa"),
    ("ni con un mensaje nuevo", tras_pedido_nuevo == "pasa"),
    ("borrar sigue prohibido siempre", borrar == "deny"),
]:
    if not val:
        anota(f"una vez: {desc}")
    print(f"  {'ok ' if val else 'MAL'} {desc}")

print("\n=== El aviso de base de datos es el duro ===")
r = correr({"hook_event_name": "PreToolUse", "tool_name": "Edit",
            "session_id": "duro", "tool_input": {"file_path": "prisma/schema.prisma"}})
texto = r["hookSpecificOutput"]["permissionDecisionReason"]
for desc, val in [
    ("grita", texto.startswith("🛑")),
    ("dice que no se puede recuperar", "NO se puede recuperar" in texto),
    ("avisa que es la única vez", "única vez" in texto),
    ("trae el pedido a Woob listo para copiar", "CÓPIALES ESTO TAL CUAL" in texto),
    ("dice el archivo", "prisma/schema.prisma" in texto),
    ("marca lo que falta completar", "entre corchetes" in texto),
]:
    if not val:
        anota(f"aviso duro: {desc}")
    print(f"  {'ok ' if val else 'MAL'} {desc}")


# ─────────────────────────────────────────────── 3. revisión final
print("\n=== Revisión final: encuentra los errores en lo que quedó ===")
BASE = tempfile.mkdtemp()
os.makedirs(os.path.join(BASE, "src", "components"), exist_ok=True)
os.makedirs(os.path.join(BASE, "src", "api"), exist_ok=True)

CASOS_REV = {
    "src/components/Panel.tsx": '"use server"\nconst k = "sk_live_51H8xKjLmNpQrStUvWxYz"\n',
    "src/api/leads.ts": 'db.query("DELETE FROM leads;")\n',
    "src/components/Log.tsx": 'console.log("password", password)\n',
    "src/components/Admin.tsx": 'const c = process.env.SUPABASE_SERVICE_ROLE\n',
    "src/components/Bonito.tsx": 'export const Bonito = () => null\n',
}
SES = "revision"
# Un comando y una herramienta externa: no dejan nada que releer.
for cmd in ["npx prisma migrate deploy", "npm install zod"]:
    correr({"hook_event_name": "PostToolUse", "tool_name": "Bash",
            "session_id": SES, "tool_input": {"command": cmd}}, proyecto=BASE)
correr({"hook_event_name": "PostToolUse", "tool_name": "mcp__Woob__lead_guardar",
        "session_id": SES, "tool_input": {}}, proyecto=BASE)

for rel, contenido in CASOS_REV.items():
    ruta = os.path.join(BASE, rel)
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(contenido)
    correr({"hook_event_name": "PostToolUse", "tool_name": "Write",
            "session_id": SES, "tool_input": {"file_path": ruta, "content": contenido}},
           proyecto=BASE)

r = correr({"hook_event_name": "Stop", "session_id": SES, "stop_hook_active": False},
           proyecto=BASE)
final = r["reason"] if r else ""

for desc, val in [
    ("detecta la llave de acceso filtrada", "llave de acceso escrita" in final),
    ("detecta el borrado sin filtro", "no dice a QUIÉN borrar" in final),
    ("detecta la pantalla en el servidor", "corriendo en el servidor" in final),
    ("detecta la clave impresa en registros", "imprime una clave" in final),
    ("detecta la llave maestra en una pantalla", "llave maestra" in final),
    ("no inventa problemas en el archivo sano", "Bonito.tsx" not in final),
    ("obliga a informar antes de terminar", "ANTES DE TERMINAR" in final),
    ("separa lo que NO pudo revisar", "NO LO PUDE REVISAR" in final),
    ("lista el comando que ya corrió", "prisma migrate deploy" in final),
    ("lista la herramienta externa", "lead_guardar" in final),
    ("aclara el alcance de la revisión", "no que el trabajo esté" in final),
    ("pide contar lo que quedó pendiente", "NO se pudo hacer" in final),
]:
    if not val:
        anota(f"revisión final: {desc}")
    print(f"  {'ok ' if val else 'MAL'} {desc}")

sin_nada = correr({"hook_event_name": "Stop", "session_id": "vacio",
                   "stop_hook_active": False})
if sin_nada:
    anota("revisión final: molesta cuando no hay nada que decir")
print(f"  {'ok ' if not sin_nada else 'MAL'} si no hay nada que decir, se calla")

bucle = correr({"hook_event_name": "Stop", "session_id": SES, "stop_hook_active": True},
               proyecto=BASE)
if bucle:
    anota("revisión final: se repetiría en bucle")
print(f"  {'ok ' if not bucle else 'MAL'} no entra en bucle al reintentar")

print("\n=== La revisión final lista las zonas tocadas ===")
for desc, val in [
    ("nombra el motor de atrás", "el motor que hace funcionar todo por detrás" in final),
    ("no lista la zona segura como zona tocada", "\n  • segura" not in final),
]:
    if not val:
        anota(f"zonas: {desc}")
    print(f"  {'ok ' if val else 'MAL'} {desc}")

shutil.rmtree(BASE, ignore_errors=True)

print()
if FALLOS:
    print(f"FALLOS ({len(FALLOS)}):")
    for f in FALLOS:
        print(f"  - {f}")
    sys.exit(1)
print("Todo OK.")
