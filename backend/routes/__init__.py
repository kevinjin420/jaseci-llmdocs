"""
Route registration module
Imports all route modules and provides a unified registration interface
"""
from . import benchmarks
from . import models
from . import files
from . import results
from . import health


def register_all_routes(app, socketio, running_benchmarks):
    """Register all routes from all modules"""
    benchmarks.register_routes(app, socketio, running_benchmarks)
    models.register_routes(app, socketio, running_benchmarks)
    files.register_routes(app, socketio, running_benchmarks)
    results.register_routes(app, socketio, running_benchmarks)
    health.register_routes(app, socketio, running_benchmarks)


__all__ = ['register_all_routes']
