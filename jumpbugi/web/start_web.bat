@echo off
chcp 65001 >nul
pushd "%~dp0"
python -B serve.py
popd
pause
