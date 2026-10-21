"""The Board SLOOS package yields one series and drops other rows."""

import io
import zipfile

from aqil_research.adapters.fed_sloos.package import observations_from_package


def test_package_keeps_the_registered_series_only() -> None:
    xml = """<?xml version="1.0"?>
    <kf:Root xmlns:kf="urn:test" xmlns:frb="urn:test">
      <kf:Series SERIES_NAME="OTHER">
        <frb:Obs OBS_VALUE="1.0" TIME_PERIOD="2026-06-30" />
      </kf:Series>
      <kf:Series SERIES_NAME="SUBLPDCILS_N.Q">
        <frb:Obs OBS_VALUE="7.1" TIME_PERIOD="2026-06-30" />
        <frb:Obs OBS_VALUE="" TIME_PERIOD="2026-09-30" />
        <frb:Obs OBS_VALUE="11.8" TIME_PERIOD="2026-09-30" />
        <frb:Obs OBS_VALUE="4.0" TIME_PERIOD="2026-09-15" />
      </kf:Series>
    </kf:Root>
    """
    package = io.BytesIO()
    with zipfile.ZipFile(package, "w") as archive:
        archive.writestr("SLOOS_data.xml", xml)
    rows = observations_from_package(package.getvalue())
    assert rows == [
        {"period": "2026-Q2", "value": "7.1"},
        {"period": "2026-Q3", "value": "11.8"},
    ]
