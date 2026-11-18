@echo off
cd /d "%~dp0"

python --version >nul 2>&1
if errorlevel 1 (
    echo Python nao foi encontrado.
    echo Instale o Python 3.12 ou mais novo em https://www.python.org/downloads/
    echo e marque a opcao "Add Python to PATH" na instalacao.
    pause
    exit /b 1
)

echo Instalando as dependencias (so demora na primeira vez)...
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo Nao foi possivel instalar as dependencias. Confira a conexao com a internet.
    pause
    exit /b 1
)

echo.
echo Abrindo o app no navegador. Para fechar, feche esta janela.
python -m streamlit run app.py
pause
