import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

SCRIPT = str(Path(__file__).parent.parent / "scripts" / "install_skill.py")

import install_skill


@pytest.fixture
def skill_dirs(tmp_path, monkeypatch):
    """Set up isolated skills and target directories."""
    skills_dir = tmp_path / "skills"
    target_dir = tmp_path / "target"
    skills_dir.mkdir()
    target_dir.mkdir()
    monkeypatch.setattr(install_skill, "SKILLS_DIR", skills_dir)
    monkeypatch.setattr(install_skill, "TARGET_DIR", target_dir)
    return skills_dir, target_dir


def _create_skill(skills_dir: Path, name: str) -> Path:
    """Create a minimal skill directory with SKILL.md."""
    skill_dir = skills_dir / name
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(f"# {name}")
    return skill_dir


def test_install_skill_help():
    """Verify the script runs and shows help."""
    result = subprocess.run(
        [sys.executable, SCRIPT, "--help"],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "install" in result.stdout.lower()


def test_get_available_skills(skill_dirs):
    """Verify get_available_skills filters directories without SKILL.md."""
    skills_dir, _ = skill_dirs
    _create_skill(skills_dir, "valid-skill")
    # Directory without SKILL.md should be excluded
    (skills_dir / "no-skill-md").mkdir()
    # .gitkeep file should be excluded (not a directory)
    (skills_dir / ".gitkeep").touch()

    result = install_skill.get_available_skills()
    assert result == ["valid-skill"]


def test_install_skill_creates_symlink(skill_dirs):
    """Verify install_skill creates a symlink in the target directory."""
    skills_dir, target_dir = skill_dirs
    _create_skill(skills_dir, "mylib")

    install_skill.install_skill("mylib")

    target = target_dir / "mylib"
    assert target.is_symlink()
    assert target.resolve() == (skills_dir / "mylib").resolve()


def test_install_skill_force_overwrites(skill_dirs):
    """Verify --force replaces an existing symlink."""
    skills_dir, target_dir = skill_dirs
    _create_skill(skills_dir, "mylib")

    # Create an existing symlink pointing somewhere else
    target = target_dir / "mylib"
    target.symlink_to("/tmp")

    install_skill.install_skill("mylib", force=True)

    assert target.is_symlink()
    assert target.resolve() == (skills_dir / "mylib").resolve()


def test_install_skill_conflict_without_force(skill_dirs, capsys):
    """Verify warning when target exists without --force."""
    skills_dir, target_dir = skill_dirs
    _create_skill(skills_dir, "mylib")

    # Create an existing symlink
    target = target_dir / "mylib"
    target.symlink_to("/tmp")

    install_skill.install_skill("mylib", force=False)

    captured = capsys.readouterr()
    assert "already exists" in captured.err


def test_install_skill_real_dir_exits(skill_dirs):
    """Verify sys.exit when target is a real directory."""
    skills_dir, target_dir = skill_dirs
    _create_skill(skills_dir, "mylib")

    # Create a real directory at the target
    (target_dir / "mylib").mkdir()

    with pytest.raises(SystemExit):
        install_skill.install_skill("mylib", force=True)


def test_install_skill_missing_skill_md(skill_dirs):
    """Verify sys.exit for a skill directory without SKILL.md."""
    skills_dir, _ = skill_dirs
    (skills_dir / "bad-skill").mkdir()

    with pytest.raises(SystemExit):
        install_skill.install_skill("bad-skill")


def test_remove_skill(skill_dirs):
    """Verify remove_skill removes the symlink."""
    skills_dir, target_dir = skill_dirs
    _create_skill(skills_dir, "mylib")

    # Install first, then remove
    install_skill.install_skill("mylib")
    assert (target_dir / "mylib").is_symlink()

    install_skill.remove_skill("mylib")
    assert not (target_dir / "mylib").exists()


def test_remove_skill_not_symlink(skill_dirs, capsys):
    """Verify warning when target is not a symlink."""
    install_skill.remove_skill("nonexistent")

    captured = capsys.readouterr()
    assert "not a symlink" in captured.err


def test_list_skills(skill_dirs, capsys, monkeypatch):
    """Verify --list shows available skills with install status."""
    skills_dir, target_dir = skill_dirs
    _create_skill(skills_dir, "installed-lib")
    _create_skill(skills_dir, "uninstalled-lib")

    install_skill.install_skill("installed-lib")

    monkeypatch.setattr("sys.argv", ["install_skill.py", "--list"])
    install_skill.main()

    captured = capsys.readouterr()
    assert "[✓] installed-lib" in captured.out
    assert "[ ] uninstalled-lib" in captured.out


def test_install_all(skill_dirs, monkeypatch):
    """Verify --all installs every available skill."""
    skills_dir, target_dir = skill_dirs
    _create_skill(skills_dir, "lib-a")
    _create_skill(skills_dir, "lib-b")

    monkeypatch.setattr("sys.argv", ["install_skill.py", "--all"])
    install_skill.main()

    assert (target_dir / "lib-a").is_symlink()
    assert (target_dir / "lib-b").is_symlink()


def test_remove_all(skill_dirs, monkeypatch):
    """Verify --all --remove removes every installed skill."""
    skills_dir, target_dir = skill_dirs
    _create_skill(skills_dir, "lib-a")
    _create_skill(skills_dir, "lib-b")

    # Install all first
    monkeypatch.setattr("sys.argv", ["install_skill.py", "--all"])
    install_skill.main()

    # Remove all
    monkeypatch.setattr("sys.argv", ["install_skill.py", "--all", "--remove"])
    install_skill.main()

    assert not (target_dir / "lib-a").exists()
    assert not (target_dir / "lib-b").exists()
