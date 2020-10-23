from datetime import date
from os import path
from pathlib import Path
from unittest.mock import MagicMock
import argparse
import yaml
import pytest
import snapwell
import snapwell.snapwell_main as swm


@pytest.fixture()
def valid_config(tmpdir):
    config = {
        "grid_file": path.join(test_data_path, "../eclipse/SPE3CASE1.EGRID"),
        "restart_file": path.join(test_data_path, "../eclipse/SPE3CASE1.UNRST"),
        "wellpath_files": [
            {"well_file": path.join(test_data_path, "well.w"), "date": "2022-1-1"},
            {"well_file": path.join(test_data_path, "well1.w"), "date": "2019-05-1"},
        ],
    }
    with tmpdir.as_cwd():
        with open("config_file.yaml", "w") as fout:
            yaml.dump(config, fout)
        yield "config_file.yaml"


def test_version(capsys):
    with pytest.raises(SystemExit) as e:
        swm.SnapwellApp(["snapwell", "--version"])
    assert e.value.code == 0
    assert snapwell.__version__ in capsys.readouterr().out


def test_run_missing(capsys, tmp_path):
    missing_file = path.join(tmp_path, "__missing__")
    with pytest.raises(SystemExit) as e:
        swm.SnapwellApp(["snapwell", missing_file])
    assert e.value.code == 2
    assert "No such file" in capsys.readouterr().err


def test_missing_config_grid(capsys, tmp_path):
    config_file_path = path.join(tmp_path, "config.yaml")

    with open(config_file_path, "w") as config_file:
        config_file.write("grid_file:\n")
        config_file.write("restart_file: 'a.UNRST'\n")
        config_file.write("wellpath_files:\n")
        config_file.write("  - {well_file: 'a.w', date: '2020-1-1'}\n")

    with pytest.raises(SystemExit) as e:
        swm.SnapwellApp(["snapwell", config_file_path])
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

    with pytest.raises(SystemExit) as e:
        swm.SnapwellApp(["snapwell", config_file_path])
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
    config = app.load_config()

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
    config = app.load_config()
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
    config = app.load_config()
    with pytest.raises(SystemExit) as e:
        app.load_permx(config)

    assert e.value.code == 2
    cap = capsys.readouterr().err
    assert "load supplied INIT file" in cap


@pytest.mark.parametrize("config_file", ["test-depth.yaml", "test.yaml"])
def test_commandline_owc_defintion(config_file):
    app = swm.SnapwellApp(
        ["snapwell", path.join(test_data_path, config_file), "-f", "SWAT:0.7"]
    )
    owc_definition = app.load_config().owc_definition

    assert owc_definition.keyword == "SWAT"
    assert owc_definition.value == 0.7


@pytest.mark.parametrize("owc_def", ["SWAT::", "SWAT0.7", "SWAT:bad", "   :0.7"])
def test_commandline_owc_defintion_malformed_owc_defnition(capsys, owc_def):
    with pytest.raises(SystemExit) as e:
        swm.SnapwellApp(
            ["snapwell", path.join(test_data_path, "test.yaml"), "-f", owc_def]
        )
    assert e.value.code == 2
    assert "owc definition" in capsys.readouterr().err


@pytest.mark.parametrize("input_val", [0, 0.0, 10, 10.0, 100, 100.0])
def test_percentage(input_val):
    swm.percentage(input_val) == float(input_val)


@pytest.mark.parametrize("input_val", [-1, -1.0, 100.01, 101, 200])
def test_invalid_percentage(input_val):
    with pytest.raises(argparse.ArgumentError):
        swm.percentage(input_val)


@pytest.mark.parametrize("input_val", ["a", [1, 2, 3]])
def test_invalid_percentage(input_val):
    with pytest.raises(argparse.ArgumentTypeError):
        swm.percentage(input_val)


@pytest.mark.parametrize(
    "allow_fail_threshold, expected_exit", [[0, -1], [50, 0], [50.1, 0], [100, 0]]
)
def test_run_allow_fail(
    tmpdir, monkeypatch, allow_fail_threshold, expected_exit, valid_config
):
    app = swm.SnapwellApp(
        [
            "snapwell",
            valid_config,
            "--allow-fail",
            str(allow_fail_threshold),
            "-w",
        ]
    )
    snap_mock = MagicMock(side_effect=[None, ValueError])
    monkeypatch.setattr(swm, "snap", snap_mock)
    assert swm.run(app) == expected_exit
