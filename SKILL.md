---
name: woob-security
description: Advertencia obligatoria, en lenguaje común y sin nada técnico, antes de tocar cualquier archivo fuera de la zona segura del proyecto (todo lo que no sea pantallas, colores, textos, imágenes, pruebas o documentación). Úsala ANTES de editar, crear o borrar archivos y antes de correr comandos que escriban, migren o publiquen. NO bloquea: advierte, explica el riesgo en palabras simples y deja seguir a quien acepte la responsabilidad. Dispara con: "base de datos", "database", "migración", "migration", "schema", "modelo", "tabla", "SQL", "prisma", "supabase", "backend", "API", "endpoint", "servidor", "server action", "auth", "login", "sesión", "permisos", "RLS", ".env", "secreto", "credencial", "deploy", "docker", "webhook", "pago", "stripe", "dependencia", "npm install", "config".
---

# Cambios sensibles — advertir en simple, no bloquear

Este proyecto es de un cliente de **Woob** y está funcionando de verdad, con
gente usándolo. Fuera de un puñado de carpetas, un cambio bien intencionado
puede borrar información real, dejar el sitio caído o abrir un hueco de
seguridad — y el daño casi nunca se ve en el momento.

Tu trabajo es **avisar con claridad y dejar decidir**. No eres un portero: eres
el cartel de "piso mojado".

## Regla 0 — Nunca bloquear

Después de advertir, si la persona dice que asume la responsabilidad, **haz el
cambio completo y bien hecho**. Sin repetir la advertencia, sin sermón, sin
hacerlo a medias en señal de protesta. La decisión es suya.

Está prohibido:

- Negarse a hacer el cambio.
- Hacer una versión "más segura" que no es lo que pidieron, sin decirlo.
- Volver a advertir sobre lo mismo que ya aceptaron en esta conversación.

## Regla 1 — Habla en cristiano, cero técnico

**Esta es la regla que hace que el aviso sirva.** La persona que lo lee puede
no saber qué es una migración, un endpoint o un token. Si no entiende el aviso,
lo acepta sin leer, y entonces el aviso no sirvió de nada.

Tres cosas, siempre:

1. **Cero palabras técnicas.** Nada de *schema*, *endpoint*, *deploy*, *build*,
   *token*, *middleware*, *RLS*, *commit*, *lockfile*, *entorno*, *instancia*.
   Tampoco siglas: ni API, ni SQL, ni JWT, ni CI.
2. **Explica la consecuencia, no el mecanismo.** No "modifica el schema de la
   tabla", sino "cambia cómo está guardada la información de los clientes".
   A nadie le importa *cómo* se rompe; le importa *qué* se rompe.
3. **Frases cortas, sin condicionales.** "Puede borrar información de clientes
   sin poder recuperarla" es útil. "Podría, dependiendo del entorno, afectar la
   integridad referencial" no le dice nada a nadie.

### Diccionario

| No digas | Di |
|---|---|
| base de datos, migración, SQL | dónde se guarda la información de los clientes |
| schema, modelo, tabla, campo | cómo está organizada la información |
| backend, API, endpoint, servidor | el motor que hace funcionar todo por detrás |
| autenticación, sesión, token, permisos, RLS | quién puede entrar y qué puede ver cada persona |
| variables de entorno, secretos, credenciales, `.env` | las llaves de acceso del sistema |
| infraestructura, deploy, contenedor, pipeline | lo que mantiene el sitio en línea |
| dependencias, build, lockfile, paquetes | las piezas que el proyecto necesita para armarse |
| webhook, integración, pasarela de pago | los cobros y la conexión con otros servicios |
| irreversible, no idempotente | no se puede deshacer |
| romper el contrato, breaking change | otras pantallas dejan de funcionar |
| producción | el sitio que están usando los clientes ahora mismo |

**La única excepción es el nombre del archivo o el comando.** Ese va tal cual,
porque es la única forma de que sepan de qué estás hablando. Todo lo que lo
rodea, en simple.

Las tablas de señales que vienen más abajo (`migrations/`, `schema.*`, `api/`…)
son **para que tú reconozcas la zona**. Nunca se las repitas a la persona.

## Regla 2 — Lista blanca, no lista negra

No adivines si algo es peligroso. Pregúntate si está en la zona segura. Si no
lo está, avisa — aunque parezca inofensivo, aunque no sepas qué hace.

### Zona segura (trabaja normal, sin avisos)

| En simple | Señales para ti |
|---|---|
| **Las pantallas** | `components/`, `ui/`, `views/`, `layouts/`, `sections/`, `page.tsx`, `layout.tsx` |
| **Los colores y el aspecto** | `styles/`, `theme/`, `*.css`, `*.scss`, `*.less` |
| **Los textos** | `content/`, `copy/`, `locales/`, `i18n/`, `blog/`, `*.md`, `*.mdx` |
| **Las imágenes y tipografías** | `assets/`, `public/`, `img/`, `icons/`, `fonts/`, `*.svg`, `*.png` |
| **Las pruebas** | `tests/`, `__tests__/`, `*.test.*`, `*.spec.*`, `*.stories.*` |
| **La documentación** | `docs/`, `README`, `CHANGELOG`, `CONTRIBUTING` |

### Todo lo demás avisa

Con nombre propio cuando lo reconozcas:

| Cómo lo nombras (en simple) | Señales para ti |
|---|---|
| **dónde se guarda la información de los clientes** | `migrations/`, `*.sql`, `seed`, `supabase/`, `db/`, `alembic/`, `drizzle`, `knex` |
| **cómo está organizada la información** | `schema.*`, `models/`, `entities/`, `prisma/`, `*.graphql` |
| **el motor que hace funcionar todo por detrás** | `api/`, `server/`, `routes/`, `controllers/`, `services/`, `actions/`, `functions/`, `trpc/`, `convex/`, `route.ts`, `*.server.ts` |
| **quién puede entrar y qué puede ver cada persona** | `auth`, `session`, `middleware`, `jwt`, `rbac`, `rls`, `policy`, `guard`, `*.rules` |
| **las llaves de acceso del sistema** | `.env*`, `credentials`, `secrets`, `*.pem`, `*.key`, `.gitignore`, `.npmrc` |
| **lo que mantiene el sitio en línea** | `Dockerfile`, `.github/`, `vercel.json`, `netlify.toml`, `*.tf`, `Makefile`, `nginx` |
| **las piezas que el proyecto necesita para armarse** | `package.json`, lockfiles, `tsconfig.json`, `next.config.*`, `vite.config.*` |
| **los cobros y el dinero** | `stripe`, `mercadopago`, `transbank`, `webhook`, `checkout`, `billing` |
| **los avisos de seguridad que te protegen** | `.claude/`, `CLAUDE.md`, `.mcp.json` |
| **un comando que puede hacer daño** | migraciones, publicaciones, instalar paquetes, `DROP`, `rm -rf`, `git push --force` |

Y cuando no lo reconozcas, con nombre genérico:
*"un archivo que está fuera de la zona segura"*. Un `src/lib/helpers.ts` no está
en ninguna lista y aun así puede tener la lógica de la que depende media
aplicación.

**Si dudas, avisa.** Una advertencia de más cuesta diez segundos; borrar datos
de clientes cuesta un fin de semana.

## Regla 3 — El contenido también cuenta

Un archivo de la zona segura deja de serlo por lo que le escribes adentro.
Avisa igual si el cambio mete:

- `"use server"`, `createServerClient` o cualquier cosa que lo mueva al motor
  de atrás → *"esta pantalla pasa a tener permisos que antes no tenía"*.
- Una llave escrita a mano (`sk_live_…`, `AKIA…`, una clave privada, un token)
  → *"esa llave queda escrita en el proyecto y ya no se puede volver a ocultar"*.
- Órdenes que borran o cambian datos (`DROP`, `ALTER TABLE`, `DELETE FROM` sin
  `WHERE`) → *"esto borra información de verdad"*.
- Una conexión directa a la base de datos desde una pantalla.

## Cómo advertir

Usa `AskUserQuestion`, para que sea una decisión explícita y no un párrafo que
se pueda pasar por alto. Antes de la pregunta, escribe el aviso así:

```
⚠️  Fuera de la zona segura

Mejor solicita este cambio al Equipo de Woob, porque estas tocando: {zona en simple} ({archivo o comando}).

Qué puede salir mal:
  • {consecuencia concreta, en una línea, sin jerga}
  • {segunda consecuencia, si aplica}

Contacto: Equipo de Woob.
```

Con estas dos opciones exactas:

- **"Pedirlo al Equipo de Woob"** → no tocas nada. Déjale escrito el pedido
  listo para copiar y pegar, también en simple: qué quiere que cambie y por qué.
- **"Sigo, asumo la responsabilidad"** → haces el cambio completo, sin
  restricciones y sin volver a preguntar por esa misma zona en esta
  conversación.

### Ejemplo de cómo NO hacerlo

> Estás modificando el schema de Prisma, lo que implica una migración
> destructiva sobre la tabla `leads`. Esto puede romper el contrato de la API
> y requerir un redeploy.

Nadie fuera del equipo entiende eso. Nadie lo lee. Todos lo aceptan.

### Ejemplo de cómo sí

> ⚠️  Fuera de la zona segura
>
> Mejor solicita este cambio al Equipo de Woob, porque estas tocando: cómo está
> organizada la información de los clientes (`prisma/schema.prisma`).
>
> Qué puede salir mal:
>   • se puede perder información de clientes que ya está guardada, sin poder recuperarla
>   • pantallas que hoy funcionan pueden dejar de cargar, y no te vas a enterar hasta que un cliente reclame
>
> Contacto: Equipo de Woob.

## Cuando hay dos zonas a la vez

Nombra la más grave. El orden: avisos de seguridad → llaves de acceso →
información de clientes → quién puede entrar → dinero → lo que mantiene el
sitio en línea → el motor de atrás → organización de la información → piezas
del proyecto → zona desconocida.

## Después de que aceptan

1. Haz el cambio como lo pidieron, completo.
2. Al terminar, en una o dos líneas y **también en simple**: qué cambiaste, qué
   conviene revisar, y cómo volver atrás si sale mal.
3. Si el cambio necesita un paso extra sobre el sitio en vivo, dilo
   explícitamente en vez de hacerlo por tu cuenta.
