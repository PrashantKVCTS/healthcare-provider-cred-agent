"""
Roster Ingestion Agent.
Parses, normalizes, and validates incoming provider roster files (CSV, JSON, dictionaries).
Handles diverse payer/PMS column mappings and performs baseline data hygiene.
"""

import csv
import json
import io
from typing import List, Dict, Any, Union
from models.provider_models import RosterProviderItem


class RosterIngestionAgent:
    """Agent responsible for provider roster intake and schema normalization."""

    NAME = "RosterIngestionAgent"

    # Known column aliases for flexibility across different health plans and PMS formats
    COLUMN_MAPPINGS = {
        "npi": ["npi", "provider_npi", "npi_number", "national_provider_identifier", "npi_id"],
        "first_name": ["first_name", "provider_first_name", "first", "fname", "provider_fname"],
        "last_name": ["last_name", "provider_last_name", "last", "lname", "provider_lname"],
        "caqh_id": ["caqh_id", "caqh", "caqh_number", "caqh_proview_id", "proview_id"],
        "tin": ["tin", "tax_id", "tax_identification_number", "group_tin", "ein"],
        "group_name": ["group_name", "practice_name", "clinic_name", "organization_name", "group"],
        "specialty": ["specialty", "primary_specialty", "taxonomy_desc", "provider_specialty"],
        "practice_state": ["practice_state", "state", "servicing_state", "loc_state"],
        "requested_products": ["requested_products", "market_lines", "products", "lines_of_business", "lob"]
    }

    def _normalize_row_keys(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize various column names into canonical keys."""
        normalized = {}
        for canonical_key, aliases in self.COLUMN_MAPPINGS.items():
            for raw_key, raw_val in row.items():
                clean_raw_key = raw_key.strip().lower().replace(" ", "_").replace("-", "_")
                if clean_raw_key in aliases or clean_raw_key == canonical_key:
                    normalized[canonical_key] = raw_val
                    break
        return normalized

    def parse_csv_content(self, csv_text_or_filepath: str) -> List[RosterProviderItem]:
        """Parse CSV text or file path into a list of RosterProviderItem objects."""
        # Check if input is a filepath or raw CSV content
        if "\n" in csv_text_or_filepath or "," in csv_text_or_filepath:
            reader = csv.DictReader(io.StringIO(csv_text_or_filepath.strip()))
        else:
            with open(csv_text_or_filepath, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                return self._process_dict_rows(list(reader))

        return self._process_dict_rows(list(reader))

    def parse_json_content(self, json_content: Union[str, List[Dict[str, Any]]]) -> List[RosterProviderItem]:
        """Parse JSON array or string of provider records."""
        if isinstance(json_content, str):
            rows = json.loads(json_content)
        else:
            rows = json_content
        return self._process_dict_rows(rows)

    def _process_dict_rows(self, raw_rows: List[Dict[str, Any]]) -> List[RosterProviderItem]:
        """Process and validate list of raw row dictionaries."""
        items: List[RosterProviderItem] = []
        for index, row in enumerate(raw_rows):
            norm = self._normalize_row_keys(row)
            npi = str(norm.get("npi", "")).strip().replace(".0", "")
            first_name = str(norm.get("first_name", "")).strip()
            last_name = str(norm.get("last_name", "")).strip()

            if not npi or not first_name or not last_name:
                continue  # Skip header-less or blank rows

            # Products list normalization
            raw_products = norm.get("requested_products", ["Commercial HMO", "Commercial PPO", "Medicare Advantage", "Medicaid"])
            if isinstance(raw_products, str):
                if ";" in raw_products:
                    products = [p.strip() for p in raw_products.split(";") if p.strip()]
                elif "," in raw_products:
                    products = [p.strip() for p in raw_products.split(",") if p.strip()]
                else:
                    products = [raw_products.strip()]
            elif isinstance(raw_products, list):
                products = raw_products
            else:
                products = ["Commercial HMO", "Commercial PPO", "Medicare Advantage", "Medicaid"]

            item = RosterProviderItem(
                npi=npi,
                first_name=first_name,
                last_name=last_name,
                caqh_id=str(norm.get("caqh_id", "")).strip() or None,
                tin=str(norm.get("tin", "")).strip() or None,
                group_name=str(norm.get("group_name", "")).strip() or None,
                specialty=str(norm.get("specialty", "")).strip() or None,
                practice_state=str(norm.get("practice_state", "TX")).strip().upper(),
                requested_products=products
            )
            items.append(item)

        return items
