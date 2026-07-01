"""Run pytest programmatically and print results."""
import sys
sys.exit(__import__('pytest').main(['-v', '--tb=short', 'tests/test_storage.py']))
