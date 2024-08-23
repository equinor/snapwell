import os
import sys

if sys.version_info >= (3, 9):
    from importlib.resources import files
else:
    from importlib_resources import files
from snapwell.snapwell_main import main as snapwell_main
from ert.plugins.plugin_manager import hook_implementation
from ert.shared.plugins.plugin_response import plugin_response


@hook_implementation
@plugin_response(plugin_name="snapwell")
def installable_jobs():
    resource_directory = files("snapwell") / "_ert_hooks"
    return {"SNAPWELL": os.path.join(resource_directory, "SNAPWELL")}


@hook_implementation
@plugin_response(plugin_name="snapwell")
def job_documentation(job_name):
    if job_name != "SNAPWELL":
        return None

    return {
        "description": snapwell_main.__doc__,
        "examples": "",
        "category": "modelling.well",
    }
