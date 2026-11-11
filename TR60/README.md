# Calculadora RT60 STI v1.2

Aplicación didáctica para estimar el tiempo de reverberación de recintos mediante seis bandas de octava: 125, 250, 500, 1000, 2000 y 4000 Hz.

## Funcionalidades

- Definición de la geometría del recinto y cálculo de su volumen.
- Introducción de paredes, suelo y techo con sus dimensiones y materiales.
- Incorporación de ventanas, puertas y otros huecos, asignándoles su propia superficie y material de absorción.
- Selección de personas, asientos y elementos discretos desde la base de datos, indicando sus cantidades.
- Cálculo del RT60 por bandas de octava mediante los métodos de Sabine, Eyring y Millington-Sette.
- Representación gráfica y comparación de los resultados de los tres métodos.
- Comparación orientativa de cada banda con el intervalo recomendado para el tipo de recinto seleccionado.
- Esquema cenital del recinto con la distribución de paredes y huecos.
- Sugerencias de acondicionamiento acústico cuando los resultados se encuentran fuera del intervalo de referencia.

## Archivos

| Archivo | Descripción |
|---|---|
| `calculadora_rt60_sti_v1_2.py` | Aplicación principal. |
| `database.json` | Base de datos de materiales, coeficientes de absorción y tipos de recinto. |
| `requirements.txt` | Dependencias necesarias. |

**Importante:** descarga también `database.json` y mantenlo en la misma carpeta que el programa Python.

## Instalación y ejecución

Desde una terminal abierta en esta carpeta:

```powershell
python -m pip install -r requirements.txt
python -m streamlit run calculadora_rt60_sti_v1_2.py
```

La aplicación se abrirá en el navegador.

## Consideraciones sobre los resultados

- Sabine, Eyring y Millington-Sette utilizan hipótesis diferentes; sus resultados pueden variar.
- Los métodos de Eyring y Millington-Sette tienen condiciones de aplicación. La aplicación advierte cuando los coeficientes introducidos no permiten aplicar correctamente una expresión.
- Los intervalos por tipo de recinto son referencias orientativas procedentes de la base de datos; no sustituyen los requisitos de una norma aplicable ni un estudio acústico profesional.
- Los resultados dependen de la calidad de los datos geométricos y de los coeficientes de absorción utilizados.

## Versión

Versión publicada: **1.2**.
