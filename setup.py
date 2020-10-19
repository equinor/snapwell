from pathlib import Path
from setuptools import setup, find_packages


def get_long_description() -> str:
    return Path("README.md").read_text(encoding="utf8")


setup(
    name="snapwell",
    use_scm_version={"write_to": "snapwell/version.py"},
    long_description=get_long_description(),
    long_description_content_type="text/markdown",
    packages=find_packages(include=["snapwell*"]),
    install_requires=["libecl", "equinor-libres"],
    entry_points={
        "console_scripts": [
            "snapwell_app=snapwell.snapwell_main:main",
        ],
        "ert": [
            "snapwell=snapwell._ert_hooks._ert_hook",
        ],
    },
    license="GPL-3.0",
    platforms="any",
    classifiers=[
        "Development Status :: 1 - Planning",
        "Environment :: Plugins",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Natural Language :: English",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Topic :: Scientific/Engineering",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    setup_requires=["setuptools_scm"],
    include_package_data=True,
)
