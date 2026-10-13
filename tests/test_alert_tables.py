"""D58: a hromada/city alert must never become an alert of its whole raion (or oblast); it goes to the local table."""
import pandas as pd

from src.alerts.build import local_events, merge_intervals, oblast_table, raion_events

T = lambda s: pd.Timestamp(s, tz="UTC")
UNIVERSE = pd.DataFrame({"oblast": ["O1", "O1", "O2"], "raion": ["R1", "R2", "R3"]})


def official(rows):
    return pd.DataFrame(rows, columns=["oblast", "raion", "hromada", "loc_level", "start", "end", "kind"])


def archive(rows):
    d = pd.DataFrame(rows, columns=["oblast", "raion", "hromada", "loc_level", "location_type", "start", "end", "alert_type"])
    d["red"] = False
    return d


VOL = pd.DataFrame(columns=["oblast", "start", "end"])


def tables():
    off = official([
        ("O1", "R1", None, "raion", T("2026-01-01 10:00"), T("2026-01-01 11:00"), "air_raid"),
        ("O1", "R1", "H1", "hromada", T("2025-05-01 00:00"), T("2026-02-01 00:00"), "air_raid"),  # months-long local alert
        ("O1", None, None, "oblast", T("2026-01-02 10:00"), T("2026-01-02 10:30"), "air_raid"),
        ("O2", "R3", "H3", "hromada", T("2026-01-03 10:00"), T("2026-01-03 10:30"), "unknown"),  # unknown at hromada: out
    ])
    arc = archive([
        ("O2", "R3", "H3", "hromada", "hromada", T("2026-09-10 10:00"), T("2026-09-10 12:00"), "air_raid"),
        ("O2", "R3", "м. C", "hromada", "city", T("2026-09-10 10:00"), T("2026-09-10 12:00"), "air_raid"),  # twin of H3
        ("O2", "R3", None, "raion", "raion", T("2026-09-11 10:00"), pd.NaT, "air_raid"),  # still running
    ])
    snap = T("2026-09-12 00:00")
    ev, dropped = raion_events(off, arc, VOL, UNIVERSE, snap)
    ev = ev.assign(source="x")
    return merge_intervals(ev, ["oblast", "raion"]), local_events(off, arc, UNIVERSE, snap)


def test_local_alerts_are_not_raion_alerts():
    raion, local = tables()
    r1 = raion[(raion.oblast == "O1") & (raion.raion == "R1")]
    # only the raion alert and the oblast-wide one; the months-long hromada alert is not there
    assert list(r1.start) == [T("2026-01-01 10:00"), T("2026-01-02 10:00")]
    assert (r1.duration_min <= 60).all()
    r3 = raion[raion.raion == "R3"]
    assert list(r3.start) == [T("2026-09-11 10:00")]  # the hromada/city alert of 09-10 is not a raion alert
    obl = oblast_table(raion)
    assert (obl.duration_min <= 24 * 60 * 2).all()


def test_local_table_keeps_hromada_alerts():
    _, local = tables()
    assert set(local.hromada) == {"H1", "H3"}  # the city twin of H3 is dropped, the unknown-kind row too
    h1 = local[local.hromada == "H1"].iloc[0]
    assert (h1.oblast, h1.raion) == ("O1", "R1") and h1.end == T("2026-02-01 00:00")


def test_hromada_names_in_english():
    from src.alerts.translit import hromada_en, hromada_uk, translit
    assert hromada_en("Липецька територіальна громада") == "Lypetska hromada"
    assert hromada_en("Червоногригорівська територіальна громада") == "Chervonohryhorivska hromada"
    assert hromada_en("м. Харків") == "Kharkiv city"
    assert hromada_en("м. Харків та Харківська територіальна громада") == "Kharkiv city and Kharkivska hromada"
    assert translit("Ізюм") == "Izium" and translit("Їжакевич") == "Yizhakevych" and translit("Згурівка") == "Zghurivka"
    assert translit("Мар'їнка") == "Marinka" and translit("Яготин") == "Yahotyn"
    assert hromada_uk("Липецька територіальна громада") == "Липецька громада"
