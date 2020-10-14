import os
import subprocess
import unittest

import pytest
from ecl.util.test import TestAreaContext
from .testcase import TestCase
from snapwell import WellPath


class TestSnapwellProgram(TestCase):
    """
    This tests the installed version of snapwell, so will fail if not installed.
    """

    def setUp(self):
        self.testDataFolder = os.path.join(
            TestCase.PROJECT_ROOT, "tests", "testdata", "snapwell", "norne"
        )
        self.snapwellprogram = "snapwell"
        self.norneTestEdgeWellPath = os.path.join(
            self.testDataFolder, "norne-test-1-edge.w"
        )

    def test_snapwell_invalid_arg_throws(self):
        with TestAreaContext("Run_snapwell_invalid_arg_throws"):
            with self.assertRaises(subprocess.CalledProcessError):
                subprocess.check_call([self.snapwellprogram, "no_such_file.sc"])

    def test_snapwell_well_ok(self):
        with TestAreaContext("Run_snapwell_valid_arg_exit_ok"):
            config_file_name = "norne-reg-test.sc"
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

            self.check_snapwell_wellpath_ok(wp_in, wp_snapped)

    def check_snapwell_metadata_ok(self, expected_well_output_fname):
        wp_in = WellPath.parse(self.norneTestEdgeWellPath)
        wp_snapped = WellPath.parse(expected_well_output_fname)

        self.assertEqual(wp_in.wellname(), wp_snapped.wellname())
        self.assertEqual(expected_well_output_fname, wp_snapped.filename())
        self.assertEqual("DISPOSAL - DRILLED", wp_snapped.welltype())
        self.assertEqual(len(wp_in), len(wp_snapped))
        # Expects additional headers / columns in output.
        self.assertNotEqual(wp_in.headers(), wp_snapped.headers())
        self.assertEqual(
            ["x", "y", "z", "LENGTH", "TVD_DIFF", "OLD_TVD", "OWC"],
            wp_snapped.headers(),
        )
        self.assertEqual(wp_in.rkb(), wp_snapped.rkb())
        return wp_in, wp_snapped

    def check_snapwell_wellpath_ok(self, wp_in, wp_snapped):
        for i in range(len(wp_snapped)):
            # Check xy unchanged
            self.assertEqual(wp_in[i][0:2], wp_snapped[i][0:2])
            # Check consistency with new-tvd and old-tvd + TVD_DIFF
            TVD_DIFF = wp_snapped[i][4]
            self.assertAlmostEqual(wp_snapped[i][2], wp_in[i][2] + TVD_DIFF, 2)
            # Check input tvd against outputted old-tvd for consistency
            self.assertEqual(wp_snapped[i][5], wp_in[i][2])

        # Check actual z values
        self.assertAlmostEqual(2507.52, wp_snapped[0][2], 2)
        self.assertAlmostEqual(2684.09, wp_snapped[1][2], 2)
        self.assertAlmostEqual(2678.74, wp_snapped[2][2], 2)
        self.assertAlmostEqual(2674.40, wp_snapped[3][2], 2)
        self.assertAlmostEqual(2690.73, wp_snapped[4][2], 2)
        self.assertAlmostEqual(2688.32, wp_snapped[5][2], 2)

        # Check OWC values
        self.assertAlmostEqual(2695.61, wp_snapped[0][6], 2)
        self.assertAlmostEqual(2699.40, wp_snapped[1][6], 2)
        self.assertAlmostEqual(2695.52, wp_snapped[2][6], 2)
        self.assertAlmostEqual(2690.78, wp_snapped[3][6], 2)
        self.assertAlmostEqual(2694.47, wp_snapped[4][6], 0)
        self.assertAlmostEqual(2693.05, wp_snapped[5][6], 2)

    def write_snap_config_and_run(self, filename):
        norne_test_data_prefix = os.path.join(
            self.TEST_ROOT_PATH,
            "testdata",
            "snapwell",
            "norne",
            "sim_data",
            "NORNE_ATW2013",
        )
        with open(filename, "a") as the_file:
            the_file.write("GRID       " + norne_test_data_prefix + ".EGRID\n")
            the_file.write("RESTART    " + norne_test_data_prefix + ".UNRST\n")
            the_file.write("INIT       " + norne_test_data_prefix + ".INIT\n")
            the_file.write("OUTPUT     snap_output\n")
            the_file.write("OVERWRITE  False\n")
            the_file.write(
                "WELLPATH " + self.norneTestEdgeWellPath + "            1998\n"
            )
            the_file.write("LOG        LENGTH\n")
            the_file.write("LOG        TVD_DIFF\n")
            the_file.write("LOG        OLD_TVD\n")
            the_file.write("LOG        OWC\n")

        # Run the snapwell program
        self.assertEqual(0, subprocess.check_call([self.snapwellprogram, filename]))


if __name__ == "__main__":
    unittest.main()
