import unittest

from redact import as_file_destination, is_a_secret, redact_text


class TestRedaction(unittest.TestCase):
    def test_as_file_destination(self):
        self.assertIsNone(
            as_file_destination("http://example.com", "/home/me/folder", "/home/me")
        )
        self.assertEqual(
            as_file_destination("./file.txt", "/home/me/folder/file.md", "/home/me"),
            "folder/file.txt",
        )
        self.assertEqual(
            as_file_destination(
                "subdir/file.txt", "/home/me/folder/file.md", "/home/me"
            ),
            "folder/subdir/file.txt",
        )
        self.assertEqual(
            as_file_destination("../file.txt", "/home/me/folder/file.md", "/home/me"),
            "file.txt",
        )
        self.assertIsNone(
            as_file_destination("../../file.txt", "/home/me/folder/file.md", "/home/me")
        )

    def test_is_a_secret(self):
        self.assertTrue(is_a_secret("my_password", "jshd_K176!"))
        self.assertTrue(
            is_a_secret("API_TOKEN", "nBJGKTKB68Gvbsdf6aKJGKUTusdbfkIUjsdfvk")
        )
        self.assertTrue(
            is_a_secret("value", "my_email nBJGKTKB68Gvbsdf6aKJGKUTusdbfkIUjsdfvk")
        )
        self.assertFalse(is_a_secret("value", "my_email postmater@my.site"))
        self.assertFalse(is_a_secret("use_password_auth", "false"))
        self.assertFalse(is_a_secret("tokenizer", "default"))
        self.assertFalse(is_a_secret("webserver", "route-53.example.com"))
        self.assertTrue(is_a_secret("value", "qFWAPxEkKkqZ9i9QLad50Nk5mZ1DcxFifUj4"))

    def test_redact_text(self):
        self.assertEqual(
            redact_text("safe_flag: true", ".yaml"), ("safe_flag: true", 0)
        )
        self.assertEqual(
            redact_text("password: jasghDSGF2346", ".yaml"), ("password: REDACTED", 1) # gitleaks:allow
        )
        self.assertEqual(
            redact_text("- --zone=hwer5uy6528hHJG", ".yaml"), ("- --zone=REDACTED", 1)
        )
        self.assertEqual(
            redact_text('value: "kjhds76HJfjkhnf7868HJKGfhagdsJHGJ"', ".yaml"),
            ("value: REDACTED", 1),
        )
        self.assertEqual(
            redact_text("password: jhajksdjk&T*^%ghvsd324GHhd", ".tf"),
            ("password: REDACTED", 1),
        )


if __name__ == "__main__":
    unittest.main()
