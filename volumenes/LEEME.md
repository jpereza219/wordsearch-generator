# Bancos de palabras por volumen

Cada volumen del libro tiene su propia carpeta aquí dentro, por ejemplo `volumenes/vol2/`.
En cada carpeta hay **dos archivos CSV** (tablas que se abren con Excel o Google Sheets):

| Archivo | Qué contiene |
|---|---|
| `puzzles.csv` | Una fila por puzzle: su número, su título y, si quieres, su configuración. |
| `palabras.csv` | Una fila por palabra: a qué puzzle pertenece y si es una palabra oculta. |

La app los lee: eliges el volumen y el puzzle, y se llenan solos el título, las palabras, las
palabras ocultas y la configuración. Antes de generar puedes cambiar lo que quieras.

## `puzzles.csv`

| Columna | ¿Obligatoria? | Qué poner |
|---|---|---|
| `puzzle` | Sí | Número del puzzle, de 1 a 50. No se puede repetir. |
| `titulo` | Sí | Título del puzzle (aparece en el PDF y en el nombre de los archivos). |
| `filas` | No | Filas de la cuadrícula (5 a 40). Vacío = lo que diga la app (15). |
| `columnas` | No | Columnas (5 a 40). Vacío = 15. |
| `dificultad` | No | `Very easy`, `Easy`, `Medium`, `Hard`, `Very hard` o `Extreme`. Vacío = `Medium`. |
| `senuelos` | No | Número de señuelos (0 a 30). Si no coincide con los de la dificultad, la app usa `Custom` con las direcciones de esa dificultad y estos señuelos. |
| `especiales` | No | Caracteres especiales del relleno, como en la app: `Ñ,Á,É,Í,Ó,Ú,Ü, ’`. Vacío = los de la app. |
| `notas` | No | Lo que quieras; la app no lo usa. |

## `palabras.csv`

| Columna | ¿Obligatoria? | Qué poner |
|---|---|---|
| `puzzle` | Sí | Número del puzzle al que pertenece la palabra (debe existir en `puzzles.csv`). |
| `palabra` | Sí | La palabra tal como debe salir en la lista: con tildes, Ñ, Ü, espacios, guion o apóstrofo ’. |
| `oculta` | No | `sí` si es una palabra de la **Ruta Secreta** (no sale en la lista ni en la solución del libro). Vacío si es normal. También valen `si`, `x` o `1`. |

### Ejemplo

`puzzles.csv`

```
puzzle,titulo,filas,columnas,dificultad,senuelos,especiales,notas
1,Próceres de Honduras,,,,,,Usa la configuración de la app
2,Momentos de nuestra historia,15,15,Hard,,"Ñ,Á,É,Í,Ó,Ú,Ü",
```

`palabras.csv`

```
puzzle,palabra,oculta
1,LEMPIRA,
1,POLICARPO PAZ,
1,NUESTRA,sí
2,INDEPENDENCIA,
2,HISTORIA,sí
```

El mensaje de la Ruta Secreta se arma con las palabras ocultas **en orden de puzzle**:
en el ejemplo, «NUESTRA HISTORIA».

> El campo `especiales` lleva comas por dentro; por eso va entre comillas. Excel y Google
> Sheets lo hacen solos al guardar: tú solo escribe `Ñ,Á,É,Í,Ó,Ú,Ü` en la celda.

## Qué revisa la app

**Errores** (hay que corregirlos; la app dice el archivo y el número de línea):

- un puzzle sin título;
- un número de puzzle fuera de 1–50 o repetido en `puzzles.csv`;
- una palabra que apunta a un puzzle que no existe;
- faltan columnas obligatorias;
- un valor que no se entiende (por ejemplo, letras en `filas` o una dificultad desconocida).

**Avisos** (solo informan):

- un puzzle sin palabras o sin palabra oculta;
- una palabra repetida dentro del volumen (en el Vol. 1 algunas se repitieron a propósito,
  como YORO o LA PAZ).

## Editar en Excel sin dañar las tildes

1. Abre el CSV. Si las tildes se ven raras (`PrÃ³ceres`), ciérralo sin guardar y ábrelo desde
   **Datos → Obtener datos → Desde texto/CSV**, eligiendo el origen **65001: Unicode (UTF-8)**.
2. Edita las celdas normalmente.
3. Guarda con **Archivo → Guardar como → «CSV UTF-8 (delimitado por comas) (*.csv)»**.
   No elijas «CSV (delimitado por comas)» a secas: ese tipo pierde las tildes y la Ñ.

Excel en español a veces guarda con **punto y coma** (`;`) en vez de coma. No pasa nada: la app
acepta los dos.

## Editar en Google Sheets

1. **Archivo → Importar → Subir** el CSV (o arrástralo a Google Drive y ábrelo con Hojas de cálculo).
2. Edita las celdas.
3. **Archivo → Descargar → Valores separados por comas (.csv)**. Google Sheets siempre guarda en
   UTF-8, así que las tildes se conservan.
4. El archivo descargado puede llamarse `vol2 - puzzles.csv`: cámbiale el nombre a `puzzles.csv`
   (o `palabras.csv`) antes de subirlo.

## Probar un borrador sin subirlo

En la app, abre **«Probar un borrador»** y sube tu `puzzles.csv` y tu `palabras.csv`. La app los
valida y te deja generar sus puzzles sin tocar lo que está en GitHub.

## Subir los cambios a GitHub desde la web

1. Entra al repositorio en GitHub y abre la carpeta del volumen (por ejemplo `volumenes/vol2`).
2. Pulsa **Add file → Upload files** y arrastra los CSV. Si ya existían, se reemplazan.
3. Abajo, en **Commit changes**, escribe qué cambiaste (por ejemplo «Vol. 2: puzzles 4 a 10»).
4. Elige **«Create a new branch for this commit and start a pull request»** y pulsa
   **Propose changes**. Así las pruebas automáticas revisan los archivos antes de que lleguen a la
   app publicada.
5. Cuando el pull request esté en verde, pulsa **Merge pull request**.

Para un volumen nuevo, crea la carpeta al subir: en **Add file → Create new file** escribe
`volumenes/vol3/puzzles.csv` como nombre (la barra `/` crea la carpeta) y pega el contenido.
