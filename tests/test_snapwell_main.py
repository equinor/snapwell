from os import path

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
    config_file_path = path.join(tmp_path, "config.sc")

    with open(config_file_path, "w") as config_file:
        config_file.write("GRID\n")
        config_file.write("RESTART a.UNRST\n")
        config_file.write("WELLPATH b.w 2020\n")

    app = swm.SnapwellApp(["snapwell", config_file_path])
    with pytest.raises(SystemExit) as e:
        app.load_config(app.parse_args())
    assert e.value.code == 2
    assert "Could not load GRID" in capsys.readouterr().err


def test_missing_config_restart(capsys, tmp_path):
    config_file_path = path.join(tmp_path, "config.sc")

    with open(config_file_path, "w") as config_file:
        config_file.write("GRID a.grid\n")
        config_file.write("RESTART\n")
        config_file.write("WELLPATH b.w 2020\n")

    app = swm.SnapwellApp(["snapwell", config_file_path])
    with pytest.raises(SystemExit) as e:
        app.load_config(app.parse_args())
    assert e.value.code == 2
    assert "Could not load RESTART" in capsys.readouterr().err


def write_config(
    config_file_path,
    grid_file="grid.EGRID",
    restart_file="restart.UNRST",
    well_files=[("well1.w", 2020)],
):
    with open(config_file_path, "w") as config_file:
        config_file.write(f"GRID {grid_file}\n")
        config_file.write(f"RESTART {restart_file}\n")
        for wf in well_files:
            config_file.write(f"WELLPATH {wf[0]} {wf[1]}\n")


def test_config_sets_correct_paths(tmp_path):
    config_file_path = path.join(tmp_path, "config.sc")

    grid_file = "a.EGRID"
    restart_file = "b.UNRST"
    well_file = "c.w"
    year = 2020

    write_config(config_file_path, grid_file, restart_file, [(well_file, year)])

    app = swm.SnapwellApp(["snapwell", config_file_path])
    config = app.load_config(app.parse_args())

    assert config.gridFile() == path.join(tmp_path, grid_file)
    assert config.restartFile() == path.join(tmp_path, restart_file)
    assert config.filename(0) == path.join(tmp_path, well_file)
    assert config.date(0).year == year
    assert not config.overwrite()


@pytest.mark.parametrize("overwrite_keyword", ["-w", "--overwrite"])
def test_overwrite(tmp_path, overwrite_keyword):
    config_file_path = path.join(tmp_path, "config.sc")
    write_config(config_file_path)

    app = swm.SnapwellApp(["snapwell", config_file_path, overwrite_keyword])
    config = app.load_config(app.parse_args())
    assert config.overwrite()


test_data_path = path.join(path.dirname(__file__), "testdata", "snapwell")


def test_runner_correct_wellpaths():
    runner = swm.SnapwellApp(
        ["snapwell", path.join(test_data_path, "test.sc")]
    ).runner()
    assert len(runner.wellpaths) == 1
    wp = runner.wellpaths[0]
    assert wp.welltype() == "A - B"
    assert wp.version() == "2.0"
    rows = list(wp.rows())
    assert len(rows) == 4
    assert all(len(r) == 6 for r in rows)


@pytest.mark.parametrize("config_file", ["test-depth.sc", "test.sc"])
def test_run_test_data_exits_with_zero(config_file):
    assert (
        swm.run(
            swm.SnapwellApp(["snapwell", path.join(test_data_path, config_file), "-w"])
        )
        == 0
    )
