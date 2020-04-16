import setuptools

setuptools.setup(
    name="snapwell",
    version="1.0.0",
    packages=["snapwell"],
    entry_points={
        "console_scripts": [
            "snapwell = snapwell:snapwellmain",
            "snapviz = snapwell:snapvizmain",
        ]
    },
)
