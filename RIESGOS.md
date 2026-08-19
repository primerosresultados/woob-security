# Lo que este guardrail NO te salva

Escrito a propósito en tono pesimista. Un guardrail que se vende como
infalible es peor que no tener guardrail, porque te hace bajar la guardia.

Esto **reduce accidentes de gente con buena intención**. No detiene a nadie que
quiera hacer daño, y no reemplaza permisos, backups ni revisión de código.

**Sobre el bloqueo de eliminaciones:** es lo único que se rechaza de verdad, y
aun así todo lo de la sección 1 lo evita igual. Un bloqueo dentro de Claude
Code no impide borrar desde la terminal, desde el editor, ni desde el panel de
Supabase. Lo único que impide borrar de verdad es no tener permiso para
borrar.

---

## 1. Se salta el guardrail entero

| Agujero | Qué pasa | Mitigación |
|---|---|---|
| **`claude --dangerously-skip-permissions`** | Los hooks siguen corriendo pero la confirmación no se muestra. Se acabó la protección. | No entregar ese flag en la documentación interna. La barrera real es el paso 6. |
| **`--permission-mode acceptEdits`** | Los edits se auto-aceptan. Mismo problema. | Igual que arriba. |
| **Editar fuera de Claude Code** | VS Code, Cursor, vim, la UI de GitHub. El hook solo ve lo que pasa por Claude Code. | Branch protection. |
| **Otro agente de IA** | Cursor, Copilot, Windsurf no leen `.claude/`. | Branch protection. |
| **Borrar el bloque `hooks`** | El guardrail avisa (`.claude/` es zona sensible) pero si aceptan, queda desactivado para siempre y en silencio. | CODEOWNERS sobre `.claude/`. |
| **`.claude/settings.local.json`** | Es local, no se commitea, y puede agregar permisos. | Ponerlo en `.gitignore` no basta: es local por definición. |
| **`python3` no existe** | El hook falla, Claude Code muestra un error no bloqueante **y sigue adelante**. Falla abierto, no cerrado. | `instalar.sh` avisa si falta. La skill es la capa redundante. |
| **`git merge` / `git revert` / `git pull`** | Traen cambios sensibles ya hechos sin pasar por ningún `Edit`. | Branch protection. |

**El punto incómodo:** un hook es una convención dentro de una herramienta, no
un permiso del sistema. Todo lo de arriba se arregla en el servidor, no acá.

---

## 2. Se salta la detección

- **Eliminaciones armadas de forma indirecta.** `F="-rf src"; rm $F` no se
  detecta. Tampoco un script `.sh` que borra por dentro: se avisa que es un
  atajo desconocido, pero no se prohíbe.
- **Comandos armados con variables.** `F=.env; echo x > $F` — el regex ve `$F`,
  no `.env`. Lo mismo con `eval`, `xargs`, rutas construidas.
- **Intérpretes embebidos.** `python3 -c`, `node -e`, heredocs y `base64 -d`
  ahora avisan de forma genérica, pero no sabemos **qué archivo** van a tocar.
  El aviso dice "por acá se puede escribir cualquier cosa", no más.
- **Pipes y descargas.** `curl … | bash` avisa. `wget && chmod +x && ejecutar`
  en tres comandos separados, cada uno inocente, no.
- **MCP.** Ahora avisa en toda herramienta externa salvo las que claramente
  solo consultan (`listar`, `detalle`, `get`, `search`). Sigue siendo el vector
  más peligroso: escriben directo sobre datos de producción, **sin git, sin
  diff y sin revertir**. Si un MCP llama "consultar" a algo que escribe, pasa.
- **Edits que quitan una protección.** Borrar el `WHERE` de un `DELETE` ya
  existente: el `new_string` no contiene "delete from", así que el chequeo de
  contenido no lo ve.
- **Symlinks y `..`.** La ruta se evalúa como texto. Un symlink desde una
  carpeta segura hacia una sensible no se resuelve.
- **Archivo inocente en carpeta segura.** `src/ui/config.ts` pasa porque `ui/`
  es zona segura. La lista blanca por carpeta es gruesa por naturaleza.

---

## 3. Riesgos del propio diseño

- **Fatiga de alerta.** Sigue siendo el riesgo número uno, aunque el nivel por
  defecto se calibró justamente para eso: una pregunta por zona y los comandos
  desconocidos pasando. Si la persona ve cuarenta avisos en media hora deja de
  leerlos y acepta por reflejo — y ahí el guardrail vale cero, aunque
  técnicamente esté "funcionando".

  Si pasa: ajustar `SEGURA_CARPETA` a las convenciones del proyecto antes de
  bajar el nivel.

- **Dos avisos en toda la sesión, y después nada.** El de base de datos y el
  general. Es lo pedido explícitamente: molestar poco. El costo es directo — si
  la primera vez que se toca la base de datos era algo inocente y la segunda
  era una migración destructiva, **la segunda pasa callada**. La única red que
  queda ahí es el bloqueo de eliminaciones.

- **Una aprobación abre todo el pedido. Este es el trade-off más grande del
  diseño.** Si la persona aprueba un plan que decía "voy a tocar el schema" y
  después el trabajo termina tocando también las llaves de acceso, el hook ya
  no interrumpe: la aprobación cubre lo que venga hasta el próximo mensaje.

  La contención es la skill, que tiene instrucción explícita de frenar y pedir
  una aprobación nueva si aparece algo más grave que lo aprobado. Pero eso es
  una instrucción al modelo, no un candado: **si el plan estaba mal hecho, la
  aprobación cubre de más.**

  La apuesta es que un plan leído y una aprobación consciente valen más que
  veinte confirmaciones salteadas. Si no te convence, `estricto` no cambia
  esto — la aprobación sigue siendo una por pedido; lo que cambia es qué la
  dispara. Para volver a confirmar paso a paso hay que sacar el chequeo de
  `estado(...).get("aprobado")` en el hook.

- **Los avisos ya no caducan con el mensaje nuevo.** `UserPromptSubmit` solo
  limpia la bitácora del informe; los avisos dados valen para toda la sesión.
  Reiniciar Claude Code es lo único que los vuelve a activar.

- **Los comandos desconocidos vuelven a pasar** en el nivel por defecto.
  `docker compose up`, `ssh servidor`, `npx tsx script.ts` no avisan. Si te
  importa cubrir eso, `WOOB_GUARDRAIL_NIVEL=estricto`.

- **El informe final lo escribe el modelo, no el hook.** El hook deja anotado
  qué se tocó (en el archivo de estado en `/tmp`), pero quien redacta el cierre
  es la skill. Si el modelo se olvida de cerrar, no hay nada que lo fuerce.
- **Falsos negativos silenciosos.** Cuando el guardrail no avisa, no dice
  "revisé y está bien". Dice "no lo reconocí". No son lo mismo.
- **Advertir no es impedir.** Por diseño. La persona puede aceptar todo. El
  guardrail deja un rastro de decisión consciente, no una barrera.
- **No juzga el cambio.** Mira *dónde* cae el archivo, no si el código está
  bien. Un cambio perfectamente ubicado puede tener la lógica de negocio mal.

---

## 4. Lo que sí hay que hacer (esto es lo que importa)

El guardrail es la capa más barata y la más débil. Las que de verdad sostienen:

1. **Branch protection + CODEOWNERS.** Que `migrations/`, `api/`, `.claude/`,
   `.github/` y `package.json` exijan review de Woob para mergear. Es la única
   barrera que no depende de la buena voluntad de nadie.
2. **Que no tengan las llaves de producción.** Base de datos de staging,
   credenciales propias, RLS activo. Si no tiene la llave, no puede abrir la
   puerta — no importa cuántos carteles pongas.
3. **Backups con point-in-time recovery**, probados. Un backup que nunca
   restauraste no es un backup.
4. **Deploy solo desde `main` y solo por Woob.** Nunca desde una máquina.
5. **Secret scanning** en pre-commit y en CI (gitleaks, GitHub secret
   scanning). El guardrail avisa al escribir; esto atrapa lo que se escapó.
6. **CI que falle** si el diff toca rutas protegidas sin aprobación explícita.

Los puntos 1 y 2 solos valen más que todo este repo. Lo de acá sirve para que
la persona se entere *antes* de apretar enter, no para impedírselo.

---

## 5. Cómo probar que sigue funcionando

```bash
python3 pruebas.py
```

Si tocas los patrones, corre esto. Un guardrail sin pruebas se degrada solo:
alguien agrega una regex, rompe otra, y nadie se entera hasta que ya pasó algo.
