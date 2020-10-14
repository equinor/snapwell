import setuptools

setuptools.setup(
    name="snapwell",
    version="1.0.0",
    packages=["snapwell"],
    install_requires=["libecl", "equinor-libres"],
    entry_points={
        "console_scripts": [
            "snapwell=snapwell.snapwell_main:main",
        ]
    },
)
