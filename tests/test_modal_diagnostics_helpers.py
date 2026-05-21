from modal_app import _git_lfs_available_from_outputs


def test_git_lfs_available_true_when_version_contains_git_lfs() -> None:
    assert _git_lfs_available_from_outputs("git-lfs/3.5.1 (GitHub; linux amd64; go 1.22)", None) is True


def test_git_lfs_available_false_when_git_reports_missing_command() -> None:
    err = "git: 'lfs' is not a git command. See 'git --help'."
    assert _git_lfs_available_from_outputs(None, err) is False
