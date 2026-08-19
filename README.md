# woob-security

> **¿Te pidieron instalar esto?** Salta a
> [Si eres Claude y te pidieron instalar esta skill](#si-eres-claude-y-te-pidieron-instalar-esta-skill).

Guardrail para cuando dejas que alguien externo edite el código de un proyecto
en producción.

**Molesta lo mínimo mientras se trabaja, y revisa el resultado al final.**

Una advertencia previa solo puede adivinar. La revisión final ve lo que de
verdad pasó: la llave que se coló, el borrado sin filtro, la pantalla que quedó
con permisos de servidor. **Encuentra más y molesta menos.**

Solo dos cosas frenan en el momento, porque después ya no habría nada que
hacer: **borrar** (prohibido, no se puede aceptar) y **la primera vez que se
toca la base de datos** (una advertencia dura, una sola vez).

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

## Cómo funciona la conversación

Preguntar de más y preguntar de menos fallan igual: si el aviso sale a cada
rato, se acepta sin leer y es como si no existiera. Por eso el trato es otro —
**una sola aprobación, a cambio de información completa antes y después**:

**1. Antes de tocar nada, dice el plan.** Qué va a hacer paso a paso, qué de
eso sale de la zona segura, qué puede salir mal, y cómo se vuelve atrás. Todo
junto, en un mensaje.

**2. Una aprobación, y solo si toca la base de datos.** Es la única
interrupción de todo el trabajo, y ocurre una vez en la conversación. El resto
—backend, llaves, infraestructura, dependencias— pasa callado y queda anotado.

**3. Trabaja sin molestar.** Nada de recordar el riesgo a mitad de camino ni
cerrar cada mensaje con una advertencia.

Solo frena si aparece algo más grave que no estaba en el plan, o si hay que
borrar (eso no se aprueba nunca).

**4. Al terminar, revisa el resultado.** Acá está el grueso del valor: el hook
vuelve a leer los archivos como quedaron y busca errores de verdad. Si
encuentra algo, obliga a informarlo antes de dar el trabajo por terminado.

Qué busca en lo que quedó escrito:

| Lo que encuentra | Por qué importa |
|---|---|
| Una llave de acceso escrita dentro de un archivo | Una vez que entra al proyecto, queda a la vista para siempre |
| `DELETE FROM tabla;` sin filtro | Borra todos los registros, no unos pocos |
| `DROP` o `TRUNCATE` | Elimina información completa |
| Una pantalla con `"use server"` | Le da permisos que antes no tenía |
| Un registro que imprime una clave | La clave queda escrita en los registros del sistema |
| La llave maestra de la base de datos en una pantalla | Esa llave se salta todos los permisos |

Y separa lo que **no pudo revisar**: los comandos que ya corrieron y las
herramientas externas que ya escribieron. Eso no deja archivo que releer, así
que el reporte lo dice en vez de callarlo:

```
ESTO NO LO PUDE REVISAR, porque ya se ejecutó y no deja nada que
releer. Si algo salió mal acá, no hay forma de detectarlo desde
afuera:

  ?  npx prisma migrate deploy
  ?  npm install zod
  ?  lead_guardar
```

Después lista las zonas tocadas, en simple, y le pide al modelo un cierre con
seis cosas: qué cambió, qué problemas había y cuáles arregló, qué no se pudo
revisar, cómo volver atrás, si hay que avisarle a Woob, y qué quedó pendiente.

Y le exige ser honesto con el alcance: **que la revisión no encuentre nada
significa que no encontró lo que sabe buscar, no que el trabajo esté bien.**

Si no hay nada que decir, **no dice nada**.

```
Esto es lo que voy a hacer:

  1. Agregar el campo "teléfono" a los clientes — prisma/schema.prisma
  2. Guardar ese teléfono al mandar el formulario — src/app/api/leads/route.ts
  3. Mostrarlo en la ficha del cliente — src/components/FichaCliente.tsx

De esto, sale de la zona segura:

  • cómo está organizada la información de los clientes (prisma/schema.prisma)
  • el motor que hace funcionar todo por detrás (src/app/api/leads/route.ts)

Qué puede salir mal:
  • se puede perder información de clientes que ya está guardada
  • pantallas que hoy funcionan pueden dejar de cargar

Cómo se vuelve atrás: volviendo a la versión anterior, sin tocar nada a mano.

Esta aprobación cubre todo el pedido: si me dices que sí, sigo hasta el
final sin interrumpirte, y al terminar te cuento qué cambié.
```

El hook es el respaldo: si la skill no hizo el plan, él fuerza esa aprobación
única igual, y después se calla hasta el próximo mensaje.

## El aviso de base de datos es distinto a propósito

Todo lo demás avisa en dos líneas. La base de datos, la primera vez, grita:

```
🛑  P A R A .   E S T Á S   T O C A N D O   L A   B A S E   D E   D A T O S .

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  supabase/migrations/0007_leads.sql

  Ahí adentro está la información REAL de los clientes.
  Nombres, teléfonos, correos, ventas, cobros. Todo lo que existe.

  Esto no es tu computador. Es el sistema que están usando AHORA MISMO.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SI ESTO SALE MAL:

  ✗  Se pierde información que NO se puede recuperar. No hay deshacer.
  ✗  No existe un botón para volver atrás. No hay papelera.
  ✗  Los clientes pierden sus datos, y se dan cuenta.
  ✗  Puede que nadie note el daño hasta días después, cuando ya es tarde.
```

Y después de eso, silencio: no vuelve a mencionar la base de datos en toda la
conversación. **Si todo se grita, nada se escucha** — por eso solo esto grita, y
solo una vez.

## Cuando eligen pedírselo a Woob

No los manda a "hablar con Woob" y ya. Deja el mensaje **escrito y listo para
copiar**, con el contexto ya puesto:

```
Hola, necesito ayuda con el proyecto Inmoo.

Qué necesito hacer: guardar el teléfono de los clientes cuando llenan
el formulario de contacto.
Para qué lo necesito: los corredores necesitan llamarlos y hoy solo
queda el correo.

Me avisaron que esto toca dónde se guarda la información de los
clientes, así que prefiero no hacerlo por mi cuenta.

Archivo: prisma/schema.prisma
Rama: feature/formulario-contacto

Lo que habría que cambiar: agregar un campo "teléfono" a los clientes
y que el formulario lo guarde ahí.
Ya intenté: nada, preferí preguntar antes.
Urgencia: [dime tú cuándo lo necesitas y se lo agrego]
```

El hook arma el esqueleto solo (proyecto, archivo, rama, zona). La skill rellena
lo que sabe de la conversación: qué querían hacer, para qué, y qué había que
cambiar. **Solo queda en blanco lo que únicamente la persona sabe.**

Un pedido sin contexto obliga a Woob a preguntar de vuelta, y ahí se pierde un
día. Y mientras esperan, si parte del trabajo era zona segura, la hace igual y
avisa qué quedó pendiente.

## Lo que protege siempre, en cualquier nivel

- **Borrar.** Prohibido, sin opción de aceptar.
- **La información de los clientes**, sus llaves de acceso, quién puede entrar
  y el dinero.
- **Las herramientas externas (MCP) que escriben.** Son el vector más
  peligroso: tocan datos reales sin git, sin diff y sin forma de volver atrás.
- **Nombres sospechosos dentro de carpetas seguras.** `src/ui/config.ts` y
  `src/components/cliente-db.ts` avisan igual: están en zona segura pero el
  nombre delata que no son solo pantalla.
- **El contenido.** Un componente deja de ser seguro si le escribes
  `"use server"`, una llave de acceso o un `DROP TABLE`.

## Tres niveles

```bash
WOOB_GUARDRAIL_NIVEL=equilibrado   # por defecto
WOOB_GUARDRAIL_NIVEL=estricto      # pregunta por cada archivo y en todo comando que no sea de solo lectura
WOOB_GUARDRAIL_NIVEL=relajado      # además deja pasar las herramientas externas y los nombres sospechosos
```

Borrar sigue prohibido en los tres.

Si aun así avisa demasiado para tu proyecto, antes de bajar el nivel ajusta
`SEGURA_CARPETA` a cómo está ordenado ese repo: cuando avisa en todo, casi
siempre es porque la zona segura no coincide con sus convenciones. Ver
[RIESGOS.md](RIESGOS.md).

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
