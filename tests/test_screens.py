import unittest

from actuators.screens import (
    DbusKdeBrightnessControl,
    DbusScreenSaverControl,
    SysfsControl,
    _parse_busctl_bool,
    _parse_busctl_int,
    _parse_control,
    _state_from_read,
)


class ScreenControlTests(unittest.TestCase):
    def test_parse_dbus_screensaver_default_path(self):
        control = _parse_control("dbus:org.freedesktop.ScreenSaver")
        self.assertIsInstance(control, DbusScreenSaverControl)
        self.assertEqual(control.service, "org.freedesktop.ScreenSaver")
        self.assertEqual(control.object_path, "/org/freedesktop/ScreenSaver")

    def test_parse_dbus_kde_brightness(self):
        control = _parse_control(
            "dbus:org.kde.ScreenBrightness:/org/kde/ScreenBrightness/display0"
        )
        self.assertIsInstance(control, DbusKdeBrightnessControl)
        self.assertEqual(control.service, "org.kde.ScreenBrightness")
        self.assertEqual(control.object_path, "/org/kde/ScreenBrightness/display0")

    def test_parse_sysfs_blank(self):
        control = _parse_control("/sys/class/graphics/fb0/blank")
        self.assertIsInstance(control, SysfsControl)
        self.assertEqual(control.path, "/sys/class/graphics/fb0/blank")

    def test_dbus_state_active_means_asleep(self):
        on, brightness = _state_from_read(
            DbusScreenSaverControl("org.freedesktop.ScreenSaver", "/org/freedesktop/ScreenSaver"),
            "b true\n",
        )
        self.assertFalse(on)
        self.assertEqual(brightness, 1)

    def test_dbus_state_inactive_means_awake(self):
        on, brightness = _state_from_read(
            DbusScreenSaverControl("org.freedesktop.ScreenSaver", "/org/freedesktop/ScreenSaver"),
            "b false\n",
        )
        self.assertTrue(on)
        self.assertEqual(brightness, 0)

    def test_kde_brightness_zero_is_asleep(self):
        on, brightness = _state_from_read(
            DbusKdeBrightnessControl("org.kde.ScreenBrightness", "/org/kde/ScreenBrightness/display0"),
            "i 0\n",
        )
        self.assertFalse(on)
        self.assertEqual(brightness, 0)

    def test_kde_brightness_positive_is_awake(self):
        on, brightness = _state_from_read(
            DbusKdeBrightnessControl("org.kde.ScreenBrightness", "/org/kde/ScreenBrightness/display0"),
            "i 10000\n",
        )
        self.assertTrue(on)
        self.assertEqual(brightness, 10000)

    def test_blank_sysfs_zero_is_awake(self):
        on, brightness = _state_from_read(
            SysfsControl("/sys/class/graphics/fb0/blank"),
            "0\n",
        )
        self.assertTrue(on)
        self.assertEqual(brightness, 0)

    def test_parse_busctl_bool(self):
        self.assertTrue(_parse_busctl_bool("b true"))
        self.assertFalse(_parse_busctl_bool("b false"))

    def test_parse_busctl_int(self):
        self.assertEqual(_parse_busctl_int("i 10000"), 10000)
        self.assertIsNone(_parse_busctl_int("b true"))


if __name__ == "__main__":
    unittest.main()