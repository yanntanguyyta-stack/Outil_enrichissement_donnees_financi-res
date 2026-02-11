"""Tests for the core logic of the company search application."""
import importlib
import sys
import types
import pandas as pd
from io import BytesIO, StringIO
from unittest.mock import MagicMock, patch


def _import_app():
    """Import app module while mocking Streamlit to avoid UI initialization."""
    mock_st = MagicMock()
    mock_st.set_page_config = MagicMock()
    mock_st.title = MagicMock()
    mock_st.markdown = MagicMock()
    mock_st.tabs = MagicMock(return_value=[MagicMock(), MagicMock()])
    mock_st.sidebar = MagicMock()
    mock_st.sidebar.__enter__ = MagicMock(return_value=mock_st.sidebar)
    mock_st.sidebar.__exit__ = MagicMock(return_value=False)
    mock_st.file_uploader = MagicMock(return_value=None)
    mock_st.text_area = MagicMock(return_value="")
    mock_st.button = MagicMock(return_value=False)
    mock_st.spinner = MagicMock()
    mock_st.spinner.return_value.__enter__ = MagicMock()
    mock_st.spinner.return_value.__exit__ = MagicMock(return_value=False)
    mock_st.expander = MagicMock()
    mock_st.expander.return_value.__enter__ = MagicMock()
    mock_st.expander.return_value.__exit__ = MagicMock(return_value=False)
    mock_st.columns = MagicMock(return_value=[MagicMock(), MagicMock()])
    # Make tabs return context managers
    tab1, tab2 = MagicMock(), MagicMock()
    tab1.__enter__ = MagicMock(return_value=tab1)
    tab1.__exit__ = MagicMock(return_value=False)
    tab2.__enter__ = MagicMock(return_value=tab2)
    tab2.__exit__ = MagicMock(return_value=False)
    mock_st.tabs = MagicMock(return_value=[tab1, tab2])
    # col context managers
    col1, col2 = MagicMock(), MagicMock()
    col1.__enter__ = MagicMock(return_value=col1)
    col1.__exit__ = MagicMock(return_value=False)
    col2.__enter__ = MagicMock(return_value=col2)
    col2.__exit__ = MagicMock(return_value=False)
    mock_st.columns = MagicMock(return_value=[col1, col2])

    with patch.dict(sys.modules, {'streamlit': mock_st}):
        if 'app' in sys.modules:
            del sys.modules['app']
        import app
        return app


app = _import_app()


class TestSiretSirenValidation:
    """Tests for SIRET/SIREN validation and extraction."""

    def test_is_siret_valid(self):
        assert app.is_siret("38347481400019") is True

    def test_is_siret_too_short(self):
        assert app.is_siret("383474814") is False

    def test_is_siret_with_letters(self):
        assert app.is_siret("3834748140001A") is False

    def test_is_siret_empty(self):
        assert app.is_siret("") is False

    def test_is_siret_with_spaces(self):
        assert app.is_siret("  38347481400019  ") is True

    def test_is_siren_valid(self):
        assert app.is_siren("383474814") is True

    def test_is_siren_too_long(self):
        assert app.is_siren("38347481400019") is False

    def test_is_siren_too_short(self):
        assert app.is_siren("12345") is False

    def test_extract_siren_from_siret(self):
        assert app.extract_siren_from_siret("38347481400019") == "383474814"

    def test_extract_siren_from_siret_not_siret(self):
        # If not a valid SIRET, returns the original value
        assert app.extract_siren_from_siret("383474814") == "383474814"


class TestDemoDataLookup:
    """Tests for demo data lookup by SIRET, SIREN, and name."""

    def test_search_by_siren(self):
        result = app.search_company_demo("383474814")
        assert result is not None
        assert result["nom_complet"] == "AIRBUS"

    def test_search_by_siret(self):
        result = app.search_company_demo("38347481400019")
        assert result is not None
        assert result["nom_complet"] == "AIRBUS"

    def test_search_by_name(self):
        result = app.search_company_demo("airbus")
        assert result is not None
        assert result["siren"] == "383474814"

    def test_search_not_found(self):
        result = app.search_company_demo("99999999999999")
        assert result is None


class TestExtractFinancialInfo:
    """Tests for financial info extraction."""

    def test_extract_from_demo_data(self):
        company = app.DEMO_COMPANIES["383474814"]
        info = app.extract_financial_info(company)
        assert info["SIREN"] == "383474814"
        assert info["Vérification SIREN"] == "✅ Vérifié"
        assert info["Nom"] == "AIRBUS"
        assert "49,524,000,000" in info["Chiffre d'affaires (CA)"]
        assert "3,501,000,000" in info["Résultat net"]
        assert info["Date clôture exercice"] == "2023-12-31"

    def test_extract_with_original_siret(self):
        company = app.DEMO_COMPANIES["383474814"]
        info = app.extract_financial_info(company,
                                          original_siret="38347481400019")
        assert info["SIRET"] == "38347481400019"

    def test_format_etat_active(self):
        assert app._format_etat("A") == "Active"

    def test_format_etat_cessee(self):
        assert app._format_etat("C") == "Cessée"

    def test_format_currency(self):
        assert "1,000" in app._format_currency(1000)
        assert app._format_currency("N/A") == "N/A"


class TestReadUploadedFile:
    """Tests for file upload parsing."""

    def test_read_csv_with_siret_column(self):
        csv_content = "siret,nom\n38347481400019,Airbus\n54205118000066,Total\n"
        fake_file = MagicMock()
        fake_file.name = "test.csv"
        fake_file.read = MagicMock(return_value=csv_content.encode('utf-8'))
        fake_file.seek = MagicMock()

        # Simulate pd.read_csv from a file-like object
        with patch('pandas.read_csv') as mock_csv:
            mock_csv.return_value = pd.DataFrame({
                'siret': ['38347481400019', '54205118000066'],
                'nom': ['Airbus', 'Total'],
            })
            result = app.read_uploaded_file(fake_file)
            assert len(result) == 2
            assert result[0] == '38347481400019'
            assert result[1] == '54205118000066'

    def test_read_csv_first_column_fallback(self):
        with patch('pandas.read_csv') as mock_csv:
            mock_csv.return_value = pd.DataFrame({
                'code': ['38347481400019', '54205118000066'],
            })
            fake_file = MagicMock()
            fake_file.name = "test.csv"
            result = app.read_uploaded_file(fake_file)
            assert len(result) == 2

    def test_read_xlsx(self):
        with patch('pandas.read_excel') as mock_xl:
            mock_xl.return_value = pd.DataFrame({
                'SIRET': ['38347481400019'],
            })
            fake_file = MagicMock()
            fake_file.name = "test.xlsx"
            result = app.read_uploaded_file(fake_file)
            assert len(result) == 1

    def test_unsupported_format(self):
        fake_file = MagicMock()
        fake_file.name = "test.json"
        result = app.read_uploaded_file(fake_file)
        assert result == []
