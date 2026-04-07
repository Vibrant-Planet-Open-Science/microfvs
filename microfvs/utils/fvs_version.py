import os
import subprocess

from microfvs.enums import FvsVariant


def get_fvs_version(variant: FvsVariant) -> str:
    """Gets the version of FVS for a given variant."""
    if os.path.exists(f"/usr/local/bin/FVS{variant.lower()}"):
        proc = subprocess.Popen(
            f"/usr/local/bin/FVS{variant.lower()}",
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        outs, _ = proc.communicate()
        proc.kill()
        parsed_fvs_response = [
            x for x in outs.decode().strip().split(" ") if x.startswith("RV:")
        ]
        return parsed_fvs_response[0]
    return "not installed"


def get_fvs_versions() -> dict[str, str]:
    """Gets the versions of FVS for each variant installed."""
    versions = {}
    for variant in FvsVariant:
        name = f"{variant.description} ({variant.value})"
        versions[name] = get_fvs_version(variant)

    return versions
