"""Import the supplied Mediway MVP workbook into auditable project CSV files."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("workbook", type=Path)
    args = parser.parse_args()

    medical = pd.read_excel(args.workbook, sheet_name="의료기관")
    operations = pd.read_excel(args.workbook, sheet_name="진료운영")
    access = pd.read_excel(args.workbook, sheet_name="시설접근성")
    routes = pd.read_excel(args.workbook, sheet_name="보행경로")

    current_facilities = pd.read_csv(PROCESSED / "facilities.csv")
    pharmacies = current_facilities.loc[current_facilities["type"] == "약국"].copy()
    merged = medical.merge(operations[["facility_id", "departments"]], on="facility_id", how="left")
    hospitals = pd.DataFrame(
        {
            "facility_id": merged["facility_id"],
            "name": merged["name"],
            "type": "병원",
            "address": merged["address"],
            "latitude": merged["latitude"],
            "longitude": merged["longitude"],
            "specialty": merged["departments"].fillna("정보 없음"),
            "phone": merged["phone"],
            "source_date": merged["base_data_date"],
            "sub_type": merged["facility_type"],
            "base_source": merged["base_source"],
        }
    )
    if "sub_type" not in pharmacies:
        pharmacies["sub_type"] = "약국"
    if "base_source" not in pharmacies:
        pharmacies["base_source"] = "금정구 약국 공개자료"
    facilities = pd.concat([hospitals, pharmacies], ignore_index=True, sort=False)
    facilities.to_csv(PROCESSED / "facilities.csv", index=False, encoding="utf-8-sig")

    old_hours = pd.read_csv(PROCESSED / "operating_hours.csv")
    pharmacy_hours = old_hours[old_hours["facility_id"].isin(pharmacies["facility_id"])].copy()
    hospital_hours = []
    for row in operations.to_dict("records"):
        hospital_hours.append(
            {
                "facility_id": row["facility_id"], "name": row["name"], "data_status": "unknown",
                "source_level": "공개 참고", "mon": "확인 필요", "tue": "확인 필요", "wed": "확인 필요",
                "thu": "확인 필요", "fri": "확인 필요", "sat": "확인 필요", "sun": "확인 필요",
                "lunch": "확인 필요", "holiday": "확인 필요", "verified_date": row["verified_date"],
                "source_name": "기관 공식·공개 페이지 또는 HIRA 기반 목록", "source_url": row["source_url"],
                "notes": row["reliability"], "schedule_text": row["regular_schedule"],
            }
        )
    hours = pd.concat([pd.DataFrame(hospital_hours), pharmacy_hours], ignore_index=True, sort=False)
    hours.to_csv(PROCESSED / "operating_hours.csv", index=False, encoding="utf-8-sig")

    profiles = []
    access_by_id = access.set_index("facility_id")
    for row in medical.to_dict("records"):
        a = access_by_id.loc[row["facility_id"]]
        profiles.append(
            {
                "facility_id": row["facility_id"], "route_factor": 1.3, "outdoor_ratio": 1.0,
                "slope_level": 0, "transfer_count": 0, "step_free": "unknown", "elevator": "unknown",
                "accessible_parking": "unknown", "data_status": "unknown", "verified_date": "",
                "source_note": f"{a['accessibility_source']} · {a['data_reliability']}",
            }
        )
    pd.DataFrame(profiles).to_csv(PROCESSED / "facility_accessibility.csv", index=False, encoding="utf-8-sig")

    routes.to_csv(PROCESSED / "walking_routes.csv", index=False, encoding="utf-8-sig")
    medical.merge(operations, on=["facility_id", "name"], how="left").to_csv(
        PROCESSED / "hospital_mvp_reference.csv", index=False, encoding="utf-8-sig"
    )
    print(f"Imported hospitals={len(hospitals)}, pharmacies={len(pharmacies)}, routes={len(routes)}")


if __name__ == "__main__":
    main()
