from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]


def _direct_package_names(path: Path) -> set[str]:
    names: set[str] = set()
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith(("#", "-")):
            continue
        package = line.split("==", 1)[0].split("[", 1)[0].strip().lower()
        names.add(package)
    return names


def test_development_requirements_include_runtime_as_single_source() -> None:
    development_lines = [
        line.strip()
        for line in (BACKEND_ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]

    assert development_lines[0] == "-r requirements.runtime.txt"

    runtime_packages = _direct_package_names(BACKEND_ROOT / "requirements.runtime.txt")
    development_packages = _direct_package_names(BACKEND_ROOT / "requirements.txt")

    assert runtime_packages.isdisjoint(development_packages)
