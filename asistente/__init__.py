"""Asistente de integracion de Pedidos360 (EP1 - ISY0101).

Se silencia aqui el ruido de las librerias de embeddings, que no aporta nada y
confunde a quien ejecuta el proyecto: torch avisa de que el driver de CUDA es
antiguo, y transformers imprime una barra de progreso al cargar los pesos. Los
embeddings corren en CPU a proposito —el modelo es pequeno— asi que ese aviso no
senala ningun problema, pero en un notebook sale en rojo y parece un fallo.

Solo se filtra ese ruido concreto. Los avisos que importan siguen apareciendo.
"""
import logging
import warnings

warnings.filterwarnings("ignore", category=UserWarning, module="torch")
warnings.filterwarnings("ignore", message=".*CUDA initialization.*")
logging.getLogger("transformers").setLevel(logging.ERROR)

try:  # la barra de "Loading weights" de transformers
    from transformers.utils import logging as _hf_logging
    _hf_logging.disable_progress_bar()
except Exception:  # transformers no esta instalado o cambio de API: no es critico
    pass
