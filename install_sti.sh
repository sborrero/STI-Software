#!/usr/bin/env bash
# Instalador del entorno común de Python para el módulo STI
# Ubuntu 22.04. Usa Python 3.12 sin modificar el Python del sistema.

set -Eeuo pipefail

STI_DIR="$HOME/STI"
SOFTWARE_DIR="$STI_DIR/software"
ENV_DIR="$STI_DIR/python_env"
VENV_DIR="$ENV_DIR/venv"
ACTIVATE_HELPER="$STI_DIR/activar.sh"
REQUIREMENTS_FILE="$STI_DIR/requirements.txt"

PACKAGES=(
  numpy scipy sympy pandas matplotlib plotly seaborn streamlit
  soundfile librosa openpyxl xlsxwriter
)

fail() {
  echo
  echo "ERROR: $*" >&2
  exit 1
}

trap 'echo; echo "ERROR en la línea $LINENO. La instalación se ha detenido."; exit 1' ERR

echo "======================================================"
echo " Entorno Python STI para Ubuntu 22.04 - Python 3.12"
echo "======================================================"
echo

command -v apt-get >/dev/null 2>&1 || fail "Este instalador requiere Ubuntu/Debian."
command -v sudo >/dev/null 2>&1 || fail "No se encuentra sudo."

echo "[1/7] Actualizando repositorios e instalando Python 3.12..."
sudo apt-get update
sudo apt-get install -y software-properties-common
if ! apt-cache show python3.12 >/dev/null 2>&1; then
  sudo add-apt-repository -y ppa:deadsnakes/ppa
  sudo apt-get update
fi
sudo apt-get install -y python3.12 python3.12-venv python3.12-tk

PYTHON_BIN="$(command -v python3.12)"
"$PYTHON_BIN" --version

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
  EXISTING_VERSION="$("$VENV_DIR/bin/python" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
  if [[ "$EXISTING_VERSION" != "3.12" ]]; then
    BACKUP_DIR="${VENV_DIR}.backup_python${EXISTING_VERSION}_$(date +%Y%m%d_%H%M%S)"
    echo "El entorno existente usa Python $EXISTING_VERSION."
    echo "Se conservará como: $BACKUP_DIR"
    mv "$VENV_DIR" "$BACKUP_DIR"
  else
    echo "Ya existe un entorno Python 3.12. Se reutilizará."
  fi
elif [[ -e "$VENV_DIR" ]]; then
  fail "Existe $VENV_DIR, pero no es un entorno virtual válido. Renómbralo o elimínalo manualmente."
fi

if [[ ! -x "$VENV_DIR/bin/python" ]]; then
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
echo "Entorno activo: ${VIRTUAL_ENV}"
python --version

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
echo "Python: $(python --version)"
ACTIVATE_EOF
chmod +x "$ACTIVATE_HELPER"

echo
echo "[7/7] Comprobando las librerías y guardando requirements.txt..."
python - <<'PY'
import importlib
modules = [
    "numpy", "scipy", "sympy", "pandas", "matplotlib", "plotly",
    "seaborn", "streamlit", "soundfile", "librosa", "openpyxl",
    "xlsxwriter", "tkinter"
]
failed = []
for name in modules:
    try:
        importlib.import_module(name)
        print(f"  OK  {name}")
    except Exception as exc:
        print(f"  ERROR  {name}: {exc}")
        failed.append(name)
if failed:
    raise SystemExit("Falló la comprobación de: " + ", ".join(failed))
PY

python -m pip freeze > "$REQUIREMENTS_FILE"

echo
echo "======================================================"
echo " INSTALACIÓN COMPLETADA CORRECTAMENTE"
echo "======================================================"
echo "Python:       $("$VENV_DIR/bin/python" --version)"
echo "Entorno:      $VENV_DIR"
echo "Activador:    $ACTIVATE_HELPER"
echo "Dependencias: $REQUIREMENTS_FILE"
echo
echo "Para empezar cada sesión de prácticas:"
echo "  source ~/STI/activar.sh"
echo
echo "Para instalar otra librería:"
echo "  python -m pip install nombre_paquete"
echo
echo "Para actualizar requirements.txt:"
echo "  python -m pip freeze > ~/STI/requirements.txt"

