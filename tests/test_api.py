"""Tests for Weather CLI"""

import pytest
from weather_cli.core import OpenMeteoClient


class TestOpenMeteoClient:
    """Tests for OpenMeteoClient"""

    def test_validate_city_valid(self):
        """Test valid city validation"""
        client = OpenMeteoClient()
        result = client._validate_city("beijing")
        assert result == "beijing"

    def test_validate_city_case_insensitive(self):
        """Test case insensitive city validation"""
        client = OpenMeteoClient()
        result = client._validate_city("BEIJING")
        assert result == "beijing"

    def test_validate_city_invalid(self):
        """Test invalid city raises error"""
        client = OpenMeteoClient()
        with pytest.raises(ValueError, match="not supported"):
            client._validate_city("nonexistent_city")

    def test_find_similar(self):
        """Test similar city name suggestions"""
        client = OpenMeteoClient()
        result = client._find_similar("beijin")
        assert "Beijing" in result


class TestWeatherCodes:
    """Tests for weather code mappings"""

    def test_clear_sky(self):
        from weather_cli.config import WEATHER_CODES
        assert WEATHER_CODES[0][0] == "Clear sky"
        assert WEATHER_CODES[0][1] == "☀️"

    def test_thunderstorm(self):
        from weather_cli.config import WEATHER_CODES
        assert WEATHER_CODES[95][0] == "Thunderstorm"
