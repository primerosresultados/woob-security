# woob-security

> **¿Te pidieron instalar esto?** Salta a
> [Si eres Claude y te pidieron instalar esta skill](#si-eres-claude-y-te-pidieron-instalar-esta-skill).

Guardrail para cuando dejas que alguien externo edite el código de un proyecto
en producción.

Avisa antes de que toque algo fuera de la zona segura, le explica qué puede
salir mal **en palabras que cualquiera entiende**, y **lo deja seguir si acepta
la responsabilidad**.

Con una sola excepción: **borrar está prohibido y no se puede aceptar.**

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
| `SKILL.md` | La skill. Le enseña a Claude *cómo* advertir bien, qué riesgo nombrar, cuándo interrumpir — y que después de la advertencia haga el trabajo completo, sin sermonear y sin recortarlo. |
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

## Borrar: lo único que se bloquea

Todo lo demás avisa y deja pasar. Las eliminaciones se rechazan de verdad
(`deny`), sin opción de aceptar:

```
⛔  Esto no se puede hacer

Borrar está prohibido en este proyecto.
Estabas por borrar archivos (rm -rf src/components/viejos).

Por qué:
  • lo que se borra no siempre se puede recuperar
  • no hay forma de saber desde acá qué más dependía de eso

Esto no se puede aceptar ni saltar: tiene que hacerlo el Equipo de Woob.

Si lo que necesitas es cambiar o reemplazar algo en vez de borrarlo,
eso sí se puede: pídelo así.
```

Cubre borrar archivos (`rm`, `git rm`, `git clean`, `find -delete`), borrar
información (`DROP`, `TRUNCATE`, `DELETE FROM`, `db reset`), borrar cosas del
sitio en línea (`terraform destroy`, `kubectl delete`, `docker prune`,
`aws s3 rm`, `vercel remove`, `gh repo delete`), sacar dependencias
(`npm uninstall`), vaciar un archivo que ya existe, y cualquier herramienta
externa cuyo nombre sea de eliminar.

La skill acompaña: en vez de solo negarse, propone la alternativa que no borra
(renombrar, comentar, marcar como inactivo, dejar de mostrarlo).

## La skill interrumpe a propósito

Un aviso que sale una vez y bajito no le cambia el comportamiento a nadie. Por
eso la skill está escrita para ser pesada:

- **Se presenta al principio.** Antes del primer cambio dice qué puede tocar
  libre y qué va a consultar.
- **Avisa antes de empezar**, no cuando ya está editando. Si el pedido va a
  salir de la zona segura, lo dice antes de escribir una línea.
- **No acepta un sí genérico.** "Dale", "hazlo" o "no preguntes más" no son
  aceptación: tiene que ser una respuesta explícita, por ese archivo. Si le
  dicen que no pregunte más, explica por qué sigue preguntando y sigue
  preguntando.
- **No esconde un cambio sensible adentro de otro.** Si mover un botón obliga a
  tocar el motor de atrás, para y avisa. Es la forma más común de que se cuele
  algo.
- **Deja la cuenta al final:** la lista de todo lo que se aceptó fuera de la
  zona segura, para pasársela a Woob.

Nada de esto bloquea. Ser pesado e impedir no son lo mismo.

## Modo estricto (por defecto)

- **Los comandos van al revés que los archivos:** avisa salvo que el comando
  sea claramente de solo lectura (`ls`, `cat`, `grep`, `git status`,
  `npm run dev`, `npm test`…). Todo lo demás pregunta, incluido lo que no
  reconoce. Y cada tramo de un comando encadenado cuenta por separado:
  `cat x && npm run migrate` no pasa por empezar con `cat`.
- **Aceptar un archivo no abre su zona.** Aceptar `0007.sql` no autoriza
  `0008.sql`. La memoria es por archivo, no por categoría.
- **Las herramientas externas (MCP) avisan casi siempre**, salvo las que solo
  consultan. Son el vector más peligroso: escriben sobre datos reales sin git,
  sin diff y sin forma de volver atrás.
- **Nombres sospechosos dentro de carpetas seguras.** `src/ui/config.ts` y
  `src/components/cliente-db.ts` avisan igual: están en zona segura pero el
  nombre delata que no son solo pantalla.
- **El contenido también cuenta.** Un componente deja de ser seguro si le
  escribes `"use server"`, una llave de acceso o un `DROP TABLE`.
- **Zonas que preguntan siempre**, aunque ya hayan aceptado antes: comandos
  destructivos, llaves de acceso, lo que mantiene el sitio en línea, los avisos
  de seguridad mismos, y las herramientas externas.

Si avisa demasiado para tu proyecto, la primera respuesta es ajustar
`SEGURA_CARPETA` a cómo está ordenado ese repo. La segunda:

```bash
WOOB_GUARDRAIL_NIVEL=normal   # los comandos desconocidos pasan y aceptar una zona la abre entera
```

Léelo con cuidado: un guardrail que grita en todo se aprende a ignorar, y ahí
deja de servir. Ver [RIESGOS.md](RIESGOS.md).

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
