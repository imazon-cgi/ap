# app/__init__.py
from flask import Flask
from app.dashboards.ameaca_geral_terra_indigena import (
    register_ameaca_terra_indigena,
)
from app.dashboards.ameaca_geral_area_de_protecao import register_ameaca_area_protecao
from app.dashboards.ameaca_geral_ucs              import register_ameaca_ucs
from app.dashboards.pressao_geral_area_de_protecao import (
    register_pressao_area_protecao,
)
from app.dashboards.pressao_geral_terra_indigena import (
    register_pressao_terras_indigenas,
)
from app.dashboards.pressao_geral_ucs import register_pressao_ucs
def create_app():
    server = Flask(__name__)
    register_ameaca_terra_indigena(server)  # /ameaca_terras_indigenas/
    register_ameaca_area_protecao(server) # /area_de_protecao/
    register_ameaca_ucs(server)              # /ucs/
    register_pressao_area_protecao(server)  # /pressao_area_de_protecao/
    register_pressao_terras_indigenas(server)  # /pressao_terra_indigena/
    register_pressao_ucs(server)   # /pressao_ucs/
    return server
