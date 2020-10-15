import pytest
from snapwell.snapwell_main import main as snapwell_main

skip_tests = False
try:
    import snapwell._ert_hooks._ert_hook
    from ert_shared.plugins.plugin_manager import ErtPluginManager
except ImportError:
    skip_tests = True

pytestmark = pytest.mark.skipif(skip_tests, reason="No ert (optional) installed")


def test_hook_implementations():
    pm = ErtPluginManager(
        plugins=[
            snapwell._ert_hooks._ert_hook,
        ]
    )

    wf_name = "SNAPWELL"
    wf_location = "snapwell/_ert_hooks/SNAPWELL"
    installable_jobs = pm.get_installable_jobs()
    assert wf_name in installable_jobs
    assert installable_jobs[wf_name].endswith(wf_location)


def test_hook_implementations_job_docs():
    pm = ErtPluginManager(plugins=[snapwell._ert_hooks._ert_hook])

    installable_jobs = pm.get_installable_jobs()
    docs = pm.get_documentation_for_jobs()

    assert set(docs.keys()) == set(installable_jobs.keys())
    assert docs["SNAPWELL"]["description"] == snapwell_main.__doc__
    assert docs["SNAPWELL"]["category"] == "modelling.well"
