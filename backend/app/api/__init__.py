"""
API路由模块
"""

from flask import Blueprint

graph_bp = Blueprint('graph', __name__)
simulation_bp = Blueprint('simulation', __name__)
report_bp = Blueprint('report', __name__)
evaluation_bp = Blueprint('evaluation', __name__)
incident_bp = Blueprint('incident', __name__)
forecast_bp = Blueprint('forecast', __name__)

from . import graph  # noqa: E402, F401
from . import simulation  # noqa: E402, F401
from . import report  # noqa: E402, F401
from . import evaluation  # noqa: E402, F401
from . import incident  # noqa: E402, F401
from . import forecast  # noqa: E402, F401

