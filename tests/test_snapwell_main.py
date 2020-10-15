from datetime import date
from os import path
from pathlib import Path

import pytest
import snapwell
import snapwell.snapwell_main as swm


def test_version(capsys):
    app = swm.SnapwellApp(["snapwell", "--version"])
    with pytest.raises(SystemExit) as e:
        swm.run(app)
    assert e.value.code == 0
    assert snapwell.__version__ in capsys.readouterr().out


def test_run_missing(capsys, tmp_path):
    missing_file = path.join(tmp_path, "__missing__")
    app = swm.SnapwellApp(["snapwell", missing_file])
    with pytest.raises(SystemExit) as e:
        app.parse_args()
    assert e.value.code == 2
    assert "No such file" in capsys.readouterr().err


def test_missing_config_grid(capsys, tmp_path):
    config_file_path = path.join(tmp_path, "config.yaml")

    with open(config_file_path, "w") as config_file:
        config_file.write("grid_file:\n")
        config_file.write("restart_file: 'a.UNRST'\n")
        config_file.write("wellpath_files:\n")
        config_file.write("  - {well_file: 'a.w', date: '2020-1-1'}\n")

    app = swm.SnapwellApp(["snapwell", config_file_path])
    with pytest.raises(SystemExit) as e:
        app.load_config(app.parse_args())
    assert e.value.code == 2
    cap = capsys.readouterr()
    assert "grid_file" in cap.err


def test_missing_config_restart(capsys, tmp_path):
    config_file_path = path.join(tmp_path, "config.yaml")

    with open(config_file_path, "w") as config_file:
        config_file.write("grid_file: 'a.grid'\n")
        config_file.write("restart_file:\n")
        config_file.write("wellpath_files:\n")
        config_file.write("  - {well_file: 'a.w', date: '2020-1-1'}\n")

    app = swm.SnapwellApp(["snapwell", config_file_path])
    with pytest.raises(SystemExit) as e:
        app.load_config(app.parse_args())
    assert e.value.code == 2
    assert "restart_file" in capsys.readouterr().err


def write_config(
    config_file_path,
    grid_file="grid.EGRID",
    restart_file="restart.UNRST",
    well_files=[("well1.w", 2020)],
    init_file=None,
    keywords=[],
):
    with open(config_file_path, "w") as config_file:
        config_file.write(f"grid_file: '{grid_file}'\n")
        config_file.write(f"restart_file: '{restart_file}'\n")
        config_file.write(f"init_file: '{init_file}'\n")
        config_file.write(f"log_keywords: {keywords}\n")
        config_file.write("wellpath_files:\n")
        for wf in well_files:
            config_file.write(f"  - {{well_file: '{wf[0]}', date: '{wf[1]}'}}\n")


def test_config_sets_correct_paths(tmp_path):
    config_file_path = path.join(tmp_path, "config.yaml")

    grid_file = "a.EGRID"
    restart_file = "b.UNRST"
    well_file = "c.w"

    write_config(config_file_path, grid_file, restart_file, [(well_file, "2020-1-1")])

    app = swm.SnapwellApp(["snapwell", config_file_path])
    config = app.load_config(app.parse_args())

    assert config.grid_file == Path(path.join(tmp_path, grid_file))
    assert config.restart_file == Path(path.join(tmp_path, restart_file))
    assert config.wellpath_files[0].well_file == Path(path.join(tmp_path, well_file))
    assert config.wellpath_files[0].date == date(2020, 1, 1)
    assert not config.overwrite


@pytest.mark.parametrize("overwrite_keyword", ["-w", "--overwrite"])
def test_overwrite(tmp_path, overwrite_keyword):
    config_file_path = path.join(tmp_path, "config.yaml")
    write_config(config_file_path)

    app = swm.SnapwellApp(["snapwell", config_file_path, overwrite_keyword])
    config = app.load_config(app.parse_args())
    assert config.overwrite


test_data_path = path.join(path.dirname(__file__), "testdata", "snapwell")


def test_runner_correct_wellpaths():
    runner = swm.SnapwellApp(
        ["snapwell", path.join(test_data_path, "test.yaml")]
    ).runner()
    assert len(runner.wellpaths) == 1
    wp = runner.wellpaths[0]
    assert wp.well_type == "A - B"
    rows = list(wp.rows())
    assert len(rows) == 4
    assert all(len(r) == 6 for r in rows)


@pytest.mark.parametrize("config_file", ["test-depth.yaml", "test.yaml"])
def test_run_test_data_exits_with_zero(config_file):
    assert (
        swm.run(
            swm.SnapwellApp(["snapwell", path.join(test_data_path, config_file), "-w"])
        )
        == 0
    )


def test_missing_init_gives_error(capsys, tmp_path):
    config_file_path = path.join(tmp_path, "config.yaml")

    write_config(config_file_path, init_file="__MISSING__.INIT", keywords=["PERMX"])

    app = swm.SnapwellApp(["snapwell", config_file_path])
    args = app.parse_args()
    config = app.load_config(args)
    with pytest.raises(SystemExit) as e:
        app.load_permx(config)

    assert e.value.code == 2
    cap = capsys.readouterr().err
    assert "load supplied INIT file" in cap
