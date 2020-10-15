import os
from pkg_resources import resource_filename
from snapwell.snapwell_main import main as snapwell_main
from ert_shared.plugins.plugin_manager import hook_implementation
from ert_shared.plugins.plugin_response import plugin_response


@hook_implementation
@plugin_response(plugin_name="snapwell")
def installable_jobs():
    resource_directory = resource_filename("snapwell", "_ert_hooks")
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
