# woob-security

Guardrail para cuando dejas que alguien externo edite el código de un proyecto
en producción.

Avisa antes de que toque algo fuera de la zona segura, le explica qué puede
salir mal, y **lo deja seguir si acepta la responsabilidad**. No bloquea nunca.

```
⚠️  Fuera de la zona segura

Mejor solicita este cambio al Equipo de Woob, porque estas tocando:
base de datos y migraciones (supabase/migrations/0007_leads.sql).

Qué puede salir mal:
  • puede borrar o corromper datos reales de clientes
  • muchas migraciones no se pueden deshacer una vez corridas

Si prefieres ir a la segura, pídeselo al Equipo de Woob y no toques nada.
Si aceptas la responsabilidad de este cambio, apruébalo y sigue:
nadie te está bloqueando, la decisión es tuya.
```

## Instalar

**En un proyecto** (lo normal — así le llega a quien vaya a editarlo):

```bash
git clone https://github.com/<usuario>/woob-security.git
cd woob-security
./instalar.sh /ruta/a/tu/proyecto
```

Deja la skill en `.claude/skills/woob-security/` y el hook en `.claude/hooks/`.
Después commitea esa carpeta al repo del proyecto: así viaja con el código y
funciona en la máquina de la otra persona.

**En todas tus sesiones** (el repo es una skill, se clona y ya):

```bash
git clone https://github.com/<usuario>/woob-security.git ~/.claude/skills/woob-security
```

Ojo: así solo tienes la skill, no el hook. El hook se instala por proyecto,
porque se engancha en el `settings.json` del proyecto.

## Cómo funciona

Dos capas, a propósito redundantes:

| | |
|---|---|
| `SKILL.md` | La skill. Le enseña a Claude *cómo* advertir bien, qué riesgo nombrar y — sobre todo — que después de la advertencia haga el trabajo completo, sin sermonear y sin recortarlo. |
| `hooks/guardrail-woob.py` | El hook `PreToolUse`. Intercepta `Edit`, `Write`, `Bash` y herramientas MCP **antes** de que corran y fuerza la confirmación. |

El hook es el candado; garantiza que el aviso salga aunque el modelo se
distraiga. La skill es la que hace que el aviso sirva de algo. Por separado
cada una es la mitad.

## Lista blanca, no lista negra

La decisión de diseño que importa: **no adivinamos qué es peligroso, definimos
qué es seguro.** Todo lo demás avisa, incluso lo que no sabemos clasificar.

Una lista negra siempre tiene agujeros — `src/lib/helpers.ts` no parece
peligroso hasta que resulta que ahí vive la conexión a la base de datos.

**Zona segura** (pasa sin avisos):
interfaz · estilos · textos y traducciones · imágenes y fuentes · tests · docs

**Todo lo demás avisa**, con nombre propio cuando lo reconoce:
base de datos y migraciones · schema y modelos · backend y API · auth y
permisos · secretos y `.env` · infra y deploy · dependencias y build · pagos y
webhooks · el guardrail mismo (`.claude/`) · comandos destructivos.

Y con nombre genérico cuando no: *"un archivo que está fuera de la zona segura"*.

## Detalles que importan

- **Cuando alguien acepta una zona, no se le vuelve a preguntar por esa zona en
  la sesión.** Si el aviso sale veinte veces, nadie lo lee, y ahí el guardrail
  deja de servir.
- **Salvo las zonas graves.** `destructivo`, `secretos`, `infra`, `guardrail`,
  `eval` y `mcp` preguntan siempre, aunque ya hayan aceptado antes.
- **El contenido también cuenta.** Un componente deja de ser seguro si le
  escribes `"use server"`, una API key o un `DROP TABLE`.
- **Los comandos también.** `npm run migrate`, `make deploy`, `curl | bash`,
  `python3 -c`, redirecciones a archivos sensibles.

## Antes de confiar en esto

Lee **[RIESGOS.md](RIESGOS.md)**. Es el análisis honesto de todo lo que este
guardrail *no* te salva — bypasses, límites de la detección y los riesgos del
propio diseño.

El resumen: esto reduce accidentes de gente con buena intención. No detiene a
nadie que quiera hacer daño. Branch protection y no darle credenciales de
producción valen más que todo este repo.

## Ajustar

| Qué | Dónde |
|---|---|
| Zona segura (adáptala a las convenciones de tu proyecto) | `SEGURA_CARPETA`, `SEGURA_EXTENSION` en `hooks/guardrail-woob.py` y la tabla de `SKILL.md` |
| Zonas sensibles y sus riesgos | `ZONAS_ARCHIVO`, `ZONAS_COMANDO` en el hook |
| A quién se le pide el cambio | `CONTACTO` en el hook, y el texto de `SKILL.md` |
| Qué zonas preguntan siempre | `SIEMPRE_PREGUNTAR` en el hook |

Si tocas los patrones, corre las pruebas:

```bash
python3 pruebas.py
```

## Requisitos

Claude Code y `python3` (viene con macOS y con cualquier Linux). Si falta
`python3`, el hook **falla abierto**: el aviso no sale y el cambio pasa.

## Licencia

MIT.
