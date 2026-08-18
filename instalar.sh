#!/usr/bin/env bash
# Deja la skill y el hook dentro de un proyecto, para que le lleguen a quien
# vaya a editarlo.
#   ./instalar.sh /ruta/al/proyecto
set -euo pipefail

ORIGEN="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DESTINO="${1:-}"

if [[ -z "$DESTINO" ]]; then
  echo "Uso: ./instalar.sh /ruta/al/proyecto" >&2
  echo "" >&2
  echo "Para usarla en todas tus sesiones en vez de en un proyecto:" >&2
  echo "  git clone <repo> ~/.claude/skills/woob-security" >&2
  exit 1
fi
if [[ ! -d "$DESTINO" ]]; then
  echo "No existe la carpeta: $DESTINO" >&2
  exit 1
fi
if ! command -v python3 >/dev/null 2>&1; then
  echo "AVISO: no hay python3. El hook falla abierto: no va a avisar nada." >&2
fi

mkdir -p "$DESTINO/.claude/skills/woob-security" "$DESTINO/.claude/hooks"
cp "$ORIGEN/SKILL.md" "$DESTINO/.claude/skills/woob-security/SKILL.md"
cp "$ORIGEN/hooks/guardrail-woob.py" "$DESTINO/.claude/hooks/"
chmod +x "$DESTINO/.claude/hooks/guardrail-woob.py"

# Mezcla los hooks con el settings.json que ya tenga el proyecto.
python3 - "$ORIGEN/hooks/settings-hooks.json" "$DESTINO/.claude/settings.json" <<'PY'
import json, os, sys

origen, destino = sys.argv[1], sys.argv[2]
nuevo = json.load(open(origen, encoding="utf-8"))

actual = {}
if os.path.exists(destino):
    try:
        actual = json.load(open(destino, encoding="utf-8"))
    except Exception:
        print("  ! settings.json existente no es JSON válido; se respalda como .bak")
        os.replace(destino, destino + ".bak")

hooks = actual.setdefault("hooks", {})
for evento, entradas in nuevo["hooks"].items():
    lista = hooks.setdefault(evento, [])
    for entrada in entradas:
        firma = json.dumps(entrada, sort_keys=True)
        if all(json.dumps(e, sort_keys=True) != firma for e in lista):
            lista.append(entrada)

json.dump(actual, open(destino, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
open(destino, "a", encoding="utf-8").write("\n")
PY

echo "Listo. Skill y hook instalados en: $DESTINO/.claude"
echo "Commitea .claude/ al repo para que le llegue a quien vaya a editar."
