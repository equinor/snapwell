import os
import subprocess
import unittest

import pytest
from ecl.util.test import TestAreaContext

from snapwell import WellPath

from .testcase import TestCase


class TestSnapwellProgram(TestCase):
    """
    This tests the installed version of snapwell, so will fail if not installed.
    """

    def setUp(self):
        self.testDataFolder = os.path.join(
            TestCase.PROJECT_ROOT, "tests", "testdata", "snapwell", "norne"
        )
        self.snapwellprogram = "snapwell_app"
        self.norneTestEdgeWellPath = os.path.join(
            self.testDataFolder, "norne-test-1-edge.w"
        )

    def test_snapwell_invalid_arg_throws(self):
        with TestAreaContext("Run_snapwell_invalid_arg_throws"):
            with self.assertRaises(subprocess.CalledProcessError):
                subprocess.check_call([self.snapwellprogram, "no_such_file.yaml"])

    def test_snapwell_well_ok(self):
        with TestAreaContext("Run_snapwell_valid_arg_exit_ok"):
            config_file_name = "norne-reg-test.yaml"
            self.write_snap_config_and_run(config_file_name)
            self.assertTrue(os.path.isfile(config_file_name))

            self.assertTrue(os.path.exists("snap_output"))
            expected_well_output_fname = os.path.join(
                "snap_output", "NORNE-TEST-1-EDGE.out"
            )
            self.assertTrue(os.path.isfile(expected_well_output_fname))

            wp_in, wp_snapped = self.check_snapwell_metadata_ok(
                expected_well_output_fname
            )
            self.assertEqual(
                ["x", "y", "z", "LENGTH", "TVD_DIFF", "OLD_TVD", "OWC"],
                wp_snapped.headers,
            )
            self.check_snapwell_wellpath_ok(wp_in, wp_snapped)

    def test_snapwell_well_ok_with_sat(self):
        with TestAreaContext("Run_snapwell_valid_arg_exit_ok"):
            config_file_name = "norne-reg-test.sc"
            kws = ["SWAT", "SGAS", "SOIL"]
            self.write_snap_config_and_run(config_file_name, log_keywords=kws)
            self.assertTrue(os.path.isfile(config_file_name))

            self.assertTrue(os.path.exists("snap_output"))
            expected_well_output_fname = os.path.join(
                "snap_output", "NORNE-TEST-1-EDGE.out"
            )
            self.assertTrue(os.path.isfile(expected_well_output_fname))

            wp_in, wp_snapped = self.check_snapwell_metadata_ok(
                expected_well_output_fname
            )
            self.assertEqual(["x", "y", "z"] + kws, wp_snapped.headers)

            self.check_snapwell_wellpath_ok(wp_in, wp_snapped)

    def test_snapwell_well_ok_with_permx(self):
        with TestAreaContext("Run_snapwell_valid_arg_exit_ok"):
            config_file_name = "norne-reg-test.sc"
            kws = ["PERMX"]
            self.write_snap_config_and_run(config_file_name, log_keywords=kws)
            self.assertTrue(os.path.isfile(config_file_name))

            self.assertTrue(os.path.exists("snap_output"))
            expected_well_output_fname = os.path.join(
                "snap_output", "NORNE-TEST-1-EDGE.out"
            )
            self.assertTrue(os.path.isfile(expected_well_output_fname))

            wp_in, wp_snapped = self.check_snapwell_metadata_ok(
                expected_well_output_fname
            )
            self.assertEqual(["x", "y", "z"] + kws, wp_snapped.headers)

            self.check_snapwell_wellpath_ok(wp_in, wp_snapped)

    def check_snapwell_metadata_ok(self, expected_well_output_fname):
        wp_in = WellPath.parse(self.norneTestEdgeWellPath)
        wp_snapped = WellPath.parse(expected_well_output_fname)

        self.assertEqual(wp_in.well_name, wp_snapped.well_name)
        self.assertEqual(expected_well_output_fname, wp_snapped.file_name)
        self.assertEqual("DISPOSAL - DRILLED", wp_snapped.well_type)
        self.assertEqual(len(wp_in), len(wp_snapped))
        # Expects additional headers / columns in output.
        self.assertNotEqual(wp_in.headers, wp_snapped.headers)
        self.assertEqual(wp_in.rkb, wp_snapped.rkb)
        return wp_in, wp_snapped

    def check_snapwell_wellpath_ok(self, wp_in, wp_snapped):
        headers = wp_snapped.headers
        for row_in, row_snapped in zip(wp_in, wp_snapped):
            # Check xy unchanged
            self.assertEqual(row_in[0:2], row_snapped[0:2])
            # Check consistency with new-tvd and old-tvd + TVD_DIFF
            if "TVD_DIFF" in headers:
                TVD_DIFF = row_snapped[headers.index("TVD_DIFF")]
                self.assertAlmostEqual(row_snapped[2], row_in[2] + TVD_DIFF, 2)
            # Check input tvd against outputted old-tvd for consistency
            if "OLD_TVD" in headers:
                self.assertEqual(row_snapped[headers.index("OLD_TVD")], row_in[2])

            if "SOIL" in headers and "SGAS" in headers and "SWAT" in headers:
                kw_idxes = [headers.index(kw) for kw in ["SOIL", "SGAS", "SWAT"]]
                sats = [row_snapped[j] for j in kw_idxes]
                assert all(0 <= sat <= 1 for sat in sats)
                assert sum(sat for sat in sats) == 1

        # Check actual z values
        self.assertAlmostEqual(2507.52, wp_snapped[0][2], 2)
        self.assertAlmostEqual(2684.09, wp_snapped[1][2], 2)
        self.assertAlmostEqual(2678.74, wp_snapped[2][2], 2)
        self.assertAlmostEqual(2674.40, wp_snapped[3][2], 2)
        self.assertAlmostEqual(2690.73, wp_snapped[4][2], 2)
        self.assertAlmostEqual(2688.32, wp_snapped[5][2], 2)

        if "OWC" in headers:
            idx = headers.index("OWC")
            self.assertAlmostEqual(2695.61, wp_snapped[0][idx], 2)
            self.assertAlmostEqual(2699.40, wp_snapped[1][idx], 2)
            self.assertAlmostEqual(2695.52, wp_snapped[2][idx], 2)
            self.assertAlmostEqual(2690.78, wp_snapped[3][idx], 2)
            self.assertAlmostEqual(2694.47, wp_snapped[4][idx], 0)
            self.assertAlmostEqual(2693.05, wp_snapped[5][idx], 2)

    def write_snap_config_and_run(
        self, filename, log_keywords=["LENGTH", "TVD_DIFF", "OLD_TVD", "OWC"]
    ):
        norne_test_data_prefix = os.path.join(
            self.TEST_ROOT_PATH,
            "testdata",
            "snapwell",
            "norne",
            "sim_data",
            "NORNE_ATW2013",
        )
        with open(filename, "a") as the_file:
            the_file.write("grid_file: '" + norne_test_data_prefix + ".EGRID'\n")
            the_file.write("restart_file: '" + norne_test_data_prefix + ".UNRST'\n")
            the_file.write("init_file: '" + norne_test_data_prefix + ".INIT'\n")
            the_file.write("output_dir: 'snap_output'\n")
            the_file.write("overwrite:  False\n")
            the_file.write("wellpath_files:\n")
            the_file.write(
                "  - {well_file: '"
                + self.norneTestEdgeWellPath
                + "', date: '1998-1-1'}\n"
            )
            the_file.write(f"log_keywords: {log_keywords}\n")

        # Run the snapwell program
        self.assertEqual(0, subprocess.check_call([self.snapwellprogram, filename]))


if __name__ == "__main__":
    unittest.main()
