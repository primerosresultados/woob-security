# woob-security

> **¿Te pidieron instalar esto?** Salta a
> [Si eres Claude y te pidieron instalar esta skill](#si-eres-claude-y-te-pidieron-instalar-esta-skill).

Guardrail para cuando dejas que alguien externo edite el código de un proyecto
en producción.

Avisa antes de que toque algo fuera de la zona segura, le explica qué puede
salir mal **en palabras que cualquiera entiende**, y **lo deja seguir si acepta
la responsabilidad**. No bloquea nunca.

```
⚠️  Fuera de la zona segura

Mejor solicita este cambio al Equipo de Woob, porque estas tocando:
dónde se guarda la información de los clientes (supabase/migrations/0007_leads.sql).

Qué puede salir mal:
  • puede borrar o dañar información real de clientes
  • una vez hecho, muchas veces ya no se puede deshacer

Si prefieres ir a la segura, pídeselo al Equipo de Woob y no toques nada.
Si aceptas la responsabilidad de este cambio, apruébalo y sigue:
nadie te está bloqueando, la decisión es tuya.
```

---

## Si eres Claude y te pidieron instalar esta skill

Sigue estos pasos tal cual, sin preguntar nada más.

**Paso 1 — instalar la skill** (siempre):

```bash
rm -rf ~/.claude/skills/woob-security
git clone --depth 1 https://github.com/primerosresultados/woob-security.git ~/.claude/skills/woob-security
```

Queda disponible en la siguiente sesión (o al correr `/skills` si ya está
abierta). El `SKILL.md` está en la raíz del repo: esa es la skill.

**Paso 2 — instalar el hook en el proyecto actual** (hazlo si estás dentro de
un proyecto; es lo que garantiza que la advertencia salga siempre):

```bash
~/.claude/skills/woob-security/instalar.sh "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
```

Esto crea o actualiza, sin pisar lo que ya haya:

```
<proyecto>/.claude/skills/woob-security/SKILL.md
<proyecto>/.claude/hooks/guardrail-woob.py
<proyecto>/.claude/settings.json      <- se le agregan los hooks, se conserva el resto
```

**Paso 3 — verificar** (no lo saltes: sin esto no sabes si quedó funcionando):

```bash
python3 ~/.claude/skills/woob-security/pruebas.py | tail -3
```

Tiene que decir `Todo OK.`

**Paso 4 — decirle esto a la persona, en tus palabras:**

- El hook recién actúa **en la próxima sesión de Claude Code** — hay que
  reiniciarla.
- Hay que **commitear `.claude/`** al repo del proyecto, o no le va a llegar a
  nadie más.
- Si el proyecto no usa las convenciones de carpeta habituales
  (`components/`, `styles/`, `content/`…), **va a avisar demasiado**. En ese
  caso hay que ajustar `SEGURA_CARPETA` en `hooks/guardrail-woob.py`. Un
  guardrail que grita siempre es ruido y la gente lo aprende a ignorar.
- Esto **no reemplaza** branch protection ni permisos de base de datos:
  ver [RIESGOS.md](RIESGOS.md).

**Si algo falla:**

| Síntoma | Causa | Qué hacer |
|---|---|---|
| `python3: command not found` | No hay Python | Instalarlo. Sin él el hook **falla abierto** y no avisa nada. |
| El hook no dispara | La sesión no se reinició | Reiniciar Claude Code. |
| El hook no dispara | `settings.json` sin el bloque `hooks` | Volver a correr `instalar.sh`. |
| Avisa en todo | Convenciones distintas | Ajustar `SEGURA_CARPETA`. |

**No hagas esto:** no edites el `settings.json` del proyecto a mano para
agregar los hooks — usa `instalar.sh`, que hace el merge sin romper los
permisos que ya estén configurados.

---

## Instalar a mano

**En un proyecto** (lo normal — así le llega a quien vaya a editarlo):

```bash
git clone https://github.com/primerosresultados/woob-security.git
cd woob-security
./instalar.sh /ruta/a/tu/proyecto
```

Deja la skill en `.claude/skills/woob-security/` y el hook en `.claude/hooks/`.
Después commitea esa carpeta al repo del proyecto: así viaja con el código y
funciona en la máquina de la otra persona.

**En todas tus sesiones** (el repo es una skill, se clona y ya):

```bash
git clone https://github.com/primerosresultados/woob-security.git ~/.claude/skills/woob-security
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
pantallas · colores · textos · imágenes · pruebas · documentación

**Todo lo demás avisa**, con nombre propio cuando lo reconoce:
dónde se guarda la información de los clientes · cómo está organizada · el
motor de atrás · quién puede entrar y qué ve cada uno · las llaves de acceso ·
lo que mantiene el sitio en línea · las piezas del proyecto · los cobros · los
avisos de seguridad mismos · comandos que borran sin vuelta atrás.

Y con nombre genérico cuando no: *"un archivo que está fuera de la zona segura"*.

## Todo se dice en simple

La persona que lee el aviso puede no saber qué es una migración, un endpoint o
un token. Si no entiende el aviso, lo acepta sin leer — y ahí el aviso no
sirvió de nada.

Por eso ni el hook ni la skill usan una sola palabra técnica. `SKILL.md` trae
un diccionario de traducción y la regla de fondo: **explica la consecuencia, no
el mecanismo.**

| No se dice | Se dice |
|---|---|
| base de datos, migración, SQL | dónde se guarda la información de los clientes |
| schema, modelo, tabla | cómo está organizada la información |
| backend, API, endpoint | el motor que hace funcionar todo por detrás |
| autenticación, token, RLS | quién puede entrar y qué puede ver cada persona |
| variables de entorno, secretos | las llaves de acceso del sistema |
| infraestructura, deploy | lo que mantiene el sitio en línea |
| dependencias, build, lockfile | las piezas que el proyecto necesita para armarse |
| irreversible | no se puede deshacer |
| breaking change | otras pantallas dejan de funcionar |
| producción | el sitio que están usando los clientes ahora mismo |

La única excepción es el nombre del archivo o el comando: ese va tal cual,
porque es lo único que ubica a la persona en dónde está parada.

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
