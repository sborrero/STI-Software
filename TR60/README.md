# Calculadora RT60 STI v1.2

Novedades:
- Evalúa cada banda frente al intervalo RT60 orientativo del tipo de recinto seleccionado.
- Indica si el resultado está dentro, por encima o por debajo del intervalo.
- Dibuja un esquema cenital con paredes, ventanas y puertas.
- Permite situar huecos mediante su distancia desde el inicio de la pared y su ancho.
- Sugiere medidas acústicas orientativas según el exceso o defecto de reverberación.

Nota: el esquema cenital utiliza las cuatro primeras paredes como perímetro (dos largas y dos cortas). La evaluación de RT60 usa el intervalo de la hoja Recintos; es una referencia orientativa y no sustituye una especificación normativa o un proyecto acústico.


La versión 0.8 incorpora gestión editable de materiales y tipos de recinto, distribución uniforme de huecos en el esquema y corrección del análisis de intervalos RT60.


La versión 0.9 elimina el argumento `help` de `st.data_editor`, incompatible con algunas versiones de Streamlit; la explicación se muestra mediante un texto independiente.


La versión 1.0 elimina todos los argumentos `help` de las llamadas a `st.data_editor`, incompatibles con la versión de Streamlit del entorno del usuario.


La versión 1.1 incorpora la comparación por bandas de octava de Sabine, Eyring y Millington-Sette. Sabine sigue siendo el método de referencia de la evaluación acústica. Se informa cuando los coeficientes hacen que Eyring o Millington-Sette no sean aplicables.


La versión 1.2 separa la absorción de superficies y la absorción equivalente de elementos discretos en los cálculos de Eyring y Millington-Sette. Sabine mantiene la suma total de absorciones.
