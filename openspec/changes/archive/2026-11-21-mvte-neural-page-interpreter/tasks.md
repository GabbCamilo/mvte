# Tasks: mvte-neural-page-interpreter

- [x] 1.1 Atualizar `ContourPageAnalyzer` com divisão recursiva por vales de margem (*Recursive XY-Cut*) para lidar com *bleed*.
- [x] 1.2 Implementar `RtDetrOnnxDetector` em `src/mvte/modules/visual_detection/detector.py` e helper de descoberta padrão do modelo em `models/`.
- [x] 1.3 Atualizar `interfaces/cli/main.py` e `interfaces/gui/main.py` para usar o detector neural por padrão quando disponível.
- [x] 1.4 Validar nas duas páginas reais enviadas pelo usuário e executar toda a suíte `pytest -v`.
