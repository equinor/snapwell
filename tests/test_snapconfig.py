from datetime import date
from math import inf
from os.path import dirname, join
from pathlib import Path

import pytest
import yaml

from snapwell import SnapConfig

testdata_path = join(dirname(__file__), "testdata")
conf_path = join(testdata_path, "snapwell")
eclipse_path = join(testdata_path, "eclipse")


def same_path(path1, path2):
    return Path(path1).resolve() == Path(path2).resolve()


def test_parse_missing_grid():
    with pytest.raises(TypeError):
        SnapConfig(
            restart_file="restart.UNRST",
            wellpath_files=[
                {"well_file": "well.w", "date": "2022-1-1"},
                {"well_file": "well1.w", "date": "2019-05-1"},
            ],
        )


def test_parse_missing_restart():
    with pytest.raises(TypeError):
        SnapConfig(
            grid_file="grid.EGRID",
            wellpath_files=[
                {"well_file": "well.w", "date": "2022-1-1"},
                {"well_file": "well1.w", "date": "2019-05-1"},
            ],
        )


def test_parse_without_init():
    conf = SnapConfig(
        grid_file="grid.EGRID",
        restart_file="restart.UNRST",
        wellpath_files=[
            {"well_file": "well.w", "date": "2022-1-1"},
            {"well_file": "well1.w", "date": "2019-05-1"},
        ],
    )
    assert conf.init_file is None


@pytest.fixture
def init_config():
    return SnapConfig(
        grid_file="grid.EGRID",
        restart_file="restart.UNRST",
        init_file="../eclipse/SPE3CASE1.INIT",
        wellpath_files=[
            {"well_file": "well.w", "date": "2022-1-1"},
            {"well_file": "well1.w", "date": "2019-05-1"},
        ],
    )


def test_set_base_path(init_config):
    init_config.set_base_path(conf_path)
    assert same_path(join(eclipse_path, "SPE3CASE1.INIT"), init_config.init_file)
    assert same_path(join(conf_path, "grid.EGRID"), init_config.grid_file)
    assert same_path(join(conf_path, "restart.UNRST"), init_config.restart_file)


def test_wellpath_content(init_config):
    assert len(init_config.wellpath_files) == 2

    init_config.set_base_path(conf_path)
    assert same_path(join(conf_path, "well.w"), init_config.wellpath_files[0].well_file)
    assert same_path(
        join(conf_path, "well1.w"), init_config.wellpath_files[1].well_file
    )
    assert init_config.wellpath_files[0].date == date(2022, 1, 1)
    assert init_config.wellpath_files[1].date == date(2019, 5, 1)


@pytest.fixture
def full_config():
    return SnapConfig(
        grid_file="../eclipse/SPE3CASE1.EGRID",
        restart_file="../eclipse/SPE3CASE1.UNRST",
        init_file="../eclipse/SPE3CASE1.INIT",
        output_dir="../eclipse",
        overwrite=True,
        owc_offset=0.88,
        delta_z=0.55,
        owc_definition={"keyword": "SGAS", "value": 0.31415},
        log_keywords=["LENGTH", "TVD_DIFF", "OLD_TVD", "OWC", "PERMX"],
        wellpath_files=[
            {"well_file": "well.w", "date": "2025-03-31"},
            {
                "well_file": "well1.w",
                "date": "2022-12-03",
                "depth_type": "TVD",
                "window_depth": 2000.0,
            },
            {
                "well_file": "well2.w",
                "date": "2025-03-31",
                "depth_type": "MD",
                "window_depth": 158.20,
            },
            {
                "well_file": "well3.w",
                "date": "2022-12-03",
                "depth_type": "MD",
                "window_depth": 1680,
            },
            {
                "well_file": "well4.w",
                "date": "2023-12-03",
                "owc_definition": 0.71828,
                "depth_type": "MD",
                "window_depth": 1680,
            },
            {
                "well_file": "well5.w",
                "date": "2024-12-03",
                "owc_offset": 0.5115,
                "owc_definition": 0.1828,
            },
            {
                "well_file": "well6.w",
                "date": "2025-12-03",
                "owc_offset": 0.115,
                "owc_definition": 0.828,
                "depth_type": "MD",
                "window_depth": 1884,
            },
            {
                "well_file": "well7.w",
                "date": "2022-1-1",
                "depth_type": "MD",
                "window_depth": 4000,
                "owc_definition": 0.0,
            },
        ],
    )


def test_full_config_values(full_config):
    assert full_config.log_keywords == ["LENGTH", "TVD_DIFF", "OLD_TVD", "OWC", "PERMX"]
    assert full_config.owc_offset == pytest.approx(0.88)
    assert full_config.delta_z == pytest.approx(0.55)
    assert full_config.overwrite


def test_full_config_owc_definition(full_config):
    assert full_config.owc_definition.keyword == "SGAS"
    assert full_config.owc_definition.value == pytest.approx(0.31415)


def test_full_config_set_base_path(full_config):
    full_config.set_base_path(conf_path)
    assert same_path(join(eclipse_path, "SPE3CASE1.EGRID"), full_config.grid_file)
    assert same_path(join(eclipse_path, "SPE3CASE1.UNRST"), full_config.restart_file)
    assert same_path(join(eclipse_path, "SPE3CASE1.INIT"), full_config.init_file)
    assert same_path(eclipse_path, full_config.output_dir)


def test_full_config_wellpath_files_base_path(full_config):
    full_config.set_base_path(conf_path)
    assert same_path(join(conf_path, "well.w"), full_config.wellpath_files[0].well_file)
    for i in range(1, 8):
        assert same_path(
            join(conf_path, f"well{i}.w"), full_config.wellpath_files[i].well_file
        )


def test_full_config_wellpath_depth_types(full_config):
    expected = [None, "TVD", "MD", "MD", "MD", None, "MD", "MD"]
    assert [wpf.depth_type for wpf in full_config.wellpath_files] == expected


def test_full_config_wellpath_depths(full_config):
    expected = [
        -inf,
        pytest.approx(2000.00),
        pytest.approx(158.20),
        pytest.approx(1680.00),
        pytest.approx(1680.00),
        -inf,
        pytest.approx(1884),
        pytest.approx(4000),
    ]
    assert [wpf.window_depth for wpf in full_config.wellpath_files] == expected


def test_full_config_wellpath_owc_definitions(full_config):
    expected = [
        None,
        None,
        None,
        None,
        pytest.approx(0.71828),
        pytest.approx(0.1828),
        pytest.approx(0.828),
        pytest.approx(0.0),
    ]
    assert [wpf.owc_definition for wpf in full_config.wellpath_files] == expected


def test_full_config_wellpath_owc_offset(full_config):
    expected = [
        None,
        None,
        None,
        None,
        None,
        pytest.approx(0.5115),
        pytest.approx(0.115),
        None,
    ]
    assert [wpf.owc_offset for wpf in full_config.wellpath_files] == expected


def test_full_config_wellpath6_values(full_config):
    wp = full_config.wellpath_files[6]
    # WELLPATH well6.w 2025-12-03 OWC_OFFSET 0.115 OWC_DEFINITION 0.828 MD 1884
    assert wp.owc_definition == pytest.approx(0.828)
    assert wp.owc_offset == pytest.approx(0.115)
    assert wp.depth_type == "MD"
    assert wp.window_depth == pytest.approx(1884)


@pytest.fixture
def config():
    with open(join(conf_path, "test.yaml")) as config_file:
        config_dict = yaml.safe_load(config_file)
    return SnapConfig(**config_dict)


def test_config(config):
    assert config.owc_offset == pytest.approx(0.5)
    assert config.delta_z == inf

    config.set_base_path(conf_path)
    assert same_path(join(eclipse_path, "SPE3CASE1.EGRID"), config.grid_file)
    assert same_path(join(eclipse_path, "SPE3CASE1.UNRST"), config.restart_file)

    assert same_path(join(conf_path, "well1.w"), config.wellpath_files[0].well_file)
    assert config.init_file is None
    assert date(2025, 1, 1) == config.wellpath_files[0].date
    assert config.output_dir == Path(conf_path)
    assert not config.overwrite
