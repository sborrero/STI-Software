# STI-Software

Repositorio de aplicaciones, herramientas y simuladores desarrollados en Python para las actividades prácticas del Ciclo Formativo de Grado Superior de **Sistemas de Telecomunicaciones e Informáticos (STI)**.

El objetivo es facilitar la experimentación, la visualización de fenómenos y la resolución de problemas técnicos relacionados con los módulos del ciclo.

## Áreas de trabajo

| Área | Contenido |
|---|---|
| [Audio](audio/) | Generación de señales, muestreo, digitalización, análisis espectral y comparación PCM. |
| [Ficheros digitales](ficheros_digitales/) | Análisis de archivos multimedia, formatos, metadatos y estructuras internas. |
| [Megafonía](megafonia/) | Diseño de instalaciones, distribución de altavoces, cobertura y cálculo de nivel SPL. |
| [Televisión](television/) | Señales de vídeo analógico y digital, barrido, muestreo, crominancia y compresión. |
| [Acústica – RT60](TR60/) | Cálculo del tiempo de reverberación por bandas de octava mediante Sabine, Eyring y Millington-Sette. |

## Cómo utilizar las aplicaciones

1. Entra en la carpeta del área que te interese.
2. Consulta su archivo README para conocer las aplicaciones disponibles y sus instrucciones.
3. Descarga el programa Python y, cuando corresponda, el resto de archivos necesarios (por ejemplo, la base de datos).
4. Instala las dependencias indicadas en el archivo `requirements.txt`.
5. Ejecuta la aplicación siguiendo las instrucciones de su documentación.

### Aplicaciones Streamlit

Desde una terminal abierta en la carpeta de la aplicación:

```powershell
python -m pip install -r requirements.txt
python -m streamlit run nombre_del_programa.py
```

No todas las aplicaciones utilizan Streamlit; consulta el README de cada área.

## Organización y versiones

Los programas se mantienen en sus respectivas carpetas. El número de versión forma parte del nombre del archivo cuando procede. Se conservan las versiones vigentes y se identifican en la documentación de cada área.

## Requisitos

Se requiere Python. Las bibliotecas adicionales dependen de cada aplicación y se especifican en sus instrucciones o en su archivo `requirements.txt`.

## Autoría y licencia

Autor: Santiago Borrero Ortiz.

Este repositorio se distribuye bajo licencia MIT. Consulta el archivo [LICENSE](LICENSE).
