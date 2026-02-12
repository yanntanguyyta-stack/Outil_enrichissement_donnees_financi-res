"""Tests for build_rne_db.py — SQLite database builder."""
import json
import os
import sqlite3
import tempfile

from build_rne_db import (
    _parse_amount,
    extract_bilans_from_json,
    init_db,
    INSERT_SQL,
)


class TestParseAmount:
    def test_int(self):
        assert _parse_amount(1000) == 1000

    def test_float(self):
        assert _parse_amount(1234.56) == 1234

    def test_string(self):
        assert _parse_amount("5000") == 5000

    def test_string_with_spaces(self):
        assert _parse_amount(" 5 000 ") == 5000

    def test_none(self):
        assert _parse_amount(None) is None

    def test_empty(self):
        assert _parse_amount("") is None

    def test_dash(self):
        assert _parse_amount("-") is None

    def test_na(self):
        assert _parse_amount("N/A") is None


class TestExtractBilans:
    def _bilan(self, siren="123456789", date_cloture="2023-12-31"):
        return {
            "siren": siren,
            "dateCloture": date_cloture,
            "dateDepot": "2024-07-01",
            "typeBilan": "C",
            "chiffre_affaires": 100000,
            "resultat_net": 5000,
            "resultat_exploitation": 6000,
            "total_actif": 200000,
            "capitaux_propres": 80000,
            "effectif": 10,
        }

    def test_single_bilan(self):
        data = [self._bilan()]
        rows = extract_bilans_from_json(data)
        assert len(rows) == 1
        siren, date_cloture, *_ = rows[0]
        assert siren == "123456789"
        assert date_cloture == "2023-12-31"

    def test_filters_old_dates(self):
        data = [self._bilan(date_cloture="2018-12-31")]
        rows = extract_bilans_from_json(data)
        assert len(rows) == 0

    def test_filters_invalid_siren(self):
        data = [self._bilan(siren="12345")]
        rows = extract_bilans_from_json(data)
        assert len(rows) == 0

    def test_dict_wrapper(self):
        data = {"bilans": [self._bilan()]}
        rows = extract_bilans_from_json(data)
        assert len(rows) == 1


class TestInitDB:
    def test_creates_tables(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            conn = init_db(db_path)
            # Insert a test row
            conn.execute(
                INSERT_SQL,
                ("123456789", "2023-12-31", "2024-07-01", "C",
                 100000, 5000, 6000, 200000, 80000, 10,
                 90000, 4000, 5000, 180000, 70000, 9),
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM bilans WHERE siren = '123456789'"
            ).fetchone()
            assert row is not None
            conn.close()
        finally:
            os.unlink(db_path)


class TestEnrichment:
    """Tests for enrichment.py module."""

    def test_get_finances_no_db(self):
        """get_finances returns error when DB doesn't exist."""
        import enrichment
        old_path = enrichment.DB_PATH
        try:
            enrichment.DB_PATH = "/tmp/nonexistent_test.db"
            result = enrichment.get_finances("123456789")
            assert result["success"] is False
            assert "database_not_found" in result.get("error", "")
        finally:
            enrichment.DB_PATH = old_path

    def test_get_finances_with_db(self):
        """get_finances returns data from a real SQLite DB."""
        import enrichment
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            conn = init_db(db_path)
            conn.execute(
                INSERT_SQL,
                ("123456789", "2023-12-31", "2024-07-01", "C",
                 100000, 5000, 6000, 200000, 80000, 10,
                 90000, 4000, 5000, 180000, 70000, 9),
            )
            conn.commit()
            conn.close()

            old_path = enrichment.DB_PATH
            enrichment.DB_PATH = db_path
            result = enrichment.get_finances("123456789")
            assert result["success"] is True
            assert result["count"] == 1
            assert result["bilans"][0]["chiffre_affaires"] == 100000
            enrichment.DB_PATH = old_path
        finally:
            os.unlink(db_path)

    def test_db_available(self):
        import enrichment
        old_path = enrichment.DB_PATH
        enrichment.DB_PATH = "/tmp/nonexistent_test.db"
        assert enrichment.db_available() is False
        enrichment.DB_PATH = old_path
