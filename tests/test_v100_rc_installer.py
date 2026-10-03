import os
import tempfile
import pytest
from protected.profile_installer import ProfileInstaller, START_MARKER, END_MARKER


class TestV100InstallerSafety:
    """Regression tests for Phase 8: PowerShell profile installer idempotency and safety."""

    def test_installer_idempotency_and_preservation(self):
        """Verify repeated installation does not duplicate blocks and preserves user profile content."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            profile_path = os.path.join(tmp_dir, "Microsoft.PowerShell_profile.ps1")

            # Write existing custom user profile content
            user_existing_content = (
                "# User custom settings\n"
                "Set-Alias ll Get-ChildItem\n"
                "$env:MY_CUSTOM_VAR = 'hello'\n"
            )
            with open(profile_path, "w", encoding="utf-8") as f:
                f.write(user_existing_content)

            # 1. First installation
            ok1, msg1 = ProfileInstaller.install(profile_path=profile_path)
            assert ok1 is True
            assert ProfileInstaller.is_installed(profile_path=profile_path) is True

            with open(profile_path, "r", encoding="utf-8") as f:
                content_after_first = f.read()

            assert user_existing_content.strip() in content_after_first
            assert content_after_first.count(START_MARKER) == 1
            assert content_after_first.count(END_MARKER) == 1

            # 2. Second installation (idempotency test)
            ok2, msg2 = ProfileInstaller.install(profile_path=profile_path)
            assert ok2 is True
            assert ProfileInstaller.is_installed(profile_path=profile_path) is True

            with open(profile_path, "r", encoding="utf-8") as f:
                content_after_second = f.read()

            # Verify block count remains 1 and content is preserved
            assert content_after_second.count(START_MARKER) == 1
            assert content_after_second.count(END_MARKER) == 1
            assert user_existing_content.strip() in content_after_second

            # 3. Uninstallation test
            ok3, msg3 = ProfileInstaller.uninstall(profile_path=profile_path)
            assert ok3 is True
            assert ProfileInstaller.is_installed(profile_path=profile_path) is False

            with open(profile_path, "r", encoding="utf-8") as f:
                content_after_uninstall = f.read()

            # Verify Aegis block is completely removed, user content remains
            assert START_MARKER not in content_after_uninstall
            assert END_MARKER not in content_after_uninstall
            assert "Set-Alias ll Get-ChildItem" in content_after_uninstall
            assert "$env:MY_CUSTOM_VAR = 'hello'" in content_after_uninstall

    def test_uninstall_non_existent_profile(self):
        """Verify uninstalling on a non-existent profile returns safely."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            profile_path = os.path.join(tmp_dir, "non_existent_profile.ps1")
            ok, msg = ProfileInstaller.uninstall(profile_path=profile_path)
            assert ok is False
            assert "does not exist" in msg
