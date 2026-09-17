import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from src.gui import App
if __name__ == "__main__":
    app = App()
    # Fecha a splash screen (JobAutoFit.spec) assim que a janela principal está pronta — sem
    # isso ela não fecha sozinha. pyi_splash só existe dentro do .exe empacotado; rodando do
    # código-fonte o import falha e é ignorado de propósito. Este launcher (não src/gui.py) é
    # quem o PyInstaller executa como __main__ no build congelado.
    try:
        import pyi_splash
        pyi_splash.close()
    except ImportError:
        pass
    app.mainloop()
