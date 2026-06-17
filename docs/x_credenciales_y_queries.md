# X / Twitter: credenciales, costos y formulación de queries

## 1. Dónde poner las credenciales

Las credenciales se guardan en el archivo `.env`, ubicado en la raíz del proyecto.

Primero copiar:

```powershell
Copy-Item .env.example .env
```

Luego editar `.env`:

```text
X_BEARER_TOKEN=pegar_acá_el_bearer_token
X_PRICE_PER_POST_USD=0.005
X_DAILY_BUDGET_USD=50
AUTHOR_HASH_SALT=una_frase_larga_privada
```

No subir `.env` a GitHub. Ya está excluido por `.gitignore`.

La app usa inicialmente solo `X_BEARER_TOKEN` para búsquedas públicas de lectura.

## 2. Costos actuales de X

X usa un esquema pay-per-use. No funciona como una suscripción fija para esta API: se compran créditos en la Developer Console y se consumen al hacer requests.

Según la documentación pública actual:

- posts leídos: USD 0.005 por recurso;
- usuarios leídos: USD 0.010 por recurso;
- los precios pueden variar y deben verificarse en la Developer Console;
- hay deduplicación dentro de una ventana diaria UTC;
- se pueden configurar límites de gasto.

Para desarrollo conviene comenzar con corridas de 100 a 500 posts.

Ejemplo de costo con USD 0.005/post:

```text
100 posts   = USD 0.50
500 posts   = USD 2.50
1.000 posts = USD 5.00
10.000 posts = USD 50.00
```

## 3. Estrategia de bajo costo

Antes de gastar en X:

1. Diseñar queries en una tabla.
2. Probarlas manualmente en el buscador de X.
3. Cargar algunos resultados a mano o por CSV.
4. Evaluar ruido y pertinencia.
5. Recién después ejecutar API con límite chico.

La app debe operar con tres niveles:

- laboratorio manual: costo cero;
- prueba API chica: 100 a 500 posts;
- corrida de relevamiento: 5.000 a 20.000 posts;
- monitoreo robusto: presupuesto específico.

## 4. Principios para formular queries

Cada query debe tener:

- un núcleo conceptual;
- variantes léxicas;
- filtros de idioma;
- exclusiones de ruido;
- decisión explícita sobre retweets, replies, links y medios.

Reglas prácticas:

- usar comillas para frases exactas;
- usar `OR` para variantes;
- usar paréntesis para evitar ambigüedad;
- usar `lang:es` para castellano;
- usar `-is:retweet` cuando se quiere evitar duplicación por republicaciones;
- usar `-is:reply` cuando se quiere observar publicaciones originales;
- usar `has:links`, `has:images` o `has:videos` para estudiar formatos específicos;
- no armar queries demasiado amplias en primera instancia.

## 5. Queries iniciales para la investigación antifeminismo

### Denuncias falsas

```text
("denuncias falsas" OR "falsas denuncias" OR "falsa denuncia" OR "denuncia falsa") lang:es -is:retweet
```

Versión más focalizada:

```text
("denuncias falsas" OR "falsa denuncia") (feminismo OR feminista OR género OR genero) lang:es -is:retweet
```

### Ideología de género

```text
("ideología de género" OR "ideologia de genero" OR "agenda de género" OR "agenda de genero") lang:es -is:retweet
```

Versión con educación:

```text
("ideología de género" OR "ideologia de genero") (escuela OR educación OR educacion OR ESI OR adoctrinamiento) lang:es -is:retweet
```

### ESI y adoctrinamiento

```text
(ESI OR "educación sexual integral" OR "educacion sexual integral") (adoctrinamiento OR ideología OR ideologia OR niños OR ninos) lang:es -is:retweet
```

### Feminazi / ataque identitario

```text
(feminazi OR feminazis OR "feminista resentida" OR "feministas resentidas") lang:es -is:retweet
```

### Privilegios feministas / curro

```text
(feminismo OR feministas OR género OR genero) (curro OR privilegios OR lobby OR negocio OR caja) lang:es -is:retweet
```

### Victimización masculina

```text
(hombres OR varones) (víctimas OR victimas OR discriminados OR perseguidos) (feminismo OR feministas OR género OR genero) lang:es -is:retweet
```

### Familia tradicional / amenaza moral

```text
("familia tradicional" OR "defender la familia" OR "destruir la familia") (feminismo OR género OR genero OR ESI) lang:es -is:retweet
```

## 6. Matriz de evaluación de queries

Cada query debe evaluarse con estas columnas:

```text
query_id
concepto
query
objetivo
ruido_esperado
plataforma
periodo
max_posts_prueba
posts_obtenidos
porcentaje_relevante_estimado
observaciones
estado
```

Estados sugeridos:

```text
borrador
probada_manual
probada_api_chica
aprobada
ruidosa
descartada
```

## 7. Próximo desarrollo recomendado

Agregar a la app una pestaña `Laboratorio de queries` con:

- alta de queries por proyecto;
- estimación de costo;
- estado de validación;
- notas metodológicas;
- ejecución controlada;
- comparación entre queries;
- porcentaje de ruido estimado por muestra revisada.
