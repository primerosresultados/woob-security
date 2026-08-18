---
name: woob-security
description: Advertencia obligatoria antes de tocar cualquier archivo fuera de la zona segura del proyecto (todo lo que no sea interfaz, estilos, textos, imágenes, tests o documentación). Úsala ANTES de editar, crear o borrar archivos y antes de correr comandos que escriban, migren o desplieguen. NO bloquea: advierte, explica el riesgo y deja seguir a quien acepte la responsabilidad. Dispara con: "base de datos", "database", "migración", "migration", "schema", "modelo", "tabla", "SQL", "prisma", "supabase", "backend", "API", "endpoint", "servidor", "server action", "auth", "login", "sesión", "permisos", "RLS", ".env", "secreto", "credencial", "deploy", "docker", "webhook", "pago", "stripe", "dependencia", "npm install", "config".
---

# Cambios sensibles — advertir, no bloquear

Este proyecto es de un cliente de **Woob** y está en producción. Fuera de un
puñado de carpetas, un cambio bien intencionado puede romper datos reales,
tumbar el servicio o abrir un hueco de seguridad — y el daño casi nunca se ve
en el momento.

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

## Regla 1 — Lista blanca, no lista negra

Esto es lo que cambia el criterio por completo: **no adivines si algo es
peligroso. Pregúntate si está en la zona segura.** Si no lo está, avisa —
aunque parezca inofensivo, aunque no sepas qué hace.

### Zona segura (trabaja normal, sin avisos)

| | |
|---|---|
| **Interfaz** | `components/`, `ui/`, `views/`, `layouts/`, `sections/`, `page.tsx`, `layout.tsx` |
| **Estilos** | `styles/`, `theme/`, `*.css`, `*.scss`, `*.less` |
| **Contenido y textos** | `content/`, `copy/`, `locales/`, `i18n/`, `blog/`, `*.md`, `*.mdx` |
| **Imágenes y fuentes** | `assets/`, `public/`, `img/`, `icons/`, `fonts/`, `*.svg`, `*.png`, `*.woff2` |
| **Tests** | `tests/`, `__tests__/`, `*.test.*`, `*.spec.*`, `*.stories.*` |
| **Documentación** | `docs/`, `README`, `CHANGELOG`, `CONTRIBUTING` |

### Todo lo demás avisa

Con nombre propio cuando lo reconozcas:

| Zona | Señales |
|---|---|
| **Base de datos y migraciones** | `migrations/`, `*.sql`, `seed`, `supabase/`, `db/`, `alembic/`, `drizzle`, `knex` |
| **Schema y modelos** | `schema.*`, `models/`, `entities/`, `prisma/`, `*.graphql` |
| **Backend y API** | `api/`, `server/`, `routes/`, `controllers/`, `services/`, `actions/`, `functions/`, `trpc/`, `convex/`, `route.ts`, `*.server.ts` |
| **Auth, sesiones y permisos** | `auth`, `session`, `middleware`, `jwt`, `rbac`, `rls`, `policy`, `guard`, `*.rules` |
| **Secretos y config** | `.env*`, `credentials`, `secrets`, `*.pem`, `*.key`, `.gitignore`, `.npmrc` |
| **Infra y deploy** | `Dockerfile`, `.github/`, `vercel.json`, `netlify.toml`, `*.tf`, `Makefile`, `nginx` |
| **Dependencias y build** | `package.json`, lockfiles, `tsconfig.json`, `next.config.*`, `vite.config.*` |
| **Pagos e integraciones** | `stripe`, `mercadopago`, `transbank`, `webhook`, `checkout`, `billing` |
| **El guardrail mismo** | `.claude/`, `CLAUDE.md`, `.mcp.json` — tocar esto es desactivar la protección |
| **Comandos** | migraciones, deploys, `npm install`, `DROP`, `rm -rf`, `git push --force`, `git checkout .` |

Y con nombre genérico cuando no: *"un archivo que está fuera de la zona segura"*.
Un `src/lib/helpers.ts` no está en ninguna lista negra y aun así puede tener la
lógica de la que depende media aplicación.

**Si dudas, avisa.** Una advertencia de más cuesta diez segundos; una migración
mal hecha cuesta un fin de semana.

## Regla 2 — El contenido también cuenta

Un archivo de la zona segura deja de serlo por lo que le escribes adentro. Avisa
igual si el cambio introduce:

- `"use server"`, `createServerClient` o cualquier cosa que lo mueva al servidor.
- Una credencial escrita a mano (`sk_live_…`, `AKIA…`, una private key, un JWT).
- SQL que modifica datos (`DROP`, `ALTER TABLE`, `DELETE FROM` sin `WHERE`).
- Una llamada directa a la base de datos desde un componente.

## Cómo advertir

Usa `AskUserQuestion`, para que sea una decisión explícita y no un párrafo que
se pueda pasar por alto. Antes de la pregunta, escribe el aviso con esta forma:

```
⚠️  Fuera de la zona segura

Mejor solicita este cambio al Equipo de Woob, porque estas tocando: {zona} ({archivo o comando}).

Qué puede salir mal:
  • {riesgo concreto, en una línea}
  • {segundo riesgo, si aplica}

Contacto: Equipo de Woob.
```

Con estas dos opciones exactas:

- **"Pedirlo al Equipo de Woob"** → no tocas nada. Déjale escrito el pedido
  listo para copiar y pegar: qué archivo, qué cambio quiere y por qué.
- **"Sigo, asumo la responsabilidad"** → haces el cambio completo, sin
  restricciones y sin volver a preguntar por esa misma zona en esta
  conversación.

`{zona}` va en palabras normales, no una ruta cruda:
"base de datos y migraciones (`supabase/migrations/0007_leads.sql`)".

## Riesgos por zona

- **Base de datos / migraciones** — puede borrar o corromper datos reales de
  clientes; muchas migraciones no se pueden deshacer.
- **Schema / modelos** — rompe código que asume la forma vieja de los datos, y
  suele fallar en producción, no en local.
- **Backend / API** — cambia el contrato que consumen el front y las
  integraciones; se rompen pantallas que no estás mirando.
- **Auth / permisos** — un error acá deja datos de un cliente visibles para otro.
- **Secretos / config** — una credencial en el repo queda expuesta para siempre,
  aunque después la borres.
- **Infra / deploy** — puede dejar el sitio caído sin forma rápida de volver atrás.
- **Dependencias / build** — puede romper el build de todo el equipo, no solo el tuyo.
- **Pagos / integraciones** — plata real y webhooks que no se pueden repetir.
- **El guardrail mismo** — desactiva las advertencias para todo el que trabaje en el repo.
- **Zona desconocida** — nadie clasificó ese archivo; puede tener lógica de la
  que dependen otras partes.

## Cuando hay dos zonas a la vez

Nombra la más grave. El orden: guardrail → secretos → base de datos → auth →
pagos → infra → backend → schema → build → desconocida.

## Después de que aceptan

1. Haz el cambio como lo pidieron, completo.
2. Al terminar, en una o dos líneas: **qué cambiaste**, **qué hay que revisar**
   y **cómo volver atrás** si sale mal.
3. Si el cambio requiere correr una migración o un deploy, dilo explícitamente
   en vez de hacerlo por tu cuenta.
