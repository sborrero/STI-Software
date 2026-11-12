echo "Se instalarán Python, herramientas de venv, Tkinter y"
echo "todas las librerías incluidas en la guía de STI."
echo

if ! command -v apt-get >/dev/null 2>&1; then
  echo "ERROR: este instalador está preparado para Ubuntu/Debian."
  exit 1
fi

if ! command -v sudo >/dev/null 2>&1; then
  echo "ERROR: no se encuentra sudo. Instala los paquetes del sistema como administrador."
  exit 1
fi

echo "[1/7] Actualizando los repositorios e instalando Python..."
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv python3-full python3-tk

echo
echo "Python del sistema:"
python3 --version
python3 -m pip --version || true

echo
echo "[2/7] Creando la estructura de carpetas..."
mkdir -p \
  "$SOFTWARE_DIR/megafonia" \
  "$SOFTWARE_DIR/audio" \
  "$SOFTWARE_DIR/television" \
  "$SOFTWARE_DIR/redes" \
  "$SOFTWARE_DIR/telefonia" \
  "$ENV_DIR"

echo
echo "[3/7] Preparando el entorno virtual..."
if [[ -x "$VENV_DIR/bin/python" ]]; then
  echo "Ya existe un entorno virtual en:"
  echo "  $VENV_DIR"
  echo "Se conservará para no borrar instalaciones existentes."
else
  if [[ -e "$VENV_DIR" ]]; then
    echo "ERROR: existe $VENV_DIR, pero no parece un entorno virtual válido."
    echo "Revisa esa carpeta y vuelve a ejecutar el instalador."
    exit 1
  fi
  python3 -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

echo "Entorno activo: $VIRTUAL_ENV"
echo "Versión usada por el entorno: $(python --version)"

echo
echo "[4/7] Actualizando pip..."
python -m pip install --upgrade pip

echo
echo "[5/7] Instalando las librerías de la guía..."
python -m pip install "${PACKAGES[@]}"

echo
echo "[6/7] Creando el comando de activación..."
cat > "$ACTIVATE_HELPER" <<'ACTIVATE_EOF'
#!/usr/bin/env bash
# Activar el entorno común de Python del módulo STI.
source "$HOME/STI/python_env/venv/bin/activate"
cd "$HOME/STI/software"
echo "Entorno Python de STI activado."
echo "Carpeta de trabajo: $HOME/STI/software"
echo "Python utilizado: $(command -v python)"
python --version
ACTIVATE_EOF
chmod +x "$ACTIVATE_HELPER"

echo
echo "[7/7] Comprobando las librerías y guardando requirements.txt..."
python - <<'PY'
modules = [
    "numpy", "scipy", "sympy", "pandas", "matplotlib",
    "plotly", "seaborn", "streamlit", "soundfile",
    "librosa", "openpyxl", "xlsxwriter", "tkinter"
]
failed = []
for module in modules:
    try:
        __import__(module)
        print(f"  OK  {module}")
    except Exception as exc:
        failed.append((module, str(exc)))
        print(f"  ERROR  {module}: {exc}")

if failed:
    print("\nHay módulos que no se han podido importar.")
    raise SystemExit(1)
PY

python -m pip freeze > "$REQUIREMENTS_FILE"

echo
echo "======================================================"
echo "  INSTALACIÓN COMPLETADA"
echo "======================================================"
echo "Entorno virtual: $VENV_DIR"
echo "Activador:       $ACTIVATE_HELPER"
echo "Dependencias:    $REQUIREMENTS_FILE"
echo
echo "Para empezar cada sesión de prácticas:"
echo "  source ~/STI/activar.sh"
echo
echo "Para instalar otra librería:"
echo "  python -m pip install nombre_paquete"
echo
echo "Para actualizar el inventario de dependencias:"
echo "  python -m pip freeze > ~/STI/requirements.txt"
echo
echo "Nota: el entorno utiliza la versión de Python proporcionada"
echo "por Ubuntu (python3). No instala ni fuerza Python 3.12."
